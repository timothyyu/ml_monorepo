package ase.portfolio;

import gnu.trove.TIntObjectHashMap;

import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.calculator.Forecast;
import ase.calculator.Forecast.Type;
import ase.data.Currency;
import ase.data.Exchange;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Triplet;

public class Fill implements Comparable<Fill> {
	
	////////////////////// ENUMERATION FOR FILL FIELDS ////////////////////
	public enum LiquidityType {
		UNK, A, R, O
	};

	public enum Tactic {
		UNKNOWN('K'), JOIN_QUEUE('J'), FLW_LEADER('L'), STEP_UP_L1('T'), CROSS('X'), TAKE_INVISIBLE('I'), FLW_SOB('S'), MKT_ON_CLOSE('M'), EXEC_UNKNOWN('U');

		private static HashMap<Character, Tactic> lookup = new HashMap<Character, Fill.Tactic>();
		static {
			for (Tactic c : EnumSet.allOf(Tactic.class))
				lookup.put(c.getCode(), c);
		}
		private char code;

		private Tactic(char c) {
			this.code = c;
		}

		public char getCode() {
			return this.code;
		}

		public static Tactic getTactic(char c) {
			return lookup.get(c);
		}
	}

	////////////////////////////////////////////////
	
	private static final ASEFormatter df = ASEFormatter.getInstance();
	protected static final Logger log = LoggerFactory.getLogger(Fill.class.getName());

	public final Security sec;
	public final double shares;
	public final double price;
	public final long ts;
	public final Order order;
	public final long fillid;
	public final Exchange.Type venue;
	public final LiquidityType liquidity;
	public final Tactic tactic;
	public final long orderid;

	public Fill(Security sec, long ts, double shares, double price, Order order, long id, Exchange.Type venue, LiquidityType liq, long orderid, Tactic tactic) {
		assert price > 0.0;
		assert shares > -1000000 && shares < 1000000;
		assert ts > 0;

		this.sec = sec;
		this.shares = shares;
		this.price = price;
		this.ts = ts;
		this.order = order;
		this.fillid = id;
		this.venue = venue;
		this.liquidity = liq;
		this.orderid = orderid;
		this.tactic = tactic;
	}

	public Fill(Security sec, long ts, double shares, double price, Order order, long id) {
		this(sec, ts, shares, price, order, id, Exchange.Type.NONE, LiquidityType.UNK, (order != null? order.orderid : -1), Tactic.UNKNOWN); 
	}

	public Fill(Order order, long ts, double price) {
		this(order.sec, ts, order.shares, price, order, 0);
	}

	public Fill(Fill fill) {
		this(fill.sec, fill.ts, fill.shares, fill.price, fill.order, fill.fillid, fill.venue, fill.liquidity, fill.orderid, fill.tactic);
	}

	@Deprecated
	private Map<Forecast, Fill> allocateMus_old1(Set<Forecast> forecasts) {
		// XXX I could be more precise here in my allocation instead of just rounding...

		// if no order associated, just allcate the whole thing to full
		if (order == null) {
			Map<Forecast, Fill> res = new HashMap<Forecast, Fill>();
			res.put(Forecast.FULL, new Fill(this));
			return res;
		}

		Map<Forecast, Fill> res = new HashMap<Forecast, Fill>(order.mus.size());
		Set<Forecast> allForecasts = new HashSet<Forecast>(forecasts.size());
		allForecasts.addAll(forecasts);
		allForecasts.addAll(order.mus.keySet());

		double full = order.mus.get(Forecast.FULL);
		double muShares;
		double riskSharesPerForecast;
		if (order.dmu <= 0) {
			muShares = 0.0;
			riskSharesPerForecast = shares / (allForecasts.size() - 1);
		}
		else {
			if (order.drisk >= 0) {
				muShares = shares;
				riskSharesPerForecast = 0.0;
			}
			else {
				muShares = shares * Math.abs(order.dmu / (order.dmu - order.drisk));
				riskSharesPerForecast = shares * Math.abs((order.drisk / (order.dmu - order.drisk)) / (allForecasts.size() - 1));
			}
		}

		assert !Double.isNaN(full) && !Double.isNaN(riskSharesPerForecast) && !Double.isNaN(muShares);

		int sharetot = 0;
		for (Forecast forecast : allForecasts) {
			if (forecast.isFull())
				continue;

			double mu = (order.mus.get(forecast) != null ? order.mus.get(forecast) : 0.0);
			double muFillShares = muShares == 0.0 ? 0.0 : muShares * mu / full;
			double tot = muFillShares + riskSharesPerForecast;

			if (Double.isNaN(tot)) {
				log.severe("Unable to calculate shares on: " + forecast + " " + order);
				continue;
			}
			int totrnd = (int) Math.round(tot);
			res.put(forecast, new Fill(sec, ts, totrnd, price, order, fillid));
			sharetot += totrnd;

			// if(sec.isIBM()) {
			// System.out.println("SEAN :" + forecast.name + " " + mu + " " + muShares + " " + muFillShares + " " + tot );
			// }
		}
		if (Math.abs(sharetot - order.shares) > allForecasts.size()) {
			log.warning("Mu shares don't add up!: " + order + " " + sharetot);
		}
		return res;
	}

