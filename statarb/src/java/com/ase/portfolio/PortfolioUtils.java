package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.Vector;
import java.util.logging.Logger;
import java.util.regex.Pattern;

import javax.print.DocFlavor;

import ase.calculator.Forecast;
import ase.calculator.Forecast.Type;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class PortfolioUtils {
	protected static final Logger log = LoggerFactory.getLogger(PortfolioUtils.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();
	protected static Pattern barSeparator = Pattern.compile("\\|");
	public static final UnifiedDataSource uSource = new UnifiedDataSource(false);

	public static Map<Long, Long> loadExecServerOrderTs(String location, long currentdate) throws IOException {
		Map<Long, Long> result = new HashMap<Long, Long>();
		File tsfile = new File(location +"/"+df.toYYYYMMDD(currentdate)+"/exec_order_ts.txt");
		if (!tsfile.exists())
			return result;
		BufferedReader reader = FileUtils.openFileReader(tsfile);
		String line;
		while ((line=reader.readLine())!=null) {
			String[] tokens = barSeparator.split(line);
			Long orderid = Long.valueOf(tokens[0]);
			Long ts = Long.valueOf(tokens[1]);
			result.put(orderid, ts);
		}
		
		return result;
	}
	
	public static Map<Integer, Map<Forecast, Double>> loadMus(File muFile) throws IOException {
		HashMap<Integer, Map<Forecast, Double>> result = new HashMap<Integer, Map<Forecast, Double>>();

		BufferedReader reader = FileUtils.openFileReader(muFile);
		String line;

		while ((line = reader.readLine()) != null) {
			String[] tokens = barSeparator.split(line);
			Integer secid = Integer.parseInt(tokens[0]);
			String forecast = tokens[1];
			Double value = Double.parseDouble(tokens[2]);

			Map<Forecast, Double> secForecasts = result.get(secid);
			if (secForecasts == null) {
				secForecasts = new HashMap<Forecast, Double>();
				result.put(secid, secForecasts);
			}
			secForecasts.put(new Forecast(forecast, Type.MU), value);
		}

		reader.close();
		return result;
	}

	public static Vector<Order> loadOrders(File file) throws IOException {
		Vector<Order> result = new Vector<Order>();
		BufferedReader reader = FileUtils.openFileReader(file);
		String line;
		while ((line = reader.readLine()) != null) {
			if (!line.startsWith("O|"))
				continue;

			String[] tokens = barSeparator.split(line);
			int ii = 1;
			Long orderid = Long.parseLong(tokens[ii++]);
			Integer secid = Integer.parseInt(tokens[ii++]);
			Long ts = Long.parseLong(tokens[ii++]);
			Integer shares = Integer.parseInt(tokens[ii++]);
			Double dutil = Double.parseDouble(tokens[ii++]);
			Double dmu = Double.parseDouble(tokens[ii++]);
			Double drisk = Double.parseDouble(tokens[ii++]);
			Double eslip = Double.parseDouble(tokens[ii++]);
			Double costs = Double.parseDouble(tokens[ii++]);
			Double aggr = Double.parseDouble(tokens[ii++]);
			Double prc = Double.parseDouble(tokens[ii++]);

			Order order = new Order(orderid, new Security(secid), ts, shares, null, dutil, dmu, drisk, eslip, costs, aggr, prc);
			result.add(order);
		}

		reader.close();
		return result;
	}

	public static Map<Integer, Order> loadOrders(File file, Map<Integer, Map<Forecast, Double>> mus) throws IOException {
		HashMap<Integer, Order> result = new HashMap<Integer, Order>();

		BufferedReader reader = FileUtils.openFileReader(file);
		String line;

		while ((line = reader.readLine()) != null) {
			if (!line.startsWith("O|"))
				continue;

			String[] tokens = barSeparator.split(line);
			int ii = 1;
			Long orderid = Long.parseLong(tokens[ii++]);
			Integer secid = Integer.parseInt(tokens[ii++]);
			Long ts = Long.parseLong(tokens[ii++]);
			Integer shares = Integer.parseInt(tokens[ii++]);
			Double dutil = Double.parseDouble(tokens[ii++]);
			Double dmu = Double.parseDouble(tokens[ii++]);
			Double drisk = Double.parseDouble(tokens[ii++]);
			Double eslip = Double.parseDouble(tokens[ii++]);
			Double costs = Double.parseDouble(tokens[ii++]);
			Double aggr = Double.parseDouble(tokens[ii++]);
			Double prc = Double.parseDouble(tokens[ii++]);

			Map<Forecast, Double> secMus = mus.get(secid);
			if (secMus == null) {
				log.severe("Failed to find mus for order of secid " + secid + " in file " + file);
				continue;
			}

			Order order = new Order(orderid, new Security(secid), ts, shares, secMus, dutil, dmu, drisk, eslip, costs, aggr, prc);
			if (result.put(secid, order) != null) {
				log.severe("Encountered more than one orders for secid " + secid + " in file " + file);
			}
		}

		reader.close();
		return result;
	}

	protected static Map<Integer, NavigableMap<Long, Order>> loadAllOrders(String location, long currentDate) throws Exception {
		Map<Integer, NavigableMap<Long, Order>> allOrders = new HashMap<Integer, NavigableMap<Long, Order>>();

		String date = df.toYYYYMMDD(currentDate);
		File muLocation = new File(location + "/" + date + "/mus");
		File orderLocation = new File(location + "/" + date + "/orders");

		if (!muLocation.exists() || !orderLocation.exists()) {
			log.severe("Failed to find mus orders subfolder in " + muLocation.toString());
			return null;
		}

		NavigableMap<Long, File> muFiles = FileUtils.getDumpedFiles(muLocation.getPath(), FileUtils.MUS_PATTERN);
		NavigableMap<Long, File> orderFiles = FileUtils.getDumpedFiles(orderLocation.getPath(), FileUtils.ORDERS_PATTERN);

		if (orderFiles == null)
			return null;

		for (Map.Entry<Long, File> tfe : orderFiles.entrySet()) {
			File orderFile = tfe.getValue();
			File muFile = muFiles.get(tfe.getKey());
			Long ts = tfe.getKey();

			if (muFile == null) {
				log.severe("Failed to match order file " + orderFile + " with a corresponding mus file");
				continue;
			}

			Map<Integer, Order> orders = loadOrders(orderFile, loadMus(muFile));
			for (Map.Entry<Integer, Order> soe : orders.entrySet()) {
				Integer secid = soe.getKey();
				Order order = soe.getValue();

				NavigableMap<Long, Order> secOrders = allOrders.get(secid);
				if (secOrders == null) {
					secOrders = new TreeMap<Long, Order>();
					allOrders.put(secid, secOrders);
				}
				secOrders.put(ts, order);
			}
		}

		return allOrders;
	}

	public static List<Fill> loadMuifiedFills(String location, long currentDate, boolean oldSystem) throws Exception {
		File fillsFile = new File(location + "/" + df.toYYYYMMDD(currentDate) + "/"
				+ (oldSystem ? OldSystemUtils.OLD_DAY_FILLS : Portfolio.dayFillsFilename(currentDate)));

		if (!fillsFile.exists()) {
			log.severe("Failed to locate fills file " + fillsFile.getPath());
			return null;
		}

		// Lazy, recreate fills
		List<Fill> fills = oldSystem ? OldSystemUtils.loadOldFillsFile(fillsFile) : PortfolioUtils.loadFillsFile(fillsFile);
		List<Fill> assignedFills = new Vector<Fill>();
		Map<Integer, NavigableMap<Long, Order>> orders = loadAllOrders(location, currentDate);

		if (orders == null) {
			log.warning("Failed to associate all fills with orders");
			return fills;
		}

		for (Fill fill : fills) {
			// locate order
			Security sec = fill.sec;
			NavigableMap<Long, Order> secOrders = orders.get(sec.getSecId());
			if (secOrders == null) {
				log.warning("Failed to associate fill " + fill.toString() + " with order");
				assignedFills.add(fill);
				continue;
			}
			boolean isAssigned = false;
			Map.Entry<Long, Order> o = secOrders.floorEntry(fill.ts);
			while (!isAssigned) {
				if (o == null) {
					log.warning("Failed to associate fill " + fill.toString() + " with order");
					assignedFills.add(fill);
					break;
				}
				if ((Time.toYYYYMMDD(currentDate) > 20110622) && (o.getValue().orderid != fill.orderid)) {
					o = secOrders.lowerEntry(o.getKey());
				}
				else {
					assignedFills.add(new Fill(fill.sec, fill.ts, fill.shares, fill.price, o.getValue(), fill.fillid, fill.venue, fill.liquidity, fill.orderid,
							fill.tactic));
					isAssigned = true;
				}
			}
		}
		return assignedFills;
	}

	public static Pair<List<Order>, List<Fill>> loadSimOrdersAndFills(File ordersFile, File fillsFile, File musFile) throws Exception {
		Map<Integer, Map<Forecast, Double>> secid2mus = loadMus(musFile);
		Map<Integer, Order> secid2orders = loadOrders(ordersFile, secid2mus);
		List<Fill> fillsWithoutOrders = loadFillsFile(fillsFile);

		Vector<Fill> fills = new Vector<Fill>();
		Vector<Order> orders = new Vector<Order>();
		for (Fill fill : fillsWithoutOrders) {
			//XXX we rely on the fact that there is a single fill per order in sim. we could change that and match on orderid if needed
			Order order = secid2orders.get(fill.sec.getSecId());
			fills.add(new Fill(fill.sec, fill.ts, fill.shares, fill.price, order, fill.fillid, fill.venue, fill.liquidity, fill.orderid, fill.tactic));
		}

		orders.addAll(secid2orders.values());
		return new Pair<List<Order>, List<Fill>>(orders, fills);
	}

	public static Portfolio restoreDayPortfolio(String location, long currentDate, boolean withMus) throws Exception {
		String date = df.toYYYYMMDD(currentDate);
		File sodFile = new File(location + "/" + date + "/" + Portfolio.SOD_PORTFOLIO);
		File musDir = new File(location + "/" + date + "/" + "muSod");

		if (sodFile.exists() && (!withMus || musDir.exists())) {
			Portfolio portfolio = new Portfolio();
			portfolio.fullRestore(sodFile, musDir);
			return portfolio;
		}
		else {
			return null;
		}
	}

	public static PortfolioStats getIntradayStats(String location, long currentDate, Exchange.Type exch, long asof, int interval) throws Exception {
		File dir = new File(location);
		File currentDateDir = new File(dir, df.toYYYYMMDD(currentDate));

		Portfolio portfolio = new Portfolio();
		portfolio.restore(new File(currentDateDir, Portfolio.SOD_PORTFOLIO));
		portfolio.updatePortfolioStats();

		File adjsFile = new File(currentDateDir, Portfolio.DAY_CAPADJUSTMENTS);
		File fillsFile = new File(currentDateDir, Portfolio.dayFillsFilename(currentDateDir));

		if (adjsFile.exists()) {
			for (CapAdjustment adj : CapAdjustment.loadCapAdjustmentsFile(adjsFile)) {
				portfolio.handleAdjustment(adj);
			}
		}
		else {
			log.warning("No cap adjustment file found: " + adjsFile.toString());
		}

		long open = Exchange.openTime(currentDate, exch);
		long close = Exchange.closeTime(currentDate, exch);
		
		NavigableMap<Long, List<Fill>> fills = new TreeMap<Long, List<Fill>>();
		if (fillsFile.exists()) {
			for (Fill fill : PortfolioUtils.loadFillsFile(fillsFile)) {
				long modTs = Math.min(fill.ts, close);
				List<Fill> tsFills = fills.get(modTs);
				if (tsFills == null) {
					tsFills = new LinkedList<Fill>();
					fills.put(modTs, tsFills);
				}
				tsFills.add(fill);
			}
		}
		else {
			log.warning("No fills file found: " + fillsFile.toString());
		}

		long from = open;
		long to = from + Time.MILLIS_PER_MINUTE * interval;
		//Since we will be using bars, preload them
		uSource.barSource.preload(portfolio.getSecurities(), currentDate, currentDate);
		for (; to <= Math.min(close, asof); from = to, to += Time.MILLIS_PER_MINUTE * interval) {
			for (List<Fill> tsFills : fills.subMap(from, false, to, true).values())
				for (Fill fill : tsFills)
					portfolio.handleFill(fill);
			portfolio.updatePrices2(uSource.getPrices(portfolio.getSecurities(), to, exch, false), to);
			portfolio.updatePortfolioStats();
		}
			
		return portfolio.stats;
	}

	/**
	 * 
	 * @param location
	 *            e.g. /apps/ase/run/useq-live
	 * @param exch
	 * @param currentDate
	 *            The date (Time.midnight(currentDate)) which we will be using as a basis
	 * @param oldSystem
	 *            Old or new system fills/adjs
	 * @param live
	 *            Get live prices
	 * @param withMus
	 *            Load mu portfolios
	 * @param asof
	 *            If 0, as of closing time+1hour of currentdate. Else, sets point in day within current day
	 * @return
	 * @throws Exception
	 */
	public static Pair<Portfolio, Portfolio> processDayPortfolio(String location, Exchange.Type exch, long currentDate, boolean oldSystem, boolean live,
			boolean withMus, long asof) throws Exception {
		if (asof > 0 && Time.midnight(currentDate) != Time.midnight(asof)) {
			log.severe("currentDate and asof point to different dates. I smell a bug");
		}

		Portfolio sodPortfolio = new Portfolio();
		Portfolio eodPortfolio = new Portfolio();
		Pair<Portfolio, Portfolio> result = new Pair<Portfolio, Portfolio>(sodPortfolio, eodPortfolio);
		sodPortfolio.setMuPortfoliosAutoUpdate(withMus);
		eodPortfolio.setMuPortfoliosAutoUpdate(withMus);

		String date = df.toYYYYMMDD(currentDate);
		sodPortfolio.fullRestore(new File(location + "/" + date + "/" + Portfolio.SOD_PORTFOLIO), new File(location + "/" + date + "/" + "muSod"));
		sodPortfolio.updatePortfolioStats();

		eodPortfolio.fullRestore(new File(location + "/" + date + "/" + Portfolio.SOD_PORTFOLIO), new File(location + "/" + date + "/" + "muSod"));
		eodPortfolio.updatePortfolioStats();

		File dir = new File(location);
		File currentDateDir = new File(dir, df.toYYYYMMDD(currentDate));
		File adjsFile = oldSystem ? new File(currentDateDir, OldSystemUtils.OLD_DAY_FAKE_FILLS) : new File(currentDateDir, Portfolio.DAY_CAPADJUSTMENTS);
		File fillsFile = oldSystem ? new File(currentDateDir, OldSystemUtils.OLD_DAY_FILLS) : new File(currentDateDir,
				Portfolio.dayFillsFilename(currentDateDir));

		// recalibrate asof
		boolean eod = false;
		if (live) {
			asof = Time.now();
		}
		else if (asof == 0) {
			// asof=0 is dummy for endof day
			asof = Exchange.closeTime(currentDate, exch);
			eod = true;
		}

		if (adjsFile.exists()) {
			List<CapAdjustment> adjs = null;
			if (oldSystem) {
				adjs = OldSystemUtils.loadOldFakeFillsFile(adjsFile);
			}
			else {
				adjs = CapAdjustment.loadCapAdjustmentsFile(adjsFile);
			}
			for (CapAdjustment adj : adjs) {
				eodPortfolio.handleAdjustment(adj);
			}
		}
		else {
			log.severe("No cap adjustment file found: " + adjsFile.toString());
		}

		if (fillsFile.exists()) {
			List<Fill> fills = null;
			if (withMus) {
				fills = PortfolioUtils.loadMuifiedFills(location, currentDate, oldSystem);
			}
			else if (oldSystem) {
				fills = OldSystemUtils.loadOldFillsFile(fillsFile);
			}
			else {
				fills = PortfolioUtils.loadFillsFile(fillsFile);
			}
			for (Fill fill : fills) {
				if (eod || fill.ts <= asof) {
					eodPortfolio.handleFill(fill);
				}
			}
		}
		else {
			log.severe("No fills file found: " + fillsFile.toString());
		}

		// UPDATE PRICES
		eodPortfolio.updatePrices2(uSource.getPrices(eodPortfolio.getSecurities(), asof, exch, live), asof);
		eodPortfolio.updatePortfolioStats();

		return result;
	}

	public static Portfolio portfolioAsOf(long asof) throws Exception {
		Exchange.Type exch = Exchange.Type.valueOf(System.getenv("PRIMARY_EXCHANGE"));
		return portfolioAsOf(System.getenv("ROOT_DIR") + "/run/" + System.getenv("STRAT"), exch, asof);
	}

	public static Portfolio portfolioAsOf(String location, Exchange.Type exch, long asof) throws Exception {
		long currentDate = Exchange.isTradingDay(asof, exch) ? Time.midnight(asof) : Exchange.prevTradingDay(asof, exch);
		return processDayPortfolio(location, exch, currentDate, false, false, false, asof).second;
	}

	public static void main(String[] args) throws Exception {
		long asof = args.length > 0 ? Long.parseLong(args[0]) : Time.now();
		Portfolio port = portfolioAsOf(asof);
		for (Position p : port.getPositions()) {
			System.out.println(p.sec.getSecId() + "|" + p.getIntShares());
		}
	}

	public static void updateStats(Map<Security, PortfolioStats> secStats, File posFile, boolean insertZero) throws Exception {
		Portfolio port = new Portfolio();
		if (posFile.exists()) {
			port.restore(posFile);
			port.setAsOf(port.getMostRecentPriceTs());
			for (Position pos : port.getPositions()) {
				Security sec = pos.sec;
				PortfolioStats st = secStats.get(sec);
				if (st == null) {
					st = new PortfolioStats();
					if (insertZero)
						st.addZero();
					secStats.put(sec, st);
				}
				st.add(port.getAsOf(), pos.notional() >= 0 ? pos.notional() : 0.0, pos.notional() < 0 ? pos.notional() : 0.0, pos.getPnl(),
						pos.getDollarsTraded(), 0.0, 0.0, 0.0, 0.0);
			}
		}
		else {
			log.warning("Couldn't find portfolio file " + posFile.toString());
		}
	}

	public static void updateStats(PortfolioStats stats, File posFile) throws Exception {
		updateStats(stats, posFile, 0.0, 0.0, 0.0);
	}

	public static void updateStats(PortfolioStats stats, File posFile, File orderFile) throws Exception {
		if (orderFile != null && orderFile.exists()) {
			List<Order> orders = PortfolioUtils.loadOrders(orderFile);
			Pair<Double, Double> p = calculateCosts(orders);
			updateStats(stats, posFile, p.first, p.second, p.first);
		}
		else {
			log.severe("Failed to locate orderFile " + orderFile);
			updateStats(stats, posFile, 0.0, 0.0, 0.0);
		}
	}

	public static void updateStats(PortfolioStats stats, File posFile, double slippage, double costs, double estSlippage) throws Exception {
		Portfolio port = new Portfolio();
		if (posFile.exists()) {
			port.restore(posFile);
			port.setAsOf(port.getMostRecentPriceTs());
			stats.updateStats(port, slippage, costs, estSlippage);
		}
		else {
			log.warning("Couldn't find portfolio file " + posFile.toString());
		}
	}

	public static Pair<Double, Double> calculateCosts(Collection<Order> orders) {
		Double slippage = 0.0;
		Double costs = 0.0;
		for (Order o : orders) {
			slippage += o.eslip;
			costs += 6e-4 * Math.abs(o.shares);
		}

		return new Pair<Double, Double>(slippage, costs);
	}

	public static List<Fill> loadFillsFile(File fillsfile) throws Exception {
		Fill.log.info("Loading fills file: " + fillsfile.getAbsolutePath());
		BufferedReader reader = FileUtils.openFileReader(fillsfile);
		Vector<Fill> fills = new Vector<Fill>();
		// skip header
		reader.readLine();
		int cnt = 0;
		for (String line = ""; line != null; line = reader.readLine()) {
			if (line.length() <= 0 || !line.startsWith("F"))
				continue;
			// handleFill(Fill.restore(line));
			Fill fill = Fill.restoreFromFillsFile(line);
			if (!(fill.sec.getSecId() > 0)) {
				Fill.log.severe("Encountered a fills line with bad secid: " + line);
				Fill.log.severe("Skipping...");
				continue;
			}
			fills.add(fill);
			cnt++;
		}
		Fill.log.info("Loaded " + cnt + " fills.");
		reader.close();
		return fills;
	}

	public static void dumpFills(String dir, List<Fill> fills, long asof) throws Exception {
		Pair<String, Writer> wr = FileUtils.openDataDumpFile(dir, "fills", asof, false);
		Writer writer = wr.second;
		writer.write(Fill.dumpHeader() + "\n");
		for (Fill f : fills) {
			writer.write(f.toString() + "\n");
		}
		writer.close();
		FileUtils.finalizeFile(wr.first);
	}
}
