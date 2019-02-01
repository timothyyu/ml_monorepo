package ase.portfolio;

import java.util.logging.Logger;

import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class Position {
	private static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(Position.class.getName());

	public final Security sec;
	private double shares = 0;
	private double cash = 0.0;
	private double latest_price = Double.NaN;
	private long price_ts = 0L;
	private double dollars_traded = 0.0;

	public Position(Security sec) {
		this.sec = sec;
	}

	public Position(Security sec, double shares, double cash) {
		assert !Double.isNaN(cash);

		this.sec = sec;
		this.shares = shares;
		this.cash = cash;
	}

	public void setLatestPrice(double price, long price_ts) {
		assert price > 0;
		if (!(price > 0))
			throw new RuntimeException("Bad price for sec " + sec.getSecId() + " of " + price);

		// XXX note the inequality. If you are using multiple data sources to set prices whose
		// timestamps can be equal (e.g. 5min bars and daily bars) apply them in descending order of priority!
		if (price_ts > this.price_ts) {
			this.latest_price = price;
			this.price_ts = price_ts;
		}
	}

	public double getLatestPrice() {
		return latest_price;
	}

	public boolean isValid() {
		return latest_price > 0;
	}

	public long getPriceTs() {
		return price_ts;
	}

	public double notional() {
		return shares * latest_price;
	}

	public double getDoubleShares() {
		return shares;
	}

	public int getIntShares() {
		assert shares == Math.round(shares);
		return (int) shares;
	}

	public double getCash() {
		return cash;
	}

	public double getDollarsTraded() {
		return dollars_traded;
	}

	public double getPnl() {
		return notional() + cash;
	}

	public boolean deadAndGone() {
		if (!sec.isAlive() && shares == 0)
			return true;
		return false;
	}

	public void adjust(CapAdjustment adj, Portfolio portfolio) {
		switch (adj.type) {
		case DIV:
		case CORP_CASH:
			adjustCash(adj, portfolio);
			break;
		case SPLIT:
			// For a split rate of X, we are getting +(X-1)*shares. This works for both X>=1 and X<1, long or short
			adj = new CapAdjustment(adj.sec, adj.type, adj.adj - 1, adj.sizeRef, adj.sizeRefType, adj.description);
			adjustShares(adj, portfolio);
			break;
		case CORP_SHARES:
			adjustShares(adj, portfolio);
			break;
		case FILL:
			adjustFill(adj, portfolio);
			break;
		case LIQ:
			adjustLiquidate(adj, portfolio);
			break;
		case CASHEQ:
			break;
		default:
			log.severe("Unsupported Adjustment Type: " + adj.type);
			break;
		}
	}

	protected void adjustCash(CapAdjustment adj, Portfolio portfolio) {
		double baseSize = 0;

		switch (adj.sizeRefType) {
		case ABSOLUTE:
			baseSize = adj.sizeRef;
			break;
		case SECID:
			Position refPos = portfolio.getPosition(new Security(adj.sizeRef));
			if (refPos == null) {
				log.severe("Adjustment references unknown secid position: " + adj);
			}
			else {
				baseSize = refPos.shares;
			}
			break;
		case SELF:
			baseSize = shares;
			break;
		default:
			log.severe("Unsupported SizeRefType");
			break;
		}

		assert portfolio.allowFracPos || Math.round(baseSize) == baseSize;

		cash += adj.adj * baseSize;
		if (Double.isNaN(cash))
			throw new RuntimeException();
	}

	protected void adjustShares(CapAdjustment adj, Portfolio portfolio) {
		if (adj.adj == 0)
			return;

		double baseSize = 0;
		double basePrice = 0;

		switch (adj.sizeRefType) {
		case ABSOLUTE:
			baseSize = adj.sizeRef;
			basePrice = 0;
			break;
		case SECID:
			Position refPos = portfolio.getPosition(new Security(adj.sizeRef));
			if (refPos == null) {
				log.severe("Adjustment references unknown secid position: " + adj);
			}
			else {
				baseSize = refPos.shares;
			}
			basePrice = refPos.latest_price;
			break;
		case SELF:
			baseSize = shares;
			basePrice = latest_price;
			break;
		default:
			log.severe("Unsupported SizeRefType");
			break;
		}

		assert portfolio.allowFracPos || Math.round(baseSize) == baseSize;
		double realShares = adj.adj * baseSize;

		if (portfolio.allowFracPos) {
			shares += realShares;
		}
		else {
			int wholeShares = (int) (Math.signum(realShares) * Math.floor(Math.abs(realShares)));
			double fracShares = realShares - wholeShares;
			// take care of numerical innacuracies
			if (Math.abs(Math.abs(fracShares) - 1) < 1e-6) {
				fracShares = 0;
				wholeShares += Math.round(fracShares);
			}

			shares += wholeShares;
			if (fracShares != 0)
				cash += fracShares * basePrice;
			
			if (Double.isNaN(cash)) {
				log.severe("Bad CapAdjustment: " + adj);
				throw new RuntimeException("Bad CapAdjustment: " + adj);
			}
		}
	}

	protected void adjustFill(CapAdjustment adj, Portfolio portfolio) {
		Fill dummyFill = new Fill(this.sec, 1, adj.sizeRef, adj.adj, null, 0);
		add(dummyFill, portfolio);
	}

	protected void adjustLiquidate(CapAdjustment adj, Portfolio portfolio) {
		Fill dummyFill = new Fill(this.sec, 1, -shares, adj.adj, null, 0);
		add(dummyFill, portfolio);
	}

	public void add(Fill fill, Portfolio portfolio) {
		assert portfolio.allowFracPos || Math.round(fill.shares) == fill.shares;
		shares += fill.shares;
		cash -= fill.price * fill.shares;
		dollars_traded += Math.abs(fill.price * fill.shares);
		setLatestPrice(fill.price, fill.ts);
	}

	public String pnlLine() {
		return sec.getSecId() + "|" + shares + "|" + df.fformat(latest_price) + "|" + df.format(price_ts) + "|" + df.fformat(getPnl());
	}

	public String toString() {
		return sec.getSecId() + "|" + shares + "|" + df.fformat(latest_price) + "|" + df.format(price_ts) + "|" + df.fformat(cash) + "|"
				+ df.fformat(dollars_traded);
	}

	public static String dumpHeader() {
		return "type|secid|shares|latest_price|price_ts|cash|dollars_traded";
	}

	public String dumpOutput() {
		return dumpOutput(false);
	}

	public String dumpOutput(boolean fractionalPositions) {
		assert fractionalPositions || Math.round(shares) == shares;
		return "POS|" + sec.getSecId() + "|" + (fractionalPositions ? df.fformat(shares) : (int) shares) + "|" + df.fformat(latest_price) + "|" + price_ts
				+ "|" + df.fformat(cash) + "|" + df.fformat(dollars_traded);
	}

	public static Position restore(String line) throws Exception {
		String[] fields = line.split("\\|");
		Position pos = new Position(new Security(Integer.parseInt(fields[1])), Double.parseDouble(fields[2]), Double.parseDouble(fields[5]));
		pos.latest_price = Double.parseDouble(fields[3]);
		try {
			pos.price_ts = Long.parseLong(fields[4]);
		}
		catch (NumberFormatException e) {
			pos.price_ts = df.parseLong(fields[4]).getTime();
		}
		pos.dollars_traded = Double.parseDouble(fields[6]);
		return pos;
	}
}