	public Map<Forecast, Fill> allocateMus(Portfolio portfolio, Map<Forecast, Portfolio> muPortfolios) {
		Map<Forecast, Fill> expanding = null;
		Map<Forecast, Fill> contracting = null;
		// Divy up the fill into contracting and expanding parts
		int pos = (portfolio.getPosition(sec) != null) ? portfolio.getPosition(sec).getIntShares() : 0;
		if (Math.signum(shares * pos) >= 0) {
			expanding = expandingTrade(this, muPortfolios, null);
		}
		else {
			double contractingShares = Math.signum(shares) * Math.min(Math.abs(pos), Math.abs(shares));
			double expandingShares = (contractingShares != shares) ? Math.signum(shares) * Math.abs(shares - contractingShares) : 0;

			assert contractingShares == Math.round(contractingShares);
			assert expandingShares == Math.round(expandingShares);
			assert Math.signum(expandingShares * contractingShares) >= 0;
			assert shares == expandingShares + contractingShares;

			if (expandingShares == 0) {
				contracting = contractingTrade(this, muPortfolios);
			}
			else {
				contracting = contractingTrade(new Fill(sec, ts, contractingShares, price, order, fillid, venue, liquidity, orderid, tactic), muPortfolios);
				expanding = expandingTrade(new Fill(sec, ts, expandingShares, price, order, fillid, venue, liquidity, orderid, tactic), muPortfolios,
						contracting);
			}
		}

		if (expanding != null && contracting == null)
			return expanding;
		else if (expanding == null && contracting != null)
			return contracting;
		else {
			Map<Forecast, Fill> res = new HashMap<Forecast, Fill>();
			Set<Forecast> fcs = new HashSet<Forecast>();
			fcs.addAll(expanding.keySet());
			fcs.addAll(contracting.keySet());

			for (Forecast fc : fcs) {
				Fill fill1 = expanding.get(fc);
				Fill fill2 = contracting.get(fc);

				double shares1 = (fill1 != null) ? fill1.shares : 0.0;
				double shares2 = (fill2 != null) ? fill2.shares : 0.0;
				// /XXX do not enforce this assertion due to portfolio auto corrections
				// assert Math.signum(shares1 * shares2) >= 0;
				res.put(fc, new Fill(sec, ts, shares1 + shares2, price, order, fillid, venue, liquidity, orderid, tactic));
			}
			return res;
		}
	}

