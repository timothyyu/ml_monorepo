package ase.apps;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.OptionBuilder;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.PosixParser;

import ase.calculator.DailyPriceCalculator;
import ase.calculator.FactorCalculator;
import ase.calculator.FactorCalculator.ReturnType;
import ase.calculator.Forecast;
import ase.calculator.PassThruCalculator;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.NumericAttribute;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.DailyBarTimeSeries;
import ase.timeseries.TimeSeriesUtil;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class Fit {
	private static final Logger log = LoggerFactory.getLogger(Fit.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private static final int FACTOR_DAYS_LOOKBACK = 20;
	private static final int FACTOR_DAYS = 130;

	private final String fitdir;
	private final Vector<Integer> horizons;
	private final Exchange.Type primaryExch;
	private final Properties cfg;
	private final boolean intraday;
	private final UnifiedDataSource uSource;
	private FactorCalculator factCalc;
	private Map<Security, NavigableMap<Long, Attribute>> capMap;
	private long lastDay;
	private final boolean slim;

	public Fit(String fitdir, Vector<Integer> horizons, Exchange.Type exch, Properties cfg, boolean intraday, boolean slim) {
		this.fitdir = fitdir;
		this.horizons = horizons;
		this.primaryExch = exch;
		this.cfg = cfg;
		this.intraday = intraday;
		this.uSource = new UnifiedDataSource(false);
		this.factCalc = null;
		this.capMap = null;
		this.lastDay = 0L;
		this.slim = slim;
	}

	public void generateFitResFiles() throws Exception {
		Map<Long, File> files = intraday && slim ? FileUtils.getDumpedFiles(fitdir + "/calcres_intraday", FileUtils.INTRADAY_CALCRES_PATTERN) : FileUtils
				.getDumpedFiles(fitdir + "/calcres", FileUtils.CALCRES_PATTERN);
		for (Map.Entry<Long, File> file : files.entrySet()) {
			log.info("Restoring " + file.getValue());
			long calcdate = file.getKey();

			CalcResults calcres = CalcResults.restore(file.getValue(), calcdate);

			// only grab "alive" securities
			Set<Security> secs = calcres.getResult(DailyPriceCalculator.ADVP).keySet();
			Map<Security, Vector<Attribute>> toRecord = null;
			if (intraday) {
				toRecord = generateIntradayDependents(secs, calcres.getAsOf(), calcres);
			}
			else {
				toRecord = generateDailyDependents(secs, calcres.getAsOf(), calcres);
			}

			// if (cfg != null && !intraday) {
			// Map<Security, Vector<Attribute>> independents = generateIndependents(secs, calcres.getAsOf(), calcres, cfg);
			// for (Security sec : independents.keySet()) {
			// Vector<Attribute> vec = toRecord.get(sec);
			// if (sec == null) {
			// vec = new Vector<Attribute>();
			// }
			// vec.addAll(independents.get(sec));
			// }
			// }
			record(toRecord, calcdate, intraday);
		}
	}

	private Map<Security, Vector<Attribute>> generateDailyDependents(Set<Security> secs, long asof, CalcResults cr) throws Exception {
		Map<Security, Vector<Attribute>> res = new HashMap<Security, Vector<Attribute>>(secs.size());
		for (Security sec : secs) {
			res.put(sec, new Vector<Attribute>());
		}
		UnifiedDataSource uSource = new UnifiedDataSource(false);
		FactorCalculator factCalc = new FactorCalculator(uSource, FACTOR_DAYS_LOOKBACK, FACTOR_DAYS, primaryExch);
		// Get the capitalization map once for efficiency
		Map<Security, NavigableMap<Long, Attribute>> capMap = uSource.attrSource.getRange(secs, PassThruCalculator.CAP, Time.today(asof), asof);

		long start = Time.today(asof);
		for (Integer horizon : horizons) {
			long endmillis = Exchange.closeTime(Exchange.addTradingDays(start, horizon, primaryExch), primaryExch);
			log.info("Generating returns at horizon: " + horizon + " from " + df.format(asof) + " to " + df.format(endmillis));
			// give ourselves a day's slack to get compustat prices
			if (endmillis > Time.now() - Time.MILLIS_PER_DAY) {
				log.info("We can't see into the future bonehead! asof=" + df.debugFormat(asof) + " horizon=" + horizon);
				continue;
			}

			Map<Security, DailyBarTimeSeries> prices = uSource.getDailyBarTimeSeries(secs, start, endmillis, primaryExch);
			log.info("Generating Raw Returns...");
			AttrType rawRetType = new CalcAttrType("RawRet" + horizon);
			for (Map.Entry<Security, DailyBarTimeSeries> ent : prices.entrySet()) {
				Security sec = ent.getKey();
				double logrel = ent.getValue().getLogrel();
				if (!Double.isNaN(logrel)) {
					res.get(sec).add(new NumericAttribute(rawRetType, sec, asof, logrel, asof));
				}
			}

			// Generate close2open only for horizon 1
			if (horizon == 1) {
				log.info("Generating Close2Open Raw Returns...");
				AttrType c2oRawRetType = new CalcAttrType("C2ORawRet" + horizon);
				for (Map.Entry<Security, DailyBarTimeSeries> ent : prices.entrySet()) {
					Security sec = ent.getKey();
					BarTimeSeries bts = ent.getValue();
					Bar bar1 = bts.floor(Exchange.closeTime(asof, primaryExch));
					Bar bar2 = bts.floor(Exchange.nextClose(asof, primaryExch));
					double logrel = TimeSeriesUtil.c2oLogrel(bar2, bar1);

					if (!Double.isNaN(logrel)) {
						res.get(sec).add(new NumericAttribute(c2oRawRetType, sec, asof, logrel, asof));
					}
				}

				log.info("Generating Close2Open Residual Returns...");
				AttrType c2oRsdRetType = new CalcAttrType("C2ORsdRet" + horizon);
				Map<Security, Attribute> c2orsdrets = factCalc.calculateFitResults(secs, asof, endmillis, c2oRsdRetType, false, ReturnType.CLOSE2OPEN, capMap);
				for (Map.Entry<Security, Attribute> ent : c2orsdrets.entrySet()) {
					res.get(ent.getKey()).add(ent.getValue());
				}
			}

			log.info("Generating Residual Returns...");
			AttrType rsdRetType = new CalcAttrType("RsdRet" + horizon);
			Map<Security, Attribute> rsdrets = factCalc.calculateFitResults(secs, asof, endmillis, rsdRetType, false, ReturnType.DAILY, capMap);
			for (Map.Entry<Security, Attribute> ent : rsdrets.entrySet()) {
				res.get(ent.getKey()).add(ent.getValue());
			}

			log.info("Generating Barra residual Returns...");
			AttrType barraRsdRetType = new CalcAttrType("BarraRsdRet" + horizon);
			Map<Security, Attribute> barrarsdrets = factCalc.calculateFitResults(secs, asof, endmillis, barraRsdRetType, true, ReturnType.DAILY, capMap);
			for (Map.Entry<Security, Attribute> ent : barrarsdrets.entrySet()) {
				res.get(ent.getKey()).add(ent.getValue());
			}
		}
		return res;
	}

	private Map<Security, Vector<Attribute>> generateIntradayDependents(Set<Security> secs, long asof, CalcResults cr) throws Exception {
		Map<Security, Vector<Attribute>> res = new HashMap<Security, Vector<Attribute>>(secs.size());
		for (Security sec : secs) {
			res.put(sec, new Vector<Attribute>());
		}

		if (Time.today(asof) != this.lastDay) {
			this.factCalc = new FactorCalculator(this.uSource, FACTOR_DAYS_LOOKBACK, FACTOR_DAYS, primaryExch);
			this.capMap = this.uSource.attrSource.getRange(secs, PassThruCalculator.CAP, Time.today(asof), Exchange.openTime(asof, primaryExch));
			this.lastDay = Time.today(asof);
		}

		for (Integer horizon : horizons) {
			long endmillis = asof + Time.fromMinutes(horizon);
			if (endmillis > Exchange.closeTime(asof, primaryExch)) {
				log.info("Asof+horizon point past exchange close: asof=" + df.debugFormat(asof) + " horizon=" + horizon);
				continue;
			}
			intraDependentsInternal(secs, res, asof, endmillis, "Intra", Integer.toString(horizon), false);
			if (horizon >= 60)
				intraDependentsInternal(secs, res, asof, endmillis, "Intra", Integer.toString(horizon), true);
		}

		// 10 am to 1pm
		if (asof == Exchange.openTime(asof, primaryExch) + 30 * Time.MILLIS_PER_MINUTE) {
			long endMillis = asof + 3 * Time.MILLIS_PER_HOUR;
			intraDependentsInternal(secs, res, asof, endMillis, "TenToOne", "", true);
		}
		// 1pm to 4pm
		if (asof == Exchange.openTime(asof, primaryExch) + 210 * Time.MILLIS_PER_MINUTE && !Exchange.isEarlyClose(asof, primaryExch)) {
			long endMillis = asof + 3 * Time.MILLIS_PER_HOUR;
			intraDependentsInternal(secs, res, asof, endMillis, "OneToFour", "", true);
		}
		// Round hour of trading, e.g., 10am-11am being Hourly1, 11am-12pm being Hourly2, etc.
		if (asof % Time.MILLIS_PER_HOUR == 0 && (asof + Time.MILLIS_PER_HOUR) <= Exchange.closeTime(asof, primaryExch)) {
			int hour = Time.millis2hour(asof, primaryExch);
			intraDependentsInternal(secs, res, asof, asof + Time.MILLIS_PER_HOUR, "Hourly" + hour, "", true);
		}

		return res;
	}

	private void intraDependentsInternal(Set<Security> secs, Map<Security, Vector<Attribute>> res, long t1, long t2, String namePrefix, String nameSuffix,
			boolean residuals) throws Exception {
		Map<Security, BarTimeSeries> prices = uSource.barSource.getTimeSeries(secs, t1, t2, primaryExch);

		log.info("Generating " + namePrefix + "RawRet" + nameSuffix);
		AttrType rawRetType = new CalcAttrType(namePrefix + "RawRet" + nameSuffix);
		for (Map.Entry<Security, BarTimeSeries> ent : prices.entrySet()) {
			Security sec = ent.getKey();
			double logrel = ent.getValue().getLogrel();
			if (!Double.isNaN(logrel))
				res.get(sec).add(new NumericAttribute(rawRetType, sec, t1, logrel, t1));
		}

		if (residuals) {
			log.info("Generating " + namePrefix + "RsdRet" + nameSuffix);
			AttrType rsdRetType = new CalcAttrType(namePrefix + "RsdRet" + nameSuffix);
			Map<Security, Attribute> rsdrets = factCalc.calculateFitResults(secs, t1, t2, rsdRetType, false, ReturnType.INTRADAY, capMap);
			for (Map.Entry<Security, Attribute> ent : rsdrets.entrySet()) {
				res.get(ent.getKey()).add(ent.getValue());
			}

			log.info("Generating " + namePrefix + "BarraRsdRet" + nameSuffix);
			AttrType barraRsdRetType = new CalcAttrType(namePrefix + "BarraRsdRet" + nameSuffix);
			Map<Security, Attribute> barrarsdrets = factCalc.calculateFitResults(secs, t1, t2, barraRsdRetType, true, ReturnType.INTRADAY, capMap);
			for (Map.Entry<Security, Attribute> ent : barrarsdrets.entrySet())
				res.get(ent.getKey()).add(ent.getValue());
		}
	}

	@Deprecated
	// /XXX revisit if you want to use again
	private Map<Security, Vector<Attribute>> generateIndependents(Set<Security> secs, long asof, CalcResults cr, Properties config) throws Exception {
		Map<Security, Vector<Attribute>> res = new HashMap<Security, Vector<Attribute>>(secs.size());
		for (Security sec : secs) {
			res.put(sec, new Vector<Attribute>());
		}

		Collection<Forecast> forecasts = Forecast.loadDefs(config);
		long start = Time.today(asof);
		for (Integer horizon : horizons) {
			long endmillis = Exchange.closeTime(Exchange.addTradingDays(start, horizon, primaryExch), primaryExch);
			log.info("Generating mus at horizon: " + horizon + " from " + df.format(asof) + " to " + df.format(endmillis));
			Map<Security, Map<Forecast, Double>> mus = Forecast.calculateMus(cr, forecasts, null, horizon, Time.millis2hour(asof, primaryExch));

			for (Map.Entry<Security, Map<Forecast, Double>> ent1 : mus.entrySet()) {
				Security sec = ent1.getKey();
				for (Map.Entry<Forecast, Double> ent2 : ent1.getValue().entrySet()) {
					Forecast fc = ent2.getKey();
					if (!res.containsKey(sec)) {
						if (fc != Forecast.FULL) {
							log.severe("Mu calculated for security with no advp??? " + sec.getSecId() + " " + fc.name);
						}
						continue;
					}
					if (ent2.getValue() != null) {
						res.get(sec).add(
								new NumericAttribute(new CalcAttrType(fc.name + Integer.toString(horizon)), sec, asof, ent2.getValue().doubleValue(), asof));
					}
				}
			}
		}
		return res;
	}

	private void record(Map<Security, Vector<Attribute>> results, long asof, boolean intraday) throws IOException {
		log.info("writing fit file");
		Pair<String, Writer> resfile = FileUtils.openDataDumpFile(fitdir + "/fit/fitres", intraday ? "fitres_intraday" : "fitres", asof);
		Writer writer = resfile.second;
		for (Vector<Attribute> attrs : results.values()) {
			for (Attribute attr : attrs) {
				writer.write(attr.toString() + "\n");
			}
		}
		writer.close();
		FileUtils.finalizeFile(resfile.first);
	}

	public static void main(String[] args) throws Exception {
		CommandLineParser parser = new PosixParser();
		Options options = new Options();
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("t1").withDescription("From [YYYYMMDD").create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("t2").withDescription("To YYYYMMDD)").create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("horizons").withValueSeparator(',').create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("location").withDescription("Strategy central, e.g., /apps/ase/run/useq-live").create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("exchange").create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("log").withDescription("Full path to logfile to be used").create());
		options.addOption(OptionBuilder.hasArg(true).withLongOpt("output").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("debug").withDescription("Set message level to INFO").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("intraday").withDescription("Intraday Fit").create());
		options.addOption(OptionBuilder.hasArg(false).withLongOpt("slim").withDescription("Slim Fit").create());

		CommandLine cl = parser.parse(options, args);

		String location = cl.getOptionValue("location");
		boolean slim = cl.hasOption("slim");
		Exchange.Type primaryExch = Exchange.Type.valueOf(cl.getOptionValue("exchange"));
		boolean intraday = cl.hasOption("intraday");

		Vector<Integer> horizons = new Vector<Integer>();
		for (String horizon : cl.getOptionValue("horizons").split(",")) {
			horizons.add(new Integer(horizon));
		}

		if (cl.hasOption("log")) {
			LoggerFactory.setLoggerFile(cl.getOptionValue("log"));
		}

		Properties config = null;
		try {
			config = new Properties();
			String configfile = location + "/" + "opt.cfg";
			log.info("Loading: " + configfile);
			config.load(new FileReader(configfile));
		}
		catch (Exception e) {
			log.severe("Exception encountered while loading config file");
		}

		try {
			Fit fitter = new Fit(location, horizons, primaryExch, config, intraday, slim);
			fitter.generateFitResFiles();
		}
		catch (Exception e) {
			e.printStackTrace();
			System.exit(1);
		}
	}
}
