package ase.apps;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.Writer;
import java.lang.management.ManagementFactory;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.TreeMap;
import java.util.Vector;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.OptionBuilder;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;
import org.apache.commons.cli.PosixParser;

import ase.calculator.CalcMaster;
import ase.calculator.CalcMaster.Mode;
import ase.calculator.DailyPriceCalculator;
import ase.calculator.Forecast;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.Universe;
import ase.portfolio.CapAdjustmentGenerator;
import ase.portfolio.OldSystemUtils;
import ase.portfolio.OverrideGenerator;
import ase.portfolio.Portfolio;
import ase.portfolio.PortfolioStats;
import ase.portfolio.PortfolioUtils;
import ase.portfolio.PortfolioStats.DailyStats;
import ase.reports.FactorReport;
import ase.reports.ForecastCorrelationReport;
import ase.reports.GraphStats;
import ase.reports.MuReport;
import ase.reports.PerformanceReport;
import ase.reports.PnlReport;
import ase.reports.Report;
import ase.reports.RiskAttribution;
import ase.reports.Report.ReportAttrType;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.reports.SlippageReport;
import ase.timeseries.Bar;
import ase.timeseries.Bar.BarExtraType;
import ase.timeseries.BarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;

public class DailyManager {
	protected static final Logger log = LoggerFactory.getLogger(DailyManager.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	protected enum Operation {
		SOD, OLD2NEW, PNL, CAP_ADJ, LIVE_PNL, OVERRIDES, FACTOR, SIMCALC, MU_SOD, MU_REPORT, PERF, SLIP, MARGINALS_PNL, MU_CORR, MU_PERF, SEC_PNL, PSTATS, MU_PSTATS, SINGLES_PNL, ENH_PROD_CALC, INTRA_STATS, FACTOR_FORECASTS, VOLUME_HIST, RISK_ATTR
	};

	public enum OutputType {
		SCREEN, FILE, EMAIL
	};

	protected static Pattern datedir = Pattern.compile("[0-9]{8}");
	private final String location;
	private final Exchange.Type primaryExch;
	private UnifiedDataSource uSource = null;

	// Create a data souce lazily, on demand
	private UnifiedDataSource getUSource() {
		if (this.uSource == null) {
			this.uSource = new UnifiedDataSource(false);
		}
		return this.uSource;
	}

	public DailyManager(String location, Exchange.Type primaryExch) {
		this.location = location;
		this.primaryExch = primaryExch;
	}

	public void operateRangeless(long date1, long date2, Operation operation, boolean oldSystem, Set<OutputType> output, String outputDir) throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);