	protected static Map<Forecast, Fill> contractingTrade(Fill fill, Map<Forecast, Portfolio> muPortfolios) {
		Map<Forecast, Fill> res = new HashMap<Forecast, Fill>();
		Map<Forecast, Double> fracShares = new HashMap<Forecast, Double>();

		double totalSecShares = 0;
		for (Map.Entry<Forecast, Portfolio> e : muPortfolios.entrySet()) {
			Portfolio p = e.getValue();
			Position pos = p.getPosition(fill.sec);
			// This is a contracting trade. Hence, fill.shares and pos.getShares should have opposite signs
			if (pos == null || pos.getDoubleShares() == 0 || Math.signum(fill.shares * pos.getDoubleShares()) > 0)
				continue;
			totalSecShares += Math.abs(pos.getDoubleShares());
		}

		int totalFracShares = 0;
		for (Map.Entry<Forecast, Portfolio> e : muPortfolios.entrySet()) {
			Forecast fcast = e.getKey();
			Portfolio p = e.getValue();
			Position pos = p.getPosition(fill.sec);
			if (pos == null || pos.getDoubleShares() == 0)
				continue;
			// This is a contracting trade. Hence, fill.shares and pos.getShares should have opposite signs
			// If they don't "auto-correct" portfolio by generating a fill that will drive the position to 0, since its position should have been 0
			if (Math.signum(fill.shares * pos.getDoubleShares()) >= 0) {
				log.warning("Auto correcting portfolio " + fcast.name + ". Found secid " + pos.sec.getSecId() + ", pos=" + df.fformat(pos.getDoubleShares())
						+ " on contracting fill of " + df.fformat(fill.shares));
				fracShares.put(fcast, -pos.getDoubleShares());
				continue;
			}

			double fraction = 1.0 * Math.abs(pos.getDoubleShares()) / totalSecShares;
			double fp = fraction * fill.shares;
			if (Math.abs(fp) > Math.abs(pos.getDoubleShares())) {
				log.warning("Allocated contracting trade for portfolio " + fcast.name + " secid=" + fill.sec.getSecId() + " of " + df.fformat(fp)
						+ " on position of " + df.fformat(pos.getDoubleShares()) + ". Truncating...");
				fp = -pos.getDoubleShares();
			}
			assert Math.signum(fp * fill.shares) >= 0;
			assert Math.abs(fp) <= Math.abs(fill.shares);
			totalFracShares += fp;
			fracShares.put(fcast, fp);
		}

		for (Map.Entry<Forecast, Double> e : fracShares.entrySet()) {
			res.put(e.getKey(), new Fill(fill.sec, fill.ts, e.getValue(), fill.price, fill.order, fill.fillid, fill.venue, fill.liquidity, fill.orderid,
					fill.tactic));
		}

		return res;
	}

	protected static Map<Forecast, Fill> expandingTrade(Fill fill, Map<Forecast, Portfolio> muPortfolios, Map<Forecast, Fill> contractingAllocation) {
		Map<Forecast, Fill> res = new HashMap<Forecast, Fill>();
		Map<Forecast, Double> fracShares = new HashMap<Forecast, Double>();

		double direction = Math.signum(fill.shares);

		// if no order associated, just allocate the whole thing to NONE
		if (fill.order == null) {
			res.put(Forecast.NONE, new Fill(fill));
			return res;
		}
		// if negative dmu order and positive risk, allocate to NONE
		if (fill.order.dmu <= 0 && fill.order.drisk >= 0) {
			res.put(Forecast.NONE, new Fill(fill));
			return res;
		}

		// Extract risk component
		double riskFraction = Math.max(-fill.order.drisk, 0) / (Math.max(fill.order.dmu, 0) + Math.max(-fill.order.drisk, 0));
		double muFraction = Math.max(fill.order.dmu, 0) / (Math.max(fill.order.dmu, 0) + Math.max(-fill.order.drisk, 0));
		double totalFracShares = 0;

		if (!(riskFraction >= 0 && riskFraction <= 1 && muFraction >= 0 && muFraction <= 1)) {
			log.warning("Bizzare risk and mu fractions. Mu=" + muFraction + ", Risk=" + riskFraction);
		}

		if (riskFraction > 0) {
			double fp = riskFraction * fill.shares;
			assert Math.signum(fp * fill.shares) >= 0;
			assert Math.abs(fp) <= Math.abs(fill.shares);
			totalFracShares += fp;
			fracShares.put(Forecast.NONE, fp);
		}

		if (muFraction > 0) {
			double totalParallelMu = 0;
			// first pass to find mus in the same direction as full
			for (Map.Entry<Forecast, Double> e : fill.order.mus.entrySet()) {
				Forecast fc = e.getKey();
				Double mu = e.getValue();
				if (fc.isFull() || fc.type != Type.MU || mu == null)
					continue;
				if (Math.signum(mu * direction) > 0)
					totalParallelMu += mu;
			}

			// second pass to divy up shares
			for (Map.Entry<Forecast, Double> e : fill.order.mus.entrySet()) {
				Forecast fc = e.getKey();
				Double mu = e.getValue();
				if (fc.isFull() || fc.type != Type.MU || mu == null)
					continue;
				if (Math.signum(mu * direction) > 0) {
					double fp = muFraction * mu / totalParallelMu * fill.shares;
					assert Math.signum(fp * fill.shares) >= 0;
					assert Math.abs(fp) <= Math.abs(fill.shares);
					totalFracShares += fp;
					fracShares.put(fc, fp);
				}
			}
		}

		// Auto correct portfolios
		for (Map.Entry<Forecast, Portfolio> e : muPortfolios.entrySet()) {
			Forecast fc = e.getKey();
			Portfolio p = e.getValue();
			Position pos = p.getPosition(fill.sec);
			Double fp = fracShares.get(fc);
			Fill contractingFill = (contractingAllocation != null) ? contractingAllocation.get(fc) : null;

			if (pos == null || pos.getDoubleShares() == 0)
				continue;

			double adj = 0;
			double contractingShares = (contractingFill != null) ? contractingFill.shares : 0.0;
			if (Math.signum((pos.getDoubleShares() + contractingShares) * fill.shares) < 0) {
				log.warning("Auto correcting portfolio " + fc.name + ". Found secid " + pos.sec.getSecId() + ", pos="
						+ df.fformat(pos.getDoubleShares() + contractingShares) + " on expanding fill of " + df.fformat(fill.shares));
				adj = -(pos.getDoubleShares() + contractingShares);
				fp = (fp != null) ? fp + adj : adj;
			}

			if (fp == null)
				continue;

			if (fp == 0)
				fracShares.remove(fc);
			else
				fracShares.put(fc, fp);
		}

		for (Map.Entry<Forecast, Double> e : fracShares.entrySet()) {
			res.put(e.getKey(), new Fill(fill.sec, fill.ts, e.getValue(), fill.price, fill.order, fill.fillid, fill.venue, fill.liquidity, fill.orderid,
					fill.tactic));
		}

		return res;
	}

