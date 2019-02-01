package ase.apps;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.Writer;
import java.lang.management.ManagementFactory;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.SortedSet;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.OptionBuilder;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.PosixParser;

import ase.apps.DailyManager.Operation;
import ase.apps.DailyManager.OutputType;
import ase.calculator.Forecast;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Price;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.portfolio.Fill;
import ase.portfolio.Order;
import ase.portfolio.Portfolio;
import ase.portfolio.PortfolioStats;
import ase.portfolio.PortfolioUtils;
import ase.reports.PerformanceReport;
import ase.reports.Report;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;

public class SimManager {
	protected static enum ReportingType {
		REGULAR, EOD, POSITION
	};

	protected static enum PenaltyType {
		NONE, DELAY, SLIPPAGE
	};

	protected static final Logger log = LoggerFactory.getLogger(SimManager.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public static final String CALCRES_DIR = "calcres";
	public static final String ORDER_DIR = "orders";
	public static final String MUS_DIR = "mus";
	public static final String FILLS_DIR = "fills";
	public static final String POSITION_DIR = "positions";
	public static final String STATS_DIR = "stats";

	protected final File simdir;
	protected final File reportdir;
	protected final Exchange.Type exch;
	protected final UnifiedDataSource usource;

	public SimManager(String location, String reports, Exchange.Type exch) {
		this.simdir = new File(location);
		this.reportdir = new File(reports);
		this.exch = exch;
		this.usource = new UnifiedDataSource(false);
	}

	@Deprecated
	private static Vector<String> extractSlippageFromOrders(File orderDirectory) throws Exception {
		Vector<String> result = new Vector<String>();
		result.add("0");
		NavigableMap<Long, File> orderFiles = FileUtils.getDumpedFiles(orderDirectory.toString(), FileUtils.ORDERS_PATTERN);
		for (File of : orderFiles.values()) {
			BufferedReader reader = FileUtils.openFileReader(of);
			String line;
			double totalSlip = 0;
			while ((line = reader.readLine()) != null) {
				if (!line.startsWith("O|"))
					continue;
				String[] tokens = line.split("\\|");
				double eslip = Double.parseDouble(tokens[8]);
				assert eslip >= 0;
				totalSlip += eslip;
			}
			result.add(df.fformat(totalSlip));
		}
		return result;
	}

	private Triplet<Double, Double, Double> calculateCosts(File orderFile, File fillsFile) throws Exception {
		return calculateCosts(PortfolioUtils.loadOrders(orderFile), PortfolioUtils.loadFillsFile(fillsFile));
	}

	private Triplet<Double, Double, Double> calculateCosts(List<Order> orders, List<Fill> fills) throws Exception {
		Map<Security, Order> ordersMap = new HashMap<Security, Order>();
		for (Order o : orders) {
			ordersMap.put(o.sec, o);
		}

		Map<Security, Fill> fillsMap = new HashMap<Security, Fill>();
		for (Fill f : fills) {
			fillsMap.put(f.sec, f);
		}

		return calculateCosts(ordersMap, fillsMap);
	}

	private Triplet<Double, Double, Double> calculateCosts(Map<Security, Order> orders, Map<Security, Fill> fills) {
		double slippage = 0;
		double cost = 0;
		double estSlippage = 0;
		for (Fill fill : fills.values()) {
			Order order = orders.get(fill.sec);
			assert order != null && fill.shares == order.shares;

			slippage += (fill.price - order.prc) * fill.shares;
			cost += 6e-4 * Math.abs(fill.shares);
			estSlippage += order.eslip;
		}

		return new Triplet<Double, Double, Double>(slippage, cost, estSlippage);
	}

	private List<Fill> penalizeOrdersBySlippage(List<Order> orders, double slippagePerDollar) {
		Vector<Fill> fills = new Vector<Fill>();

		for (Order o : orders) {
			if (o.shares == 0)
				continue;
			double prc = (o.shares > 0) ? o.prc * (1 + slippagePerDollar) : o.prc * (1 - slippagePerDollar);
			fills.add(new Fill(o.sec, o.ts, o.shares, prc, o, -1));
		}
		return fills;
	}

	private List<Fill> penalizeOrderByDelay(List<Order> orders, int mins, Set<Security> secs, long ts) throws Exception {
		Vector<Fill> fills = new Vector<Fill>();
		long asof = ts + mins * Time.MILLIS_PER_MINUTE;
		Map<Security, Price> prices = usource.getPriceAtTs(secs, asof, exch);
		for (Order o : orders) {
			if (o.shares == 0)
				continue;
			Double prc = (prices.containsKey(o.sec)) ? prices.get(o.sec).getPrice() : o.prc;
			fills.add(new Fill(o.sec, o.ts, o.shares, prc, o, -1));
		}
		return fills;
	}

	private Pair<PortfolioStats, Map<Forecast, PortfolioStats>> gatherStats(File basedir, Map<ReportingType, Long> reportingTypes, PenaltyType penalty, Double penaltyParam, boolean useSodPort, boolean getMuPortfolioStats) throws Exception {
		NavigableMap<Long, File> posFiles = FileUtils.getDumpedFiles(basedir.toString() + "/" + POSITION_DIR, FileUtils.POS_PATTERN);
		NavigableMap<Long, File> orderFiles = FileUtils.getDumpedFiles(basedir.toString() + "/" + ORDER_DIR, FileUtils.ORDERS_PATTERN);
		NavigableMap<Long, File> muFiles = FileUtils.getDumpedFiles(basedir.toString() + "/" + MUS_DIR, FileUtils.MUS_PATTERN);
		NavigableMap<Long, File> fillsFiles = FileUtils.getDumpedFiles(basedir.toString() + "/" + FILLS_DIR, FileUtils.FILLS_PATTERN);
		NavigableMap<Long, File> calcresFiles = FileUtils.getDumpedFiles(simdir.toString() + "/" + CALCRES_DIR, FileUtils.CALCRES_PATTERN);

		// First things first, get the trading days from the basedir and for each day compute the reporting timestamps
		NavigableMap<Long, SortedSet<Long>> reportingTimestamps = new TreeMap<Long, SortedSet<Long>>();
		for (Long ts : posFiles.keySet()) {
			long day = Time.today(ts);
			reportingTimestamps.put(day, new TreeSet<Long>());
		}

		// for each day, compute the required timestamps
		for (Map.Entry<ReportingType, Long> e : reportingTypes.entrySet()) {
			ReportingType rtype = e.getKey();
			Long interval = e.getValue();
			for (Map.Entry<Long, SortedSet<Long>> d : reportingTimestamps.entrySet()) {
				Long day = d.getKey();
				SortedSet<Long> dayTs = d.getValue();

				if (rtype == ReportingType.REGULAR) {
					long open = Exchange.openTime(day, exch);
					long close = Exchange.closeTime(day, exch);
					for (long ts = open + interval; ts <= close; ts += interval) {
						dayTs.add(ts);
					}
				}
				else if (rtype == ReportingType.EOD) {
					long close = Exchange.closeTime(day, exch);
					dayTs.add(close);
				}
				else if (rtype == ReportingType.POSITION) {
					long open = Exchange.openTime(day, exch);
					long close = Exchange.closeTime(day, exch);
					dayTs.addAll(posFiles.subMap(open, true, close, true).keySet());
				}
			}
		}

		// now for each reporting timestamp create an entry in the portfolio stats
		Portfolio portfolio = new Portfolio();
		portfolio.setMuPortfoliosAutoUpdate(getMuPortfolioStats);
		File sodPortFile = new File(simdir, "sodPort.txt");
		if (sodPortFile.exists() && useSodPort)
			portfolio.restore(sodPortFile);
		portfolio.updatePortfolioStats();

		// Now go through the portfolio as it evolves over time and generate the stats
		long currentTs = 0;
		long previousTs = 0;
		for (Long day : reportingTimestamps.keySet()) {
			for (Long ts : reportingTimestamps.get(day)) {
				currentTs = ts;

				// get a calcres of that day and apply splits and dividends
				if (Time.today(currentTs) != Time.today(previousTs)) {
					portfolio.clearFills();
					File calcresFile = calcresFiles.get(calcresFiles.subMap(day, day + Time.MILLIS_PER_DAY).firstKey());
					CalcResults calcres = CalcResults.restore(calcresFile);
					portfolio.updateSplitsAndDividends(calcres, true);
				}

				// apply all the fills between previousTs and currentTs
				double costs = 0;
				double slippage = 0;
				double estSlippage = 0;

				if (penalty == PenaltyType.NONE) {
					for (Map.Entry<Long, File> e : fillsFiles.subMap(previousTs, false, currentTs, true).entrySet()) {
						// the order file corresponding to this fills file is the one with the immediately previous ts
						File fillsFile = e.getValue();
						File orderFile = orderFiles.floorEntry(e.getKey()).getValue();
						File musFile = muFiles.floorEntry(e.getKey()).getValue();
						Pair<List<Order>, List<Fill>> ordersAndFills = PortfolioUtils.loadSimOrdersAndFills(orderFile, fillsFile, musFile);
						for (Fill fill : ordersAndFills.second) {
							portfolio.handleFill(fill);
						}

						Triplet<Double, Double, Double> p = calculateCosts(ordersAndFills.first, ordersAndFills.second);
						slippage += p.first;
						costs += p.second;
						estSlippage += p.third;
					}
				}
				else if (penalty == PenaltyType.SLIPPAGE) {
					for (Map.Entry<Long, File> e : orderFiles.subMap(previousTs, false, currentTs, true).entrySet()) {
						// the order file corresponding to this fills file is the one with the immediately previous ts
						File orderFile = e.getValue();
						File musFile = muFiles.get(e.getKey());
						Map<Integer, Map<Forecast, Double>> secid2mus = PortfolioUtils.loadMus(musFile);
						Map<Integer, Order> secid2orders = PortfolioUtils.loadOrders(orderFile, secid2mus);
						Vector<Order> orders =new Vector<Order>();
						orders.addAll(secid2orders.values());
						
						List<Fill> fills = penalizeOrdersBySlippage(orders, penaltyParam);
						for (Fill fill : fills)
							portfolio.handleFill(fill);

						Triplet<Double, Double, Double> p = calculateCosts(orders, fills);
						slippage += p.first;
						costs += p.second;
						estSlippage += p.third;
					}
				}
				else
					throw new RuntimeException("Not yet implememnted");

				// update prices
				// XXX maybe assert that they fall on a 5min interval and use PricesAsOf?
				Map<Security, Price> prices = usource.getPriceAtTs(portfolio.getSecurities(), currentTs, exch);
				portfolio.updatePrices2(prices, currentTs);
				portfolio.updatePortfolioStats(slippage, costs, estSlippage);

				previousTs = ts;
			}
		}

		Map<Forecast, PortfolioStats> muStats = new HashMap<Forecast, PortfolioStats>();
		for (Map.Entry<Forecast, Portfolio> e : portfolio.getMuPortfolios().entrySet()) {
			muStats.put(e.getKey(), e.getValue().stats);
		}
		
		return new Pair<PortfolioStats, Map<Forecast, PortfolioStats>>(portfolio.stats, muStats);
	}

	public void work(Operation operation, Map<ReportingType, Long> rtypes, Set<OutputType> output, Pair<PenaltyType, Double> penalty) throws Exception {
		String subDirName = null;
		boolean useSodPort = false;
		
		if (!simdir.exists()) {
			log.severe("Simdir " + simdir.toString() + " does not exist. Aborting...");
			return;
		}
		switch (operation) {
		case PNL: {
			Pair<PortfolioStats, Map<Forecast, PortfolioStats>> stats = gatherStats(simdir, rtypes, penalty.first, penalty.second, true, true);
			reportdir.mkdirs();
			Report report = PerformanceReport.report(stats.first, true, null);
			Writer writer = FileUtils.makeWriter(new File(reportdir, "pnl.txt"));
			writer.write(report.generateReport("  |  ", true));
			writer.close();
			
			File subdir = new File(reportdir, "pnl_reports");
			subdir.mkdir();
			writer = FileUtils.makeWriter(new File(subdir, "full.txt"));
			writer.write(report.generateReport("  |  ", true));
			writer.close();
			for (Map.Entry<Forecast, PortfolioStats> e : stats.second.entrySet()) {
				String name = (e.getKey().equals(Forecast.NONE))? "none" : e.getKey().name;
				writer = FileUtils.makeWriter(new File(subdir, name+".txt"));
				report = PerformanceReport.report(e.getValue(), true, null);
				writer.write(report.generateReport("  |  ", true));
				writer.close();
			}
			
			break;
		}
		case MARGINALS_PNL:
			if (subDirName == null) {
				subDirName = "marginals";
				useSodPort = true;
			}
		case SINGLES_PNL:
			if (subDirName == null){
				subDirName = "singles";
				useSodPort = false;
			}
			//Both MARGINALS_PNL and SIGNLES_PNL fall through here
			{
				Map<String, PortfolioStats> portfolios = new HashMap<String, PortfolioStats>();
	
				PortfolioStats full = gatherStats(simdir, rtypes, penalty.first, penalty.second, true, false).first;
				portfolios.put("FULL", full);
	
				File multiDir = new File(simdir, subDirName);
				if (!multiDir.exists()) {
					log.severe("Failed to locate portfolios directory " + multiDir.toString());
					break;
				}
	
				for (File mDir : multiDir.listFiles()) {
					if (!mDir.isDirectory())
						continue;
	
					PortfolioStats ps = gatherStats(mDir, rtypes, penalty.first, penalty.second, useSodPort, false).first;
					portfolios.put(mDir.getName(), ps);
				}
	
				reportdir.mkdirs();
				Writer writer = FileUtils.makeWriter(new File(reportdir, "pnl.txt"));
				writer.write(PerformanceReport.multiReport(portfolios, true, null));
				writer.close();
				
				File subdir = new File(reportdir, "pnl_reports");
				subdir.mkdir();
				
				for (Map.Entry<String, PortfolioStats> e : portfolios.entrySet()) {
					String name = (e.getKey().equals("FULL"))? "full" : e.getKey();
					writer = FileUtils.makeWriter(new File(subdir, name+".txt"));
					Report report = PerformanceReport.report(e.getValue(), true, null);
					writer.write(report.generateReport("  |  ", true));
					writer.close();
				}
				
				break;
			}
		case SEC_PNL: {
			Map<Security, PortfolioStats> secStats = new HashMap<Security, PortfolioStats>();
			PortfolioUtils.updateStats(secStats, new File(simdir, "sodPort.txt"), false);

			NavigableMap<Long, File> posFiles = FileUtils.getDumpedFiles(simdir.toString() + "/" + POSITION_DIR, FileUtils.POS_PATTERN);
			for (File file : posFiles.values())
				PortfolioUtils.updateStats(secStats, file, true);

			// dump per security pnls
			File secRepDir = new File(reportdir, "secstats");
			secRepDir.mkdir();
			for (Map.Entry<Security, PortfolioStats> e : secStats.entrySet()) {
				Report secRep = PerformanceReport.secReport(e.getKey(), e.getValue());
				Writer secWriter = FileUtils.makeWriter(new File(secRepDir, e.getKey().getSecId() + ".txt"));
				secWriter.write(secRep.generateReport("|", false));
				secWriter.close();
			}
			break;
		}
		default:
			break;
		}
	}

	public static void main(String[] args) throws Exception {
		CommandLineParser parser = new PosixParser();
		Options options = new Options();
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("simdir")
				.withDescription("Simulation dir central, e.g., /apps/ase/research/useq-live/weeklysim/20110318").isRequired().create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("reportdir")
				.withDescription("Target reports dir, e.g., /apps/ase/reports/useq-live/weeklysim/20110318").isRequired().create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("log").withDescription("Full path to logfile to be used").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("debug").withDescription("Set message level to INFO").create());

		options.addOption(OptionBuilder.hasArg(false).withLongOpt("pnl").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("marginals_pnl").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("singles_pnl").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("sec_pnl").create());
		options.addOption(OptionBuilder.hasArgs().withLongOpt("rtype").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("file").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("screen").create());

		options.addOption(OptionBuilder.hasArg(true).withLongOpt("slip_penalty").create());

		CommandLine cl = parser.parse(options, args);

		String simdir = cl.getOptionValue("simdir");
		String reportdir = cl.getOptionValue("reportdir");

		// REPORT INTERVALS
		Map<ReportingType, Long> rtypes = new HashMap<SimManager.ReportingType, Long>();
		if (cl.hasOption("rtype")) {
			for (String t : cl.getOptionValue("rtype").split(",")) {
				if (t.equals("eod"))
					rtypes.put(ReportingType.EOD, null);
				else if (t.equals("pos"))
					rtypes.put(ReportingType.POSITION, null);
				else if (t.matches("\\d*"))
					rtypes.put(ReportingType.REGULAR, Integer.parseInt(t) * Time.MILLIS_PER_MINUTE);
			}
		}

		// OUTPUT TYPE
		Set<OutputType> output = new HashSet<DailyManager.OutputType>();
		if (cl.hasOption("file")) {
			output.add(OutputType.FILE);
		}
		if (cl.hasOption("email")) {
			output.add(OutputType.EMAIL);
		}
		if (cl.hasOption("screen") || output.isEmpty()) {
			output.add(OutputType.SCREEN);
		}

		// // OPERATION
		Operation operation = null;
		if (cl.hasOption("pnl")) {
			operation = Operation.PNL;
		}
		else if (cl.hasOption("marginals_pnl")) {
			operation = Operation.MARGINALS_PNL;
		}
		else if (cl.hasOption("singles_pnl")) {
			operation = Operation.SINGLES_PNL;
		}
		else if (cl.hasOption("sec_pnl")) {
			operation = Operation.SEC_PNL;
		}

		PenaltyType penalty = PenaltyType.NONE;
		Double penaltyParam = null;
		if (cl.hasOption("slip_penalty")) {
			penalty = PenaltyType.SLIPPAGE;
			penaltyParam = Double.parseDouble(cl.getOptionValue("slip_penalty"));
		}

		// get debug logging options
		if (cl.hasOption("log")) {
			LoggerFactory.setLoggerFile(cl.getOptionValue("log"));
		}
		else {
			LoggerFactory.setLoggerFile(System.getenv("LOG_DIR") + "/simmanager." + operation.toString().toLowerCase() + "." + System.getenv("STRAT") + "."
					+ ManagementFactory.getRuntimeMXBean().getName().split("@")[0] + ".log");
		}

		if (cl.hasOption("debug")) {
			LoggerFactory.setUnsupervisedMode(false);
		}
		else {
			LoggerFactory.setUnsupervisedMode(true);
		}

		Properties config = new Properties();
		try {
			String configfile = simdir + "/opt.cfg";
			log.info("Loading: " + configfile);
			config.load(new FileReader(configfile));
		}
		catch (Exception e) {
			log.severe("Exception encountered while loading config file");
			log.severe(e.toString());
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
				log.severe(e.toString());
			}
			System.exit(1);
		}

		Exchange.Type exchange = Exchange.Type.valueOf(config.getProperty("exchange"));

		// NOW DO SOME REAL WORK
		SimManager sm = new SimManager(simdir, reportdir, exchange);
		sm.work(operation, rtypes, output, new Pair<PenaltyType, Double>(penalty, penaltyParam));
	}
}
