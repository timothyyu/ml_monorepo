package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.calculator.BorrowCalculator;
import ase.calculator.DailyPriceCalculator;
import ase.calculator.Forecast;
import ase.calculator.filter.SecurityFilter;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Price;
import ase.data.Security;
import ase.portfolio.CapAdjustment.SizeRefType;
import ase.portfolio.CapAdjustment.Type;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class Portfolio {
	
	public enum BorrowsUpdateMode {ABSOLUTE, INCREMENTAL, IGNORE};
	
	private Logger log = LoggerFactory.getLogger(Portfolio.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static final String SOD_PORTFOLIO = "sodPort.txt";
	public static final String DAY_CAPADJUSTMENTS = "cap_adjustments.txt";

	public static final String dayFillsFilename(long day) {
		return dayFillsFilename(df.toYYYYMMDD(day));
	}

	public static final String dayFillsFilename(File daydir) {
		return dayFillsFilename(daydir.getName());
	}

	public static final String dayFillsFilename(String day) {
		return "fills." + day + ".txt";
	}

	private final Map<Security, Position> positions = new HashMap<Security, Position>();
	private final List<Fill> fills = new Vector<Fill>();
	public final PortfolioStats stats = new PortfolioStats();

	private final Map<Security, SecurityTradeInfo> tradeinfo = new HashMap<Security, SecurityTradeInfo>();
	private final Map<Forecast, Portfolio> muPortfolios;

	private double maxPosPctAdv = Double.NaN;
	private int defaultLotSize = 5;

	private long asof = 0L;
	private boolean muPortfoliosAutoUpdate = false;
	public String name = "";
	public boolean allowFracPos = false;

	public Portfolio(Properties config) {
		this(config, true);
	}

	public Portfolio(Properties config, boolean autoMus) {
		this.maxPosPctAdv = Double.parseDouble(config.getProperty("max_posadv"));
		this.defaultLotSize = Integer.parseInt(config.getProperty("default_lot_size"));

		muPortfolios = new HashMap<Forecast, Portfolio>();
		muPortfoliosAutoUpdate = autoMus;
	}

	public Portfolio(String name) {
		this.muPortfolios = new HashMap<Forecast, Portfolio>();
		this.muPortfoliosAutoUpdate = false;
		this.name = name;
	}

	public Portfolio() {
		this("");
	}

	public void setLogger(Logger log) {
		this.log = log;
	}

	public boolean getMuPortfoliosAutoUpdate() {
		return muPortfoliosAutoUpdate;
	}

	public void setMuPortfoliosAutoUpdate(boolean muPortfoliosAutoUpdate) {
		this.muPortfoliosAutoUpdate = muPortfoliosAutoUpdate;
	}

	public void allowFractionalPositions(boolean allow) {
		this.allowFracPos = allow;
	}

	public Map<Forecast, Portfolio> getMuPortfolios() {
		return muPortfolios;
	}

	public long getAsOf() {
		return asof;
	}

	public void setAsOf(long ts) {
		assert ts > 0;
		asof = ts;
	}

	public long getMostRecentPriceTs() {
		long date = 0;
		for (Position pos : positions.values()) {
			date = Math.max(date, pos.getPriceTs());
		}
		return date;
	}

	public Iterator<Map.Entry<Security, SecurityTradeInfo>> getSecurityTradeInfo() {
		return tradeinfo.entrySet().iterator();
	}

	public SecurityTradeInfo getSecurityTradeInfo(Security s) {
		return tradeinfo.get(s);
	}

	public int size() {
		return positions.size();
	}

	public Set<Security> getSecurities() {
		return positions.keySet();
	}

	private void setPosition(Position pos) {
		positions.put(pos.sec, pos);
	}

	public Position getPosition(Security s) {
		return positions.get(s);
	}

	public Collection<Position> getPositions() {
		return positions.values();
	}

	public List<Fill> getFills() {
		return fills;
	}

	public Pair<Double, Double> getLongShortValue() {
		double lv = 0.0, sv = 0.0;
		for (Position pos : positions.values()) {
			if (pos.getDoubleShares() == 0)
				continue;

			if (pos.notional() > 0) {
				lv += pos.notional();
			}
			else if (pos.notional() < 0) {
				sv += pos.notional();
			}
			else {
				log.warning("Can't value position: " + pos);
			}
		}
		return new Pair<Double, Double>(lv, sv);
	}

	public Double getNotional() {
		Pair<Double, Double> temp = getLongShortValue();
		return temp.first - temp.second;
	}

	public double getPnl() {
		double ret = 0.0;
		for (Position pos : positions.values()) {
			if (!Double.isNaN(pos.getPnl())) {
				ret += pos.getPnl();
			}
			else {
				log.warning("Could not value pnl for: " + pos);
			}
		}
		return ret;
	}

	public void updatePortfolioStats() {
		updatePortfolioStats(0.0, 0.0, 0.0);
	}
	
	public void updatePortfolioStats(double slippage, double costs, double estSlippage) {
		this.stats.updateStats(this, slippage, costs, estSlippage);
		if (muPortfoliosAutoUpdate) {
			for (Portfolio mp : muPortfolios.values()) {
				mp.stats.updateStats(mp, 0.0, 0.0, 0.0);
			}
		}
	}

	public void updatePrices(CalcResults calcres) {
		Map<Security, Attribute> prices = calcres.getResult(DailyPriceCalculator.lattr(DailyPriceCalculator.PRC, -1));
		updatePrices(prices, calcres.getAsOf());
	}

	// XXX These tow need to be combined!!!
	public void updatePrices(Map<Security, Attribute> prices, long asof) {
		log.info("Updating portfolio " + name + " from attributes:" + df.format(asof));
		for (Map.Entry<Security, Attribute> ent : prices.entrySet()) {
			Security sec = ent.getKey();
			Position pos = positions.get(sec);
			if (pos == null) {
				positions.put(sec, pos = new Position(sec));
			}
			pos.setLatestPrice(ent.getValue().asDouble(), asof);
		}
		setAsOf(asof);

		if (muPortfoliosAutoUpdate) {
			for (Portfolio mp : muPortfolios.values()) {
				mp.updatePrices(prices, asof);
			}
		}
	}

	public void updatePrices2(Map<Security, ? extends Price> priceMap, long asof) {
		log.info("Updating portfolio " + name + " from quotes:" + df.format(asof));
		for (Map.Entry<Security, ? extends Price> ent : priceMap.entrySet()) {
			Security sec = ent.getKey();
			Position pos = positions.get(sec);
			if (pos == null) {
				positions.put(sec, pos = new Position(sec));
			}
			Price db = ent.getValue();
			if (db == null)
				continue;
			pos.setLatestPrice(db.getPrice(), db.getTs());
		}
		setAsOf(asof);

		if (muPortfoliosAutoUpdate) {
			for (Portfolio mp : muPortfolios.values()) {
				mp.updatePrices2(priceMap, asof);
			}
		}
	}

	public void updateAttrs(CalcResults calcres, Map<Security, Integer> borrow, BorrowsUpdateMode bum) {
		log.info("Updating portfolio prices, etc to:" + df.format(calcres.getAsOf()));

		Map<Security, Attribute> prices = calcres.getResult(DailyPriceCalculator.lattr(DailyPriceCalculator.PRC, -1));
		Map<Security, Attribute> advs = calcres.getResult(DailyPriceCalculator.ADVP);
		// Map<Security, Attribute> lotsizes = calcres.getResult(PassThruCalculator.LOTSIZE);
		Map<Security, Attribute> lotsizes = new HashMap<Security, Attribute>();
		Map<Security, Attribute> expandable = calcres.getResult(SecurityFilter.EXPANDABLE);
		Map<Security, Attribute> tradeable = calcres.getResult(SecurityFilter.TRADEABLE);
		Map<Security, Attribute> borrowRates = calcres.getResult(BorrowCalculator.ADJ_BORROW_RATE);

		if (prices.size() == 0) {
			throw new RuntimeException("No Prices found!! " + DailyPriceCalculator.lattr(DailyPriceCalculator.PRC, -1));
		}
		if (lotsizes.size() == 0) {
			log.warning("No Lotsizes, using default of: " + defaultLotSize);
		}

		asof = calcres.getAsOf();
		int noborrow = 0;

		// Note how the portfolio is enhanced with the calcres securities
		Set<Security> allSecs = new HashSet<Security>(getSecurities());
		allSecs.addAll(calcres.getSecurities());
		for (Security sec : allSecs) {
			Position pos = positions.get(sec);
			SecurityTradeInfo sti = tradeinfo.get(sec);
			if (pos == null) {
				positions.put(sec, pos = new Position(sec));
			}
			if (sti == null) {
				tradeinfo.put(sec, sti = new SecurityTradeInfo(defaultLotSize, maxPosPctAdv));
			}

			Attribute prcAttr = prices.get(sec);
			if (prcAttr == null) {
				if (pos.getIntShares() != 0 || calcres.getSecurities().contains(pos.sec)) {
					log.warning("Could not find price for " + sec.getSecId() + " making untradeable. in calcres " + calcres.name());
				}
				sti.tradeable = false;
				continue;
			}
			pos.setLatestPrice(prcAttr.asDouble(), asof);

			sti.expandable = expandable.containsKey(sec);
			sti.tradeable = tradeable.containsKey(sec);
			if (sti.expandable && !sti.tradeable) {
				log.severe("Security " + sec.getSecId() + " expandable but not tradeable in " + calcres.name());
				sti.expandable = false;
			}

			if (advs.get(sec) != null) {
				sti.setAdvp(advs.get(sec).asDouble());
			}
			if (lotsizes.get(sec) != null) {
				sti.setLotSize((int) lotsizes.get(sec).asDouble());
			}
			if (borrow.get(sec) != null) {
				switch (bum) {
				case ABSOLUTE:{
					int secBorrow = borrow.get(sec);
					sti.setBorrow(secBorrow);
					break;
				}
				case INCREMENTAL: {
					//XXX note how the second term is a negative quantity, so it must be subtracted
					int secBorrow = borrow.get(sec) - Math.min(0, pos.getIntShares());
					sti.setBorrow(secBorrow);
					break;
				}
				case IGNORE:
					break;
				default:
					throw new RuntimeException("What on earth?");
				}
			}
			else {
				noborrow++;
				log.warning("No borrow found on " + sec + " setting to 0!");
				sti.setBorrow(0);
			}
			sti.borrow_rate = borrowRates.containsKey(sec) ? borrowRates.get(sec).asDouble() : 0.0;
		}

		if (muPortfoliosAutoUpdate) {
			for (Portfolio mp : muPortfolios.values()) {
				mp.updatePrices(calcres);
			}
		}
	}

	public void updateSplitsAndDividends(CalcResults calcres, boolean casheqAffectsCash) {
		Map<Security, Attribute> dividends = calcres.getResult(DailyPriceCalculator.DIV);
		Map<Security, Attribute> splits = calcres.getResult(DailyPriceCalculator.SPLIT);
		Map<Security, Attribute> casheqs = calcres.getResult(DailyPriceCalculator.CASHEQ);
		updateSplitsAndDividends(dividends, splits, casheqs, casheqAffectsCash);
	}

	private void updateSplitsAndDividends(Map<Security, Attribute> dividends, Map<Security, Attribute> splits, Map<Security, Attribute> casheqs,
			boolean casheqAffectsCash) {
		for (Map.Entry<Security, Attribute> split : splits.entrySet()) {
			if (split.getValue().asDouble() == 1)
				continue;
			CapAdjustment adj = new CapAdjustment(split.getKey(), Type.SPLIT, split.getValue().asDouble(), 0, SizeRefType.SELF, "");
			handleAdjustment(adj);
		}
		for (Map.Entry<Security, Attribute> div : dividends.entrySet()) {
			if (div.getValue().asDouble() == 0)
				continue;
			CapAdjustment adj = new CapAdjustment(div.getKey(), Type.DIV, div.getValue().asDouble(), 0, SizeRefType.SELF, "");
			handleAdjustment(adj);
		}
		// /XXX note how casheq is converted to div
		if (casheqAffectsCash) {
			for (Map.Entry<Security, Attribute> casheq : casheqs.entrySet()) {
				if (casheq.getValue().asDouble() == 0)
					continue;
				CapAdjustment adj = new CapAdjustment(casheq.getKey(), Type.DIV, casheq.getValue().asDouble(), 0, SizeRefType.SELF, "");
				handleAdjustment(adj);
			}
		}
		//XXX /We are already doing this in handleAdjustment
		// if (muPortfoliosAutoUpdate) {
		// for (Portfolio mp : muPortfolios.values()) {
		// mp.updateSplitsAndDividends(dividends, splits, casheqs, casheqAffectsCash);
		// }
		// }
	}

	public List<Fill> addIdealTrades(Collection<Order> orders, Map<Security, Price> fillPrices, long fillTs) {
		Vector<Fill> fills = new Vector<Fill>();
		for (Order o : orders) {
			if (o.shares == 0)
				continue;
			//XXX things are already rounded in OptMaster.optimize()
			//int lotsize = getSecurityTradeInfo(o.sec).lotsize;
			//double tradeShares = Math.ceil(Math.abs(o.shares) / lotsize) * lotsize * Math.signum(o.shares);
			//if (Math.abs(tradeShares) >= lotsize)
			Fill fill = new Fill(o.sec, (fillTs > 0)? fillTs : o.ts, o.shares, (fillPrices != null && fillPrices.containsKey(o.sec))? fillPrices.get(o.sec).getPrice() : o.prc, o, -1);
			fills.add(fill);
			handleFill(fill);
		}
		return fills;
	}

	public void loadAdjustmentsFile(File adjfile) throws Exception {
		for (CapAdjustment adj : CapAdjustment.loadCapAdjustmentsFile(adjfile))
			handleAdjustment(adj);
	}

	public void handleAdjustment(CapAdjustment adj) {
		log.finest("Processing adjustment: " + adj);

		// /XXX handle first the allocation to mu portfolios, because we need an accurate count of the current position (basically when adj is a fill)
		if (muPortfoliosAutoUpdate) {
			addToMuPortfolios(adj);
		}

		Position pos = getPosition(adj.sec);
		if (pos != null) {
			pos.adjust(adj, this);
		}
		else if (pos == null && (adj.type == Type.CORP_CASH || adj.type == Type.CORP_SHARES || adj.type == Type.FILL)) {
			pos = new Position(adj.sec);
			positions.put(adj.sec, pos);
			log.severe("Handled adjustment pointing to a non-existent position: " + adj);
			pos.adjust(adj, this);
		}
	}

	public void loadFillsFile(File fillsfile) throws Exception {
		for (Fill fill : PortfolioUtils.loadFillsFile(fillsfile))
			handleFill(fill);
	}

	public void handleFill(Fill fill) {
		log.finest("Processing fill: " + fill);

		// /XXX handle first the allocation to mu portfolios, because we need an accurate count of the current position
		if (muPortfoliosAutoUpdate) {
			addToMuPortfolios(fill);
		}

		Position pos = getPosition(fill.sec);
		if (pos == null) {
			pos = new Position(fill.sec);
			positions.put(fill.sec, pos);
		}
		pos.add(fill, this);
		fills.add(fill);
	}

	private void addToMuPortfolios(Fill fill) {
		for (Map.Entry<Forecast, Fill> mu : fill.allocateMus(this, muPortfolios).entrySet()) {
			Portfolio p = muPortfolios.get(mu.getKey());
			if (p == null) {
				p = newPortfolio(mu.getKey().name);
				p.allowFracPos = true;
				muPortfolios.put(mu.getKey(), p);
			}
			p.handleFill(mu.getValue());
		}
	}

	private void addToMuPortfolios(CapAdjustment adj) {
		//If a cap adjustment is a fill, explicitely treat as a fill which will dump it into the NONE portfolio
		if (adj.type == Type.FILL) {
			Fill fill = new Fill(adj.sec, 1, adj.sizeRef, adj.adj, null, 0);
			addToMuPortfolios(fill);
		}
		//Absolute sizes that are not fills are hard... Ignore them for now, should be super rare
		else if (adj.sizeRefType == SizeRefType.ABSOLUTE) {
			log.warning("Not pushing to mu portfolios cap adj with absolute size reference " + adj.toString());
			return;
		}
		//Push the adjustment to each individual portfolio
		else {
			for (Portfolio mp : muPortfolios.values()) {
				mp.handleAdjustment(adj);
			}
		}
	}

	private Portfolio newPortfolio(String name) {
		Portfolio p = new Portfolio(name);
		for (Position pos : positions.values()) {
			Position newpos = new Position(pos.sec);
			if (pos.getLatestPrice() > Double.NaN) {
				newpos.setLatestPrice(pos.getLatestPrice(), pos.getPriceTs());
			}
			p.setPosition(newpos);
		}
		return p;
	}

	public void clearFills() {
		fills.clear();
		if (muPortfoliosAutoUpdate) {
			for (Portfolio mp : muPortfolios.values()) {
				mp.clearFills();
			}
		}
	}
	
	public void dumpFills(String dir) throws Exception {
		Pair<String, Writer> wr = FileUtils.openDataDumpFile(dir, "fills", asof, false);
		Writer writer = wr.second;
		log.info("Dumping fills to " + FileUtils.dataDumpFileName(dir, "fills", asof));
		writer.write(Fill.dumpHeader() + "\n");
		for (Fill f : fills) {
			writer.write(f.toString() + "\n");
		}
		writer.close();
		FileUtils.finalizeFile(wr.first);
	}

	public void dumpStats(String dir) throws Exception {
		Pair<String, Writer> wr = FileUtils.openDataDumpFile(dir, "stats", asof, false);
		Writer writer = wr.second;
		log.info("Dumping stats to " + FileUtils.dataDumpFileName(dir, "stats", asof));
		stats.dump(writer);
		writer.close();
		for (Map.Entry<Forecast, Portfolio> mus : muPortfolios.entrySet()) {
			Pair<String, Writer> muwr = FileUtils.openDataDumpFile(dir, mus.getKey().name + ".stats", asof, false);
			writer = muwr.second;
			mus.getValue().stats.dump(writer);
			writer.close();
			FileUtils.finalizeFile(muwr.first);
		}
		FileUtils.finalizeFile(wr.first);
	}

	public void dumpPositions(String dir) throws Exception {
		Pair<String, Writer> wr = FileUtils.openDataDumpFile(dir, "pos", asof, false);
		Writer writer = wr.second;
		log.info("Dumping positions to " + FileUtils.dataDumpFileName(dir, "pos", asof));
		writer.write(Position.dumpHeader() + "\n");
		for (Position pos : positions.values()) {
			writer.write(pos.dumpOutput(allowFracPos) + "\n");
		}
		writer.close();
		FileUtils.finalizeFile(wr.first);
	}
	
	public void dumpMuPortfolios(String dir) throws Exception {
		if (muPortfolios == null) {
			return;
		}
		for (Map.Entry<Forecast, Portfolio> mus : muPortfolios.entrySet()) {
			mus.getValue().dumpPositions(dir + "/" + mus.getKey().name + ":" + mus.getKey().type);
		}
	}

	public void savePositions(File filepath) throws Exception {
		Writer writer = FileUtils.makeWriter(filepath);
		writer.write(Position.dumpHeader() + "\n");
		for (Position pos : positions.values()) {
			writer.write(pos.dumpOutput(allowFracPos) + "\n");
		}
		writer.close();
	}

	public void saveMuPositions(File dirpath) throws Exception {
		if (muPortfolios == null) {
			return;
		}
		for (Map.Entry<Forecast, Portfolio> mus : muPortfolios.entrySet()) {
			mus.getValue().savePositions(new File(dirpath, mus.getKey().name + ":" + mus.getKey().type + ".txt"));
		}
	}

	public void restore(File posFile) throws Exception {
		BufferedReader reader = FileUtils.openFileReader(posFile);
		// first line is header
		reader.readLine();
		for (String line = ""; line != null; line = reader.readLine()) {
			if (line.length() <= 0)
				continue;
			Position pos = Position.restore(line);
			setPosition(pos);
			tradeinfo.put(pos.sec, new SecurityTradeInfo(defaultLotSize, maxPosPctAdv));
		}
		reader.close();
	}

	public void fullRestore(File posFile, File muPosDir) throws Exception {
		restore(posFile);
		File[] muFiles = muPosDir.listFiles();
		if (muFiles == null || muPortfolios == null) {
			return;
		}

		for (File muFile : muFiles) {
			String[] tokens = muFile.getName().split("[:\\.]");
			Forecast fcast = new Forecast(tokens[0], Forecast.Type.valueOf(tokens[1]));
			Portfolio muPort = new Portfolio();
			muPort.allowFractionalPositions(true);
			muPort.restore(muFile);
			muPortfolios.put(fcast, muPort);
		}
	}

	public void dumpReport() {
		for (Position pos : positions.values()) {
			System.out.println(pos.pnlLine());
		}
	}

	public String toString() {
		return df.format(asof) + "|" + positions.size() + "|" + fills.size();
	}
	
	public Portfolio getTradingPortfolio() {
		Portfolio tradingPortfolio = new Portfolio();
		tradingPortfolio.allowFractionalPositions(allowFracPos);
		for (Fill fill : fills) {
			tradingPortfolio.handleFill(fill);
		}
		for (Position cpos : positions.values()) {
			Position tpos = tradingPortfolio.getPosition(cpos.sec);
			if (tpos != null) {
				tpos.setLatestPrice(cpos.getLatestPrice(), cpos.getPriceTs());
			}
		}
		return tradingPortfolio;
	}
}