	// TODO merge this with the logic for the other allocateMus.
	public Map<Forecast, Fill> allocateMus() {
		Map<Forecast, Fill> res = new HashMap<Forecast, Fill>();

		double direction = Math.signum(shares);

		// if no order associated, just allocate the whole thing to NONE
		if (order == null) {
			res.put(Forecast.NONE, new Fill(this));
			return res;
		}
		// if negative dmu order and positive risk, allocate to NONE
		if (order.dmu <= 0 && order.drisk >= 0) {
			res.put(Forecast.NONE, new Fill(this));
			return res;
		}

		// Extract risk component
		double riskFraction = Math.max(-order.drisk, 0) / (Math.max(order.dmu, 0) + Math.max(-order.drisk, 0));
		double muFraction = Math.max(order.dmu, 0) / (Math.max(order.dmu, 0) + Math.max(-order.drisk, 0));
		double totalFracShares = 0;

		if (!(riskFraction >= 0 && riskFraction <= 1 && muFraction >= 0 && muFraction <= 1)) {
			log.warning("Bizzare risk and mu fractions. Mu=" + muFraction + ", Risk=" + riskFraction);
		}

		if (riskFraction > 0) {
			double fp = riskFraction * shares;
			assert Math.signum(fp * shares) >= 0;
			assert Math.abs(fp) <= Math.abs(shares);
			totalFracShares += fp;
			res.put(Forecast.NONE, new Fill(sec, ts, fp, price, order, fillid, venue, liquidity, orderid, tactic));
		}

		if (muFraction > 0) {
			double totalParallelMu = 0;
			// first pass to find mus in the same direction as full
			for (Map.Entry<Forecast, Double> e : order.mus.entrySet()) {
				Forecast fc = e.getKey();
				Double mu = e.getValue();
				if (fc.isFull() || fc.type != Type.MU || mu == null)
					continue;
				if (Math.signum(mu * direction) > 0)
					totalParallelMu += mu;
			}

			// second pass to divy up shares
			for (Map.Entry<Forecast, Double> e : order.mus.entrySet()) {
				Forecast fc = e.getKey();
				Double mu = e.getValue();
				if (fc.isFull() || fc.type != Type.MU || mu == null)
					continue;
				if (Math.signum(mu * direction) > 0) {
					double fp = muFraction * mu / totalParallelMu * shares;
					assert Math.signum(fp * shares) >= 0;
					assert Math.abs(fp) <= Math.abs(shares);
					totalFracShares += fp;
					res.put(fc, new Fill(sec, ts, fp, price, order, fillid, venue, liquidity, orderid, tactic));
				}
			}
		}
		return res;
	}