		switch (operation) {
		case PERF: {
			// /XXX see if you want to add a zero initial stat first
			PortfolioStats stats = new PortfolioStats();
			File statsDir = new File(System.getenv("REPORT_DIR") + "/dailyperf");
			File[] files = statsDir.listFiles();
			Arrays.sort(files);
			for (File statsFile : files) {
				if (!statsFile.getName().startsWith("full"))
					continue;

				String[] tokens = statsFile.getName().split("\\.");
				long statsDate = df.fromYYYYMMDD(tokens[1]);
				if (statsDate < date1 || statsDate >= date2)
					continue;

				BufferedReader reader = FileUtils.openFileReader(statsFile);
				String line = reader.readLine();
				stats.updateStats(line);
				reader.close();
			}

			Report report = PerformanceReport.report(stats, false, null);
			Sorter sorter = new Sorter();
			sorter.add(0, ReportAttrType.S, ReportSortType.DESC);
			report.sort(sorter);

			Pair<Report, Report> graphStats = GraphStats.perf(stats);

			if (output.contains(OutputType.SCREEN)) {
				System.out.println(report.generateReport("  |  ", true));
				System.out.flush();
			}
			if (output.contains(OutputType.FILE)) {
				Writer writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/perf.txt"));
				writer.write(report.generateReport("  |  ", true));
				writer.close();

				writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/perf_pnl_stats.txt"));
				writer.write(graphStats.first.generateReport("|", false));
				writer.close();

				writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/perf_size_stats.txt"));
				writer.write(graphStats.second.generateReport("|", false));
				writer.close();
			}
			break;
		}
		case MU_PERF: {
			// /XXX see if you want to add a zero initial stat first
			Map<String, PortfolioStats> mustats = new HashMap<String, PortfolioStats>();
			File statsDir = new File(System.getenv("REPORT_DIR") + "/dailyperf");
			File[] files = statsDir.listFiles();
			Arrays.sort(files);
			for (File statsFile : files) {
				if (statsFile.getName().startsWith("full"))
					continue;

				String[] tokens = statsFile.getName().split("\\.");
				long statsDate = df.fromYYYYMMDD(tokens[1]);
				if (statsDate < date1 || statsDate >= date2)
					continue;

				String fc = tokens[0];
				PortfolioStats stats = mustats.get(fc);
				if (stats == null) {
					stats = new PortfolioStats();
					stats.addZero();
					mustats.put(fc, stats);
				}

				BufferedReader reader = FileUtils.openFileReader(statsFile);
				String line = reader.readLine();
				stats.updateStats(line);
				reader.close();
			}

			// sort portfolios by sharpe
			int xx = 0;
			Map<Double, String> sortedFcasts = new TreeMap<Double, String>();
			for (Map.Entry<String, PortfolioStats> e : mustats.entrySet()) {
				Double s = e.getValue().computeSharpe().third;
				if (s == null)
					s = -Double.MAX_VALUE + (xx++);
				sortedFcasts.put(-s, e.getKey());
			}

			StringBuilder stringReport = new StringBuilder();
			for (String fcast : sortedFcasts.values()) {
				Report report = PerformanceReport.report(mustats.get(fcast), false, null);
				Sorter sorter = new Sorter();
				sorter.add(0, ReportAttrType.S, ReportSortType.DESC);
				report.sort(sorter);
				stringReport.append(fcast + "\n");
				stringReport.append(report.generateReport("  |  ", true));
				stringReport.append("\n\n");
			}

			if (output.contains(OutputType.SCREEN)) {
				System.out.println(stringReport.toString());
				System.out.flush();
			}
			if (output.contains(OutputType.FILE)) {
				Writer writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/muperf.txt"));
				writer.write(stringReport.toString());
				writer.close();
			}
			break;
		}
		default:
			break;
		}
	}

	/*
	 * public void operateOnRange(long date1, long date2, Operation operation, boolean oldSystem, Set<OutputType> output) throws Exception {
	 * Time.assertDay(date1); Time.assertDay(date2); File dir = new File(location); Vector<File> dateDirs = new Vector<File>(); File preDir = null; // first
	 * valid dir before range for (File dateDir : dir.listFiles()) { if (!dateDir.isDirectory() || !datedir.matcher(dateDir.getName()).matches()) continue; if
	 * (!Exchange.isTradingDay(df.fromYYYYMMDD(dateDir.getName()), primaryExch)) continue; if (dateDir.getName().compareTo(df.toYYYYMMDD(date1)) >= 0 &&
	 * dateDir.getName().compareTo(df.toYYYYMMDD(date2)) < 0) { dateDirs.add(dateDir); } if (dateDir.getName().compareTo(df.toYYYYMMDD(date1)) < 0 && (preDir ==
	 * null || dateDir.compareTo(preDir) > 0)) { preDir = dateDir; } }
	 * 
	 * Collections.sort(dateDirs); switch (operation) { case PERF: { PortfolioStats stats = new PortfolioStats(); for (File dateDir : dateDirs) {
	 * PortfolioUtils.updateStats(stats, new File(dateDir, "sodPort.txt")); }
	 * 
	 * Report report = PerformanceReport.report(stats, false, null); Sorter sorter = new Sorter(); sorter.add(0, ReportAttrType.S, ReportSortType.DESC);
	 * report.sort(sorter);
	 * 
	 * Writer writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/perf.txt")); writer.write(report.generateReport("  |  ", true));
	 * writer.close(); break; } case MU_PERF: { Map<String, PortfolioStats> mustats = new HashMap<String, PortfolioStats>(); for (File dateDir : dateDirs) {
	 * File muSodDir = new File(dateDir, "muSod"); if (!muSodDir.exists()) continue;
	 * 
	 * Portfolio p = PortfolioUtils.processDayPortfolio(location, primaryExch, df.fromYYYYMMDD(dateDir.getName()), false, false, true, 0).second; for
	 * (Map.Entry<Forecast, Portfolio> e : p.getMuPortfolios().entrySet()) { String fcast = e.getKey().name; Portfolio mp = e.getValue(); PortfolioStats stats =
	 * mustats.get(fcast); if (stats == null) mustats.put(fcast, stats = new PortfolioStats()); stats.updateStats(mp, 0, 0, 0); } }
	 * 
	 * // sort portfolios by sharpe int xx = 0; Map<Double, String> sortedFcasts = new TreeMap<Double, String>(); for (Map.Entry<String, PortfolioStats> e :
	 * mustats.entrySet()) { Double s = e.getValue().computeSharpe().third; if (s == null) s = -Double.MAX_VALUE + (xx++); sortedFcasts.put(-s, e.getKey()); }
	 * 
	 * Writer writer = FileUtils.makeWriter(new File(System.getenv("REPORT_DIR"), "/various/muperf.txt")); for (String fcast : sortedFcasts.values()) { Report
	 * report = PerformanceReport.report(mustats.get(fcast), false, null); Sorter sorter = new Sorter(); sorter.add(0, ReportAttrType.S, ReportSortType.DESC);
	 * report.sort(sorter); writer.write(fcast + "\n"); writer.write(report.generateReport("  |  ", true)); writer.write("\n\n"); } writer.close(); break; }
	 * default: break;
	 * 
	 * } }
	 */

	public void operateOnEachDayInRange(long date1, long date2, Operation operation, boolean oldSystem, Set<OutputType> output, String outputDir)
			throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);
		File dir = new File(location);
		Vector<File> dateDirs = new Vector<File>();
		File preDir = null; // first valid dir before range
		for (File dateDir : dir.listFiles()) {
			if (!dateDir.isDirectory() || !datedir.matcher(dateDir.getName()).matches())
				continue;
			if (!Exchange.isTradingDay(df.fromYYYYMMDD(dateDir.getName()), primaryExch))
				continue;
			if (dateDir.getName().compareTo(df.toYYYYMMDD(date1)) >= 0 && dateDir.getName().compareTo(df.toYYYYMMDD(date2)) < 0) {
				dateDirs.add(dateDir);
			}
			if (dateDir.getName().compareTo(df.toYYYYMMDD(date1)) < 0 && (preDir == null || dateDir.compareTo(preDir) > 0)) {
				preDir = dateDir;
			}
		}

		long t0 = preDir == null ? -1 : df.fromYYYYMMDD(preDir.getName());

		Collections.sort(dateDirs);
		for (int ii = 0; ii < dateDirs.size(); ii++) {
			long previousDate = (ii == 0) ? t0 : df.fromYYYYMMDD(dateDirs.get(ii - 1).getName());
			long currentDate = df.fromYYYYMMDD(dateDirs.get(ii).getName());

			switch (operation) {
			case SOD:
				createSodPortfolio(currentDate, previousDate, oldSystem, false);
				break;
			case MU_SOD:
				createSodPortfolio(currentDate, previousDate, oldSystem, true);
				break;
			case OLD2NEW:
				OldSystemUtils.convertOldSystemFiles(location, currentDate);
				break;
			case PNL:
				PnlReport.singlePnl(location, primaryExch, currentDate, oldSystem, output, false);
				break;
			case CAP_ADJ:
				CapAdjustmentGenerator.generateAdjustmentFile(location, currentDate, output);
				break;
			case LIVE_PNL:
				PnlReport.continuousPnl(location, primaryExch, currentDate, primaryExch, oldSystem, output);
				break;
			case OVERRIDES:
				OverrideGenerator.ammendOverrideFile(location, currentDate, oldSystem);
				break;
			case FACTOR:
				FactorReport.dailyReport(location, currentDate, primaryExch, oldSystem, output, false);
				break;
			case FACTOR_FORECASTS:
				FactorReport.dailyReport(location, currentDate, primaryExch, oldSystem, output, true);
			case MU_REPORT:
				MuReport.muReport(location, primaryExch, currentDate, oldSystem, output, false);
				break;
			case SIMCALC: {
				// get configuration
				Properties config = new Properties();
				config.load(new FileReader(System.getenv("CONFIG_DIR") + "/calc.prod.cfg"));
				Universe uni = new Universe(config, location, currentDate);
				CalcMaster daMaster = new CalcMaster(config, uni, Mode.SIM);

				long calcdate = Exchange.closeTime(currentDate, primaryExch);
				CalcResults calcres = new CalcResults(0);
				calcres = daMaster.calculate(calcdate, calcres);

				Pair<String, Writer> resfile = FileUtils.openDataDumpFile(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres", "calcres", calcdate);
				Writer writer = resfile.second;
				calcres.dump(writer);
				writer.close();
				FileUtils.finalizeFile(resfile.first);
				break;
			}
			case ENH_PROD_CALC: {
				// Get calcres closest to 3.30pm, after 3.30pm
				NavigableMap<Long, File> calcresFiles = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres",
						FileUtils.CALCRES_PATTERN);
				Map.Entry<Long, File> e = calcresFiles.ceilingEntry(Exchange.closeTime(currentDate, primaryExch) - 30 * Time.MILLIS_PER_MINUTE);
				if (e == null)
					e = calcresFiles.floorEntry(Exchange.closeTime(currentDate, primaryExch) - 30 * Time.MILLIS_PER_MINUTE);
				if (e == null) {
					log.severe("Failed to locate a calcres file for " + df.toYYYYMMDD(currentDate));
					break;
				}

				CalcResults calcres = CalcResults.restore(e.getValue());
				UnifiedDataSource uSource = getUSource();

				calcres.clearResult(DailyPriceCalculator.DIV);
				calcres.clearResult(DailyPriceCalculator.CASHEQ);
				calcres.clearResult(DailyPriceCalculator.SPLIT);
				Map<Security, Triplet<Double, Double, Double>> capAdjMap = uSource.dailySource.pw.getAdjustments(calcres.getSecurities(), currentDate);
				for (Map.Entry<Security, Triplet<Double, Double, Double>> a : capAdjMap.entrySet()) {
					calcres.add(a.getKey(), DailyPriceCalculator.DIV, currentDate, a.getValue().first);
					calcres.add(a.getKey(), DailyPriceCalculator.CASHEQ, currentDate, a.getValue().second);
					calcres.add(a.getKey(), DailyPriceCalculator.SPLIT, currentDate, a.getValue().third);
				}

				Pair<String, Writer> resfile = FileUtils.openDataDumpFile(outputDir + "/calcres", "calcres", calcres.getAsOf());
				Writer writer = resfile.second;
				calcres.dump(writer);
				writer.close();
				FileUtils.finalizeFile(resfile.first);
				break;
			}
			case SLIP:
				SlippageReport.dailyReport(location, primaryExch, currentDate, output);
				break;
			case MU_CORR:
				ForecastCorrelationReport.fcCorrReport(location, primaryExch, currentDate, output);
				break;
			case PSTATS:
				createPerformanceStatistics(currentDate, oldSystem, false);
				break;
			case MU_PSTATS:
				createPerformanceStatistics(currentDate, oldSystem, true);
				break;
			case INTRA_STATS:
				GraphStats.intradayLive(location, primaryExch, currentDate, 5);
				break;
			case VOLUME_HIST: {
				// Get the tickers file
				File tickersFile = new File(location + "/" + df.toYYYYMMDD(currentDate) + "/tickers.txt");
				if (!tickersFile.exists()) {
					log.severe("Failed to locate file " + tickersFile.toString() + ". Aborting...");
					break;
				}

				Set<Security> secs = Universe.loadFromTickersFile(tickersFile.toString());
				UnifiedDataSource uSource = getUSource();
				Map<Security, BarTimeSeries> tss = uSource.barSource.getHalfDayTimeSeries(secs, previousDate, previousDate,
						Exchange.tradingDayMillis(primaryExch), primaryExch);

				File volHistFile = new File(location + "/" + df.toYYYYMMDD(currentDate) + "/volhist.txt");
				Writer writer = FileUtils.makeWriter(volHistFile);
				for (Map.Entry<Security, BarTimeSeries> e : tss.entrySet()) {
					assert e.getValue().size() == 1;
					int secid = e.getKey().getSecId();
					Bar bar = e.getValue().getLag(0);
					int trades = (bar != null && bar.getExtra(BarExtraType.TRADES) != null) ? (int) Math.round((bar.getExtra(BarExtraType.TRADES))) : 0;
					writer.write(secid + "|" + trades + "\n");
				}
				writer.close();

				break;
			}
			case RISK_ATTR:
				RiskAttribution.dailyReport(location, currentDate, primaryExch, oldSystem, output);
				break;
			default:
				break;
			}
		}
	}

	public void createSodPortfolio(long currentDate, long previousDate, boolean oldSystem, boolean withMus) throws Exception {
		File dir = new File(location);
		File currentDateDir = new File(dir, df.toYYYYMMDD(currentDate));
		File previousDateDir = previousDate < 0 ? null : new File(dir, df.toYYYYMMDD(previousDate));

		Portfolio sodPortfolio = null;
		if (previousDateDir != null) {
			previousDate = df.fromYYYYMMDD(previousDateDir.getName());
			Pair<Portfolio, Portfolio> ports = PortfolioUtils.processDayPortfolio(location, primaryExch, previousDate, oldSystem, false, withMus, 0);
			sodPortfolio = ports.second;
		}
		else {
			log.severe("Failed to identify previous trading day while creating portfolio for day " + df.toYYYYMMDD(currentDate) + ". Assuming empty portfolio.");
			sodPortfolio = new Portfolio();
		}
		currentDateDir.mkdirs();
		// /XXX do not dump the sod portfolio, keeps things separate
		if (!withMus) {
			sodPortfolio.savePositions(new File(currentDateDir, Portfolio.SOD_PORTFOLIO));
		}
		else {
			File muDir = new File(currentDateDir, "muSod");
			muDir.mkdirs();
			sodPortfolio.saveMuPositions(muDir);
		}
	}

	public void createPerformanceStatistics(long currentDate, boolean oldSystem, boolean withMus) throws Exception {
		Pair<Portfolio, Portfolio> ports = PortfolioUtils.processDayPortfolio(location, primaryExch, currentDate, oldSystem, false, withMus, 0);

		// get stats to dump
		Map<String, DailyStats> stats = new HashMap<String, PortfolioStats.DailyStats>();
		if (!withMus) {
			stats.put("full", ports.second.stats.getLatestStats());
		}
		else {
			for (Map.Entry<Forecast, Portfolio> e : ports.second.getMuPortfolios().entrySet()) {
				stats.put(e.getKey().name + ":" + e.getKey().type, e.getValue().stats.getLatestStats());
			}
		}

		// dump
		for (Map.Entry<String, DailyStats> e : stats.entrySet()) {
			File statFile = new File(System.getenv("REPORT_DIR") + "/dailyperf/" + e.getKey() + "." + df.toYYYYMMDD(currentDate) + ".txt");
			Writer writer = FileUtils.makeWriter(statFile);
			writer.write(e.getValue().toString() + "\n");
			writer.close();
		}
	}

	public static void main(String[] args) throws Exception {
		try {
			CommandLineParser parser = new PosixParser();
			Options options = new Options();
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("all").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("today").withDescription("YYYYMMDD").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("yesterday").withDescription("YYYYMMDD").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("day").withDescription("YYYYMMDD").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("t1").withDescription("From [YYYYMMDD").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("t2").withDescription("To YYYYMMDD)").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("location").withDescription("Strategy central, e.g., /apps/ase/run/useq-live").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("exchange").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("log").withDescription("Full path to logfile to be used").create());
			options.addOption(OptionBuilder.hasArg(true).withLongOpt("outputdir").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("debug").withDescription("Set message level to INFO").create());

			options.addOption(OptionBuilder.hasArg(false).withLongOpt("old").withDescription("Use old system fills and fake_fills files").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("sod").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("musod").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("old2new").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("pnl").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("livepnl").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("capadj").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("overrides").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("factor").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("factor_forecasts").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("mureport").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("simcalc").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("perf").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("muperf").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("slip").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("mucorr").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("pstats").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("mupstats").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("enh_calc").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("intra_stats").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("volhist").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("risk_attr").create());

			options.addOption(OptionBuilder.hasArg(false).withLongOpt("file").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("email").create());
			options.addOption(OptionBuilder.hasArg(false).withLongOpt("screen").create());

			CommandLine cl = parser.parse(options, args);

			String location = cl.getOptionValue("location");
			Exchange.Type primaryExch = Exchange.Type.valueOf(cl.getOptionValue("exchange"));

			// /// GET DATE RANGE ////
			long t1 = -1;
			long t2 = -1;

			if (cl.hasOption("t1") && cl.hasOption("t2")) {
				t1 = df.fromYYYYMMDD(cl.getOptionValue("t1"));
				t2 = df.fromYYYYMMDD(cl.getOptionValue("t2"));
			}
			else if (cl.hasOption("day")) {
				t1 = df.fromYYYYMMDD(cl.getOptionValue("day"));
				t2 = t1 + Time.MILLIS_PER_DAY;
			}
			else if (cl.hasOption("today")) {
				t1 = Time.today(Time.now());
				t2 = t1 + Time.MILLIS_PER_DAY;
			}
			else if (cl.hasOption("yesterday")) {
				t1 = Exchange.prevTradingDay(Time.now(), primaryExch);
				t2 = t1 + Time.MILLIS_PER_DAY;
			}
			else if (cl.hasOption("all")) {
				t1 = Time.fromYYYYMMDD(19000000);
				t2 = Time.fromYYYYMMDD(21000000);
			}
			else {
				HelpFormatter formatter = new HelpFormatter();
				formatter.printHelp("$JAVA ase.portfolio.PortfolioManager", options);
				throw new ParseException("Invalid options");
			}

			// // OLD SYSTEM FILES
			boolean oldSystem = false;
			if (cl.hasOption("old")) {
				oldSystem = true;
			}

			// OPTIONAL OUTPUT DIR
			String outputDir = cl.getOptionValue("outputdir", null);

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
			if (cl.hasOption("sod")) {
				operation = Operation.SOD;
			}
			else if (cl.hasOption("musod")) {
				operation = Operation.MU_SOD;
			}
			else if (cl.hasOption("old2new")) {
				operation = Operation.OLD2NEW;
			}
			else if (cl.hasOption("pnl")) {
				operation = Operation.PNL;
			}
			else if (cl.hasOption("livepnl")) {
				operation = Operation.LIVE_PNL;
				if (Time.midnight(t1) != Time.midnight(Time.now())) {
					log.severe("Requested livepnl and provided a day other than day(NOW). Your date choices are being overriden.");
				}
				t1 = Time.today(Time.now());
				t2 = t1 + Time.MILLIS_PER_DAY;
			}
			else if (cl.hasOption("capadj")) {
				operation = Operation.CAP_ADJ;
			}
			else if (cl.hasOption("overrides")) {
				operation = Operation.OVERRIDES;
				if (Time.midnight(t1) != Time.midnight(Time.now())) {
					log.severe("Requested overrides and provided a day other than day(NOW). Your date choices are being overriden.");
				}
				t1 = Time.today(Time.now());
				t2 = t1 + Time.MILLIS_PER_DAY;
			}
			else if (cl.hasOption("factor")) {
				operation = Operation.FACTOR;
			}
			else if (cl.hasOption("factor_forecasts")) {
				operation = Operation.FACTOR_FORECASTS;
			}
			else if (cl.hasOption("mureport")) {
				operation = Operation.MU_REPORT;
			}
			else if (cl.hasOption("simcalc")) {
				operation = Operation.SIMCALC;
			}
			else if (cl.hasOption("slip")) {
				operation = Operation.SLIP;
			}
			else if (cl.hasOption("mucorr")) {
				operation = Operation.MU_CORR;
			}
			else if (cl.hasOption("perf")) {
				operation = Operation.PERF;
			}
			else if (cl.hasOption("muperf")) {
				operation = Operation.MU_PERF;
			}
			else if (cl.hasOption("pstats")) {
				operation = Operation.PSTATS;
			}
			else if (cl.hasOption("mupstats")) {
				operation = Operation.MU_PSTATS;
			}
			else if (cl.hasOption("enh_calc")) {
				assert outputDir != null;
				operation = Operation.ENH_PROD_CALC;
			}
			else if (cl.hasOption("intra_stats")) {
				operation = Operation.INTRA_STATS;
			}
			else if (cl.hasOption("volhist")) {
				operation = Operation.VOLUME_HIST;
			}
			else if (cl.hasOption("risk_attr")) {
				operation = Operation.RISK_ATTR;
			}
			else {
				HelpFormatter formatter = new HelpFormatter();
				formatter.printHelp("$JAVA ase.portfolio.PortfolioManager", options);
				throw new ParseException("Specify operation type");
			}

			// get debug logging options
			if (cl.hasOption("log")) {
				LoggerFactory.setLoggerFile(cl.getOptionValue("log"));
			}
			else {
				LoggerFactory.setLoggerFile(System.getenv("LOG_DIR") + "/dailymanager." + operation.toString().toLowerCase() + "." + System.getenv("STRAT")
						+ "." + ManagementFactory.getRuntimeMXBean().getName().split("@")[0] + ".log");
			}

			if (cl.hasOption("debug")) {
				LoggerFactory.setUnsupervisedMode(false);
			}
			else {
				LoggerFactory.setGlobalLevel(Level.WARNING);
				LoggerFactory.setUnsupervisedMode(true);
			}

			// tell live quote widget who we are

			// NOW DO SOME REAL WORK
			DailyManager dm = new DailyManager(location, primaryExch);
			switch (operation) {
			case PERF:
			case MU_PERF:
				dm.operateRangeless(t1, t2, operation, oldSystem, output, outputDir);
				break;
			default:
				dm.operateOnEachDayInRange(t1, t2, operation, oldSystem, output, outputDir);
				break;
			}
		}
		catch (Throwable e) {
			log.severe("Exception encountered!");
			log.severe(e.toString());
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
			}
			System.exit(1);
		}
	}
}