	public static String dumpHeader() {
		return "type|date|strat|seqnum|secid|ticker|ts_received|ts_exchange|shares|price|venue|liquidity|orderid|tactic";
	}

	public String toString() {
		Triplet<String, String, String> t = fieldsFromFillid(fillid);
		return "F|" + t.first + "|" + t.second + "|" + t.third + "|" + sec.getSecId() + "|" + "UNK" + "|" + ts + "|" + ts + "|" + shares + "|" + price + "|"
				+ venue.toString() + "|" + liquidity.toString() + "|" + (order != null ? order.orderid : -1) + "|" + tactic.getCode();
	}

	//
	protected static long fillIdFromFields(String date, String strat, String seqnum) {
		int d1 = Integer.parseInt(date);
		int d2 = Integer.parseInt(strat);
		int d3 = Integer.parseInt(seqnum);

		long fillid = d1 * 100000000L;
		fillid += d2 * 1000000L;
		fillid += d3;

		return fillid;
	}

	protected static Triplet<String, String, String> fieldsFromFillid(long fillid) {
		if (fillid < 0)
			return new Triplet<String, String, String>("0", "0", "0");

		String date = Integer.toString((int) (fillid / 100000000));
		String strat = Integer.toString((int) ((fillid % 100000000) / 1000000));
		String seq = Integer.toString((int) (fillid % 1000000));

		return new Triplet<String, String, String>(date, strat, seq);
	}

	public static Fill restoreFromFillsFile(String line) throws Exception {
		String[] fields = line.split("\\|");

		if (fields.length <= 10)
			return new Fill(new Security(Integer.parseInt(fields[4])), Long.parseLong(fields[6]), Double.parseDouble(fields[8]), Double.parseDouble(fields[9]),
					null, fillIdFromFields(fields[1], fields[2], fields[3]));
		else {
			String exch = fields[10];
			if(exch.equals("ISLD")) exch = "NASD";
			if (fields.length <= 13)
				return new Fill(new Security(Integer.parseInt(fields[4])), Long.parseLong(fields[6]), Double.parseDouble(fields[8]), Double.parseDouble(fields[9]),
								null, fillIdFromFields(fields[1], fields[2], fields[3]), Exchange.Type.valueOf(exch), LiquidityType.valueOf(fields[11]), -1, Tactic.UNKNOWN);
			else
				return new Fill(new Security(Integer.parseInt(fields[4])), Long.parseLong(fields[6]), Double.parseDouble(fields[8]), Double.parseDouble(fields[9]),
								null, fillIdFromFields(fields[1], fields[2], fields[3]), Exchange.Type.valueOf(exch), LiquidityType.valueOf(fields[11]),
								Long.parseLong(fields[12]), Tactic.getTactic(fields[13].charAt(0)));
		}
	}

	public int compareTo(Fill fill) {
		if (this.ts > fill.ts)
			return 1;
		else if (this.ts < fill.ts)
			return -1;
		else
			return 0;
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		long temp;
		temp = Double.doubleToLongBits(price);
		result = prime * result + (int) (temp ^ (temp >>> 32));
		result = prime * result + ((sec == null) ? 0 : sec.hashCode());
		result = prime * result + (int) shares;
		result = prime * result + (int) (ts ^ (ts >>> 32));
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		Fill other = (Fill) obj;
		if (Double.doubleToLongBits(price) != Double.doubleToLongBits(other.price))
			return false;
		if (sec == null) {
			if (other.sec != null)
				return false;
		}
		else if (!sec.equals(other.sec))
			return false;
		if (shares != other.shares)
			return false;
		if (ts != other.ts)
			return false;
		if (orderid != other.orderid)
			return false;
		return true;
	}

	
	public static void main(String[] args) {
		String date = "20110625";
		String strat= "1";
		String seqnum ="123";
		
		long fillid = fillIdFromFields(date, strat, seqnum);
		System.out.println(fillid);
		System.out.println(fieldsFromFillid(fillid));
	}
	
}
