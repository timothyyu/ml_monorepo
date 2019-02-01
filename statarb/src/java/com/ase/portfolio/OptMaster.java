package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Random;
import java.util.Set;
import java.util.Vector;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

import ase.calculator.FactorCalculator;
import ase.calculator.Forecast;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Quote;
import ase.data.Security;
import ase.reports.OptReports;
import ase.util.ASEFormatter;
import ase.util.Counter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class OptMaster {
	public enum Mode {
		SIM, LIVE
	};

	private Logger log = LoggerFactory.getLogger(OptMaster.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public final static long MAX_QUOTE_AGE = Time.fromMinutes(5);

	public final static double MIN_TRADEABLE_PCT = .50;
	public final static double MIN_SPREAD = .00001;

	private final Mode mode;
	private final Collection<Forecast> forecasts = new Vector<Forecast>();
	private final Collection<Forecast> disabledForecasts = new HashSet<Forecast>();

	private final Map<Security, Double> rvarAdjustments = new HashMap<Security, Double>();

	private Map<Security, Quote> quoteMap = new HashMap<Security, Quote>();
	private Set<Security> tradeable = new HashSet<Security>();

	private final Exchange.Type primaryExch;

	private String scrapDir;
	private String optFileId = null;
	private final String opt_script;
	private final double max_sumnot;
	private final double max_expnot;
	private final double max_trdnot;
	private final double max_posnot;
	private final double max_spread_abs;
	private final double max_spread_bps;
	private final double kappa;
	private final double slipCoef;
	private final double slipConst;
	private final double slip_multiplier;
	private final double horizon_long;
	private final double horizon_short;
	private final double aggr_threshold;
	private final double high_agg_prob;
	private final int min_iter;
	private final int max_iter;
	private final int max_iter_short;
	private final int zero_start;
	private final boolean multiThread;
	private final Logger fullLocalLog;
	private final Logger microLocalLog;

	private class OptInput {
		public int secid;
		public double position;
		public double lbound;
		public double ubound;
		public double mu;
		public double rvar;
		public double advp;
		public double borrowRate;
		public double price;

		public String toString() {
			// XXX a bit of hack for our optimizer which seems to be troubled by equality constraints lbound=position=ubound. turn them to round doubles
			if (lbound == position && position == ubound)
				return "S|" + secid + "|" + Math.round(position) + "|" + Math.round(lbound) + "|" + Math.round(ubound) + "|" + mu + "|" + rvar + "|" + advp
						+ "|" + borrowRate + "|" + price;
			else
				return "S|" + secid + "|" + position + "|" + lbound + "|" + ubound + "|" + mu + "|" + rvar + "|" + advp + "|" + borrowRate + "|" + price;
		}

		public OptInput clone() {
			OptInput oi = new OptInput();
			oi.secid = this.secid;
			oi.position = this.position;
			oi.lbound = this.lbound;
			oi.ubound = this.ubound;
			oi.mu = this.mu;
			oi.rvar = this.rvar;
			oi.advp = this.advp;
			oi.borrowRate = this.borrowRate;
			oi.price = this.price;
			return oi;
		}
	}

	public OptMaster(Properties config, Mode mode) {
		log.info("Initializing Optimizer");

		this.mode = mode;
		// If we are live, pipe the optimization iterations to separate files, besides the master log file
		if (this.mode == Mode.LIVE) {
			fullLocalLog = LoggerFactory.getIndependentLogger("liveopt_full", Level.INFO, System.getenv("LOG_DIR") + "/liveopt.full.log");
			microLocalLog = LoggerFactory.getIndependentLogger("liveopt_micro", Level.INFO, System.getenv("LOG_DIR") + "/liveopt.micro.log");
		}
		else {
			fullLocalLog = microLocalLog = null;
		}

		this.primaryExch = Exchange.Type.valueOf(config.getProperty("exchange"));
		this.max_sumnot = Double.parseDouble(config.getProperty("max_sumnot"));
		this.max_expnot = Double.parseDouble(config.getProperty("max_expnot"));
		this.max_trdnot = Double.parseDouble(config.getProperty("max_trdnot"));
		this.max_posnot = Double.parseDouble(config.getProperty("max_posnot"));

		this.max_spread_abs = Double.parseDouble(config.getProperty("max_spread_abs"));
		this.max_spread_bps = Double.parseDouble(config.getProperty("max_spread_bps"));
		this.kappa = Double.parseDouble(config.getProperty("kappa"));
		this.slipCoef = Double.parseDouble(config.getProperty("slipCoef"));
		this.slipConst = Double.parseDouble(config.getProperty("slipConst"));
		this.slip_multiplier = Double.parseDouble(config.getProperty("slip_multiplier"));

		this.horizon_long = Double.parseDouble(config.getProperty("horizon_long"));
		this.horizon_short = Double.parseDouble(config.getProperty("horizon_short", ".0417"));
		this.aggr_threshold = Double.parseDouble(config.getProperty("aggr_threshold")) / 10000.0;
		this.max_iter = Integer.parseInt(config.getProperty("max_iter"));
		this.min_iter = Integer.parseInt(config.getProperty("min_iter"));

		this.max_iter_short = Integer.parseInt(config.getProperty("max_iter_short", "0"));
		this.high_agg_prob = Double.parseDouble(config.getProperty("high_agg_prob", "0.0"));
		this.zero_start = Integer.parseInt(config.getProperty("zero_start", "0"));
		this.opt_script = config.getProperty("opt_script", "optimizer6.py");

		this.multiThread = Boolean.parseBoolean(config.getProperty("multi_thread", "false"));

		this.forecasts.addAll(Forecast.loadDefs(config));

		this.scrapDir = System.getenv("SCRAP_DIR");
		this.optFileId = null;
	}

	public void setScrapDir(String dir) {
		this.scrapDir = dir;
	}

	public void setScrapDir(String dir, String optFileId) {
		this.scrapDir = dir;
		this.optFileId = optFileId;
	}

	public void setLogger(Logger log) {
		this.log = log;
	}

	public void adjustRVar(Security sec, double adj) {
		if (adj > .001 || adj < -.001) {
			throw new RuntimeException("Suspicious rvar for " + sec.getSecId() + " of " + adj);
		}
		rvarAdjustments.put(sec, adj);
	}

	// used by LiveOpt (uses mids from quoteserver)
	public void loadQuotes(Map<Security, Quote> qMap) {
		quoteMap.putAll(qMap);
	}

	// used by SimOpt (uses latest prices)
	public void loadQuotes(Portfolio port) {
		for (Position pos : port.getPositions()) {
			if (!(pos.getPriceTs() > 0))
				continue;
			quoteMap.put(pos.sec, new Quote(pos.getLatestPrice(), pos.getLatestPrice(), pos.getPriceTs()));
		}
	}

	private void processQuotes(Portfolio port) {
		tradeable.clear();
		Iterator<Map.Entry<Security, SecurityTradeInfo>> tradeinfo = port.getSecurityTradeInfo();
		long now = mode == Mode.LIVE ? Time.now() : port.getAsOf();
		while (tradeinfo.hasNext()) {
			Map.Entry<Security, SecurityTradeInfo> ti = tradeinfo.next();
			if (!ti.getValue().tradeable)
				continue;
			Security sec = ti.getKey();

			Quote quote = quoteMap.get(sec);
			if (quote != null) {
				double spread = quote.getSpread();
				if (!Double.isNaN(spread) && spread < max_spread_abs && quote.getSpreadBps() < max_spread_bps && now - quote.getTs() < MAX_QUOTE_AGE) {
					if (spread > MIN_SPREAD || mode == Mode.SIM) {
						tradeable.add(sec);
					}
				}
				else {
					log.warning("Not trading security due to bad quote: " + sec.getSecId() + " " + quote);
				}
			}
		}
	}

	public Pair<IdealTrades, IdealTrades> optimize(Portfolio portfolio, CalcResults calcres, boolean microOpt) throws Exception {
		int hour = Time.millis2hour(calcres.getAsOf(), primaryExch);
		log.info("Using hour " + hour + " at " + df.debugFormat(calcres.getAsOf()));
		Map<Security, Map<Forecast, Double>> mus = Forecast.calculateMus(calcres, forecasts, disabledForecasts, horizon_long, hour);
		Map<Security, Map<Forecast, Double>> short_mus = Forecast.calculateMus(calcres, forecasts, disabledForecasts, horizon_short, hour);
		Map<Security, Map<Forecast, Double>> day_mus = Forecast.calculateMus(calcres, forecasts, disabledForecasts, 1, hour);

		Map<Security, Attribute> rvars = calcres.getResult(FactorCalculator.RVAR_ATTR);
		Map<Security, Double> rvarForecasts = Forecast.calculateRvars(calcres, forecasts, disabledForecasts, horizon_long);

		processQuotes(portfolio);
		if (tradeable.size() < MIN_TRADEABLE_PCT * portfolio.size()) {
			log.severe("Not Optimizing: tradeable stocks below threshold " + tradeable.size() + " / " + portfolio.size());
			return null;
		}

		Map<Security, Pair<Double, Double>> finalBounds = new HashMap<Security, Pair<Double, Double>>();
		Vector<String> optInputLong = new Vector<String>();
		Vector<String> optInputShort = new Vector<String>();
		Counter lbc = new Counter("lb");
		Counter ubc = new Counter("ub");
		Counter rvarc = new Counter("rvar");
		Counter muc = new Counter("mu");
		for (Position pos : portfolio.getPositions()) {
			if (pos.getIntShares() == 0 && !tradeable.contains(pos.sec))
				continue;

			if (!pos.isValid()) {
				log.severe("Not including in optimization invalid position " + pos.toString());
				continue;
			}

			OptInput oi_long = new OptInput();
			Security sec = pos.sec;
			SecurityTradeInfo ti = portfolio.getSecurityTradeInfo(sec);

			double price = quoteMap.get(sec) == null ? pos.getLatestPrice() : quoteMap.get(sec).getPrice();
			ti.calcBounds(pos.notional(), price);

			oi_long.secid = sec.getSecId();
			oi_long.position = pos.notional();
			oi_long.price = price;
			oi_long.mu = mus.containsKey(sec) ? mus.get(sec).get(Forecast.FULL) : 0.0;

			double rvar = rvars.get(sec) == null ? Double.NaN : rvars.get(sec).asDouble();
			if (!(rvar > 0)) {
				if (tradeable.contains(sec)) {
					log.severe("Bad rvar for " + sec.getSecId() + ". Not trading.  Let's get rid of our " + pos.getIntShares() + " share position!");
				}
				rvar = 0.0;
				tradeable.remove(sec);
			}
			Double rvarForecast = rvarForecasts.get(sec);
			if (rvarForecast != null && !rvarForecast.isNaN()) {
				rvar += rvarForecast.doubleValue();
			}
			if (rvarAdjustments.containsKey(sec)) {
				rvar += rvarAdjustments.get(sec);
			}
			oi_long.rvar = rvar * horizon_long;
			oi_long.advp = ti.advp;
			oi_long.borrowRate = ti.borrow_rate * (horizon_long / (double) Time.BIZ_DAYS_PER_YEAR);

			if (tradeable.contains(sec)) {
				oi_long.lbound = ti.getLBound();
				oi_long.ubound = ti.getUBound();
			}
			else {
				oi_long.lbound = oi_long.ubound = oi_long.position;
			}
			if (pos.notional() < oi_long.lbound || pos.notional() > oi_long.ubound) {
				log.warning("Security " + sec.getSecId() + " has position " + pos.notional() + " outside of " + oi_long.lbound + ", " + oi_long.ubound);
			}

			optInputLong.add(oi_long.toString());

			// update short term inputs
			OptInput oi_short = oi_long.clone();
			oi_short.mu = short_mus.containsKey(sec) ? short_mus.get(sec).get(Forecast.FULL) : 0.0;
			oi_short.rvar = rvar * horizon_short;
			oi_short.borrowRate = ti.borrow_rate * (horizon_short / (double) Time.BIZ_DAYS_PER_YEAR);
			optInputShort.add(oi_short.toString());

			lbc.add(oi_long.lbound);
			ubc.add(oi_long.ubound);
			rvarc.add(oi_long.rvar);
			muc.add(oi_long.mu);

			finalBounds.put(sec, new Pair<Double, Double>(oi_long.lbound, oi_long.ubound));
		}
		log.info(lbc.toString());
		log.info(ubc.toString());
		log.info(rvarc.toString());
		log.info(muc.toString());

		int seccnt = optInputLong.size();
		int factorcnt = calcres.getFactorCount(true, false);

		// factor exposure matrix
		Map<Security, Map<AttrType, Attribute>> factors = calcres.getFactorExposures(true, false);
		for (Map.Entry<Security, Map<AttrType, Attribute>> secs : factors.entrySet()) {
			for (Map.Entry<AttrType, Attribute> facs : secs.getValue().entrySet()) {
				optInputLong.add("F|" + secs.getKey().getSecId() + "|" + facs.getKey() + "|" + facs.getValue().asDouble());
				optInputShort.add("F|" + secs.getKey().getSecId() + "|" + facs.getKey() + "|" + facs.getValue().asDouble());
			}
		}

		Iterator<Map.Entry<Pair<AttrType, AttrType>, Double>> it = calcres.getFactorCov();
		while (it.hasNext()) {
			Map.Entry<Pair<AttrType, AttrType>, Double> n = it.next();
			optInputLong.add("C|" + n.getKey().first + "|" + n.getKey().second + "|" + n.getValue() * horizon_long);
			optInputShort.add("C|" + n.getKey().first + "|" + n.getKey().second + "|" + n.getValue() * horizon_short);
		}

		// Invoke the optimizers now
		ExecutorService executor = Executors.newFixedThreadPool(multiThread ? 2 : 1);
		Future<IdealTrades> fullTask = executor.submit(new ExternalOptimizerTask(this, "full", fullLocalLog, optInputLong, calcres.getAsOf(), seccnt,
				factorcnt, short_mus, day_mus, slipConst, min_iter, max_iter));
		Future<IdealTrades> microTask = null;
		if (microOpt) {
			log.info("MicroOptimizing at " + df.debugFormat(portfolio.getAsOf()));
			microTask = executor.submit(new ExternalOptimizerTask(this, "micro", microLocalLog, optInputShort, calcres.getAsOf(), seccnt, factorcnt, short_mus,
					day_mus, slipConst * slip_multiplier, min_iter, max_iter_short));
		}

		executor.shutdown();
		executor.awaitTermination(1000, TimeUnit.SECONDS);

		IdealTrades idealPortfolio = fullTask.get();
		idealPortfolio.calculateOrders(portfolio, mus, quoteMap, high_agg_prob);

		log.info("Reports at the full optimum");
		OptReports.constraintTightnessReport(idealPortfolio, finalBounds, max_expnot * max_sumnot, calcres, log);
		OptReports.factorExposureReport(idealPortfolio, calcres, log);

		IdealTrades idealPortfolioShort = null;
		if (microOpt) {
			idealPortfolioShort = microTask.get();
			idealPortfolioShort.calculateOrders(portfolio, short_mus, quoteMap, high_agg_prob);
		}
		return new Pair<IdealTrades, IdealTrades>(idealPortfolio, idealPortfolioShort);
	}

	// private IdealTrades callExternalOptimizer(Vector<String> optInput, long trade_ts, int seccnt, int factorcnt, Map<Security, Map<Forecast, Double>>
	// hour_mus,
	// Map<Security, Map<Forecast, Double>> day_mus, double slipConst, int max_iter) throws Exception {
	// log.info("Calling external optimizer...");
	//
	// // XXX need a much better way of sedning this data to the optimizer
	// String optfilename = (optFileId != null) ? scrapDir + "/opt." + optFileId + "." + trade_ts + ".tmp" : scrapDir + "/opt." + trade_ts + "." + max_iter
	// + ".tmp";
	// String optbin = System.getenv("BIN_DIR") + "/" + opt_script;
	// PrintWriter out = new PrintWriter(new OutputStreamWriter(new FileOutputStream(optfilename)));
	// for (String line : optInput) {
	// out.println(line);
	// }
	// out.close();
	//
	// log.info("Running: " + optbin + " optfile:" + optfilename + " max_iter:" + max_iter + " num_secs:" + seccnt + " num_factors:" + factorcnt + " kappa:"
	// + kappa + " slipCoef:" + slipCoef + " slipConst:" + slipConst + " max_sumnot:" + max_sumnot + " max_expnot:" + max_expnot + " max_trdnot:"
	// + max_trdnot + "zero_start:" + zero_start);
	//
	// ProcessBuilder pb = new ProcessBuilder(optbin, "optfile:" + optfilename, "max_iter:" + max_iter, "num_secs:" + seccnt, "num_factors:" + factorcnt,
	// "kappa:" + kappa, "slipCoef:" + slipCoef, "slipConst:" + slipConst, "max_sumnot:" + max_sumnot, "max_expnot:" + max_expnot, "max_trdnot:"
	// + max_trdnot, "zero_start:" + zero_start);
	//
	// pb.directory(new File(System.getenv("BIN_DIR")));
	// pb.redirectErrorStream(true);
	// Process p = pb.start();
	//
	// IdealTrades idealPortfolio = new IdealTrades(trade_ts, seccnt, primaryExch);
	// BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));
	// boolean completed = false;
	// for (String line = ""; line != null; line = reader.readLine()) {
	// if (line.startsWith("T|")) {
	// String[] fields = line.split("\\|");
	//
	// // XXX need to watch creating new securities
	// Security sec = new Security(Integer.parseInt(fields[2]));
	//
	// // Set aggression level
	// double hour_mu = hour_mus.get(sec) == null ? 0.0 : hour_mus.get(sec).get(Forecast.FULL);
	// double day_mu = day_mus.get(sec) == null ? 0.0 : day_mus.get(sec).get(Forecast.FULL);
	//
	// idealPortfolio.add(sec,
	// new OptInfo(Double.parseDouble(fields[3]), Double.parseDouble(fields[4]), Double.parseDouble(fields[5]), Double.parseDouble(fields[6]),
	// Double.parseDouble(fields[7]), Double.parseDouble(fields[8]), hour_mu, day_mu, Double.parseDouble(fields[9])));
	// }
	// else if (line.equals("DONE")) {
	// completed = true;
	// break;
	// }
	// else {
	// log.info("Optimizer: " + line);
	// }
	// }
	// if (!completed) {
	// throw new Exception("Optimization Failed!!");
	// }
	// p.destroy();
	//
	// return idealPortfolio;
	// }

	public void disableForecasts(Collection<Forecast> dis) {
		disabledForecasts.addAll(dis);
	}

	public void enableForecasts(Collection<Forecast> en) {
		disabledForecasts.removeAll(en);
	}

	public void enableAllForecasts() {
		disabledForecasts.clear();
	}

	public Collection<Forecast> getForecasts() {
		return forecasts;
	}

	protected static class ExternalOptimizerTask implements Callable<IdealTrades> {
		protected final OptMaster father;
		protected final String name;
		protected final Vector<String> optInput;
		protected final long trade_ts;
		protected final int seccnt;
		protected final int factorcnt;
		protected final Map<Security, Map<Forecast, Double>> hour_mus;
		protected final Map<Security, Map<Forecast, Double>> day_mus;
		protected final double slipConst;
		protected final int max_iter;
		protected final int min_iter;
		protected final Logger localLog;
		protected final StringBuilder fullMsg;

		public ExternalOptimizerTask(OptMaster father, String name, Logger localLog, Vector<String> optInput, long trade_ts, int seccnt, int factorcnt,
				Map<Security, Map<Forecast, Double>> hour_mus, Map<Security, Map<Forecast, Double>> day_mus, double slipConst, int min_iter, int max_iter) {
			super();
			this.father = father;
			this.name = name;
			this.optInput = optInput;
			this.trade_ts = trade_ts;
			this.seccnt = seccnt;
			this.factorcnt = factorcnt;
			this.hour_mus = hour_mus;
			this.day_mus = day_mus;
			this.slipConst = slipConst;
			this.min_iter = min_iter;
			this.max_iter = max_iter;
			this.localLog = localLog;
			this.fullMsg = new StringBuilder();
		}

		protected void log(String msg) {
			this.fullMsg.append(msg);
			this.fullMsg.append("\n");
			if (this.localLog != null)
				this.localLog.info(msg);
		}

		@Override
		public IdealTrades call() throws Exception {
			log("Calling external optimizer...");

			// XXX need a much better way of sedning this data to the optimizer
			String optfilename = (father.optFileId != null) ? father.scrapDir + "/opt." + father.optFileId + "." + name + "." + trade_ts + ".tmp"
					: father.scrapDir + "/opt." + name + "." + trade_ts + ".tmp";
			String optbin = System.getenv("BIN_DIR") + "/" + father.opt_script;
			PrintWriter out = new PrintWriter(new OutputStreamWriter(new FileOutputStream(optfilename)));
			for (String line : optInput) {
				out.println(line);
			}
			out.close();

			log("Running: " + optbin + " optfile:" + optfilename + " min_iter:" + min_iter + " max_iter:" + max_iter + " num_secs:" + seccnt + " num_factors:"
					+ factorcnt + " kappa:" + father.kappa + " slipCoef:" + father.slipCoef + " slipConst:" + father.slipConst + " max_sumnot:"
					+ father.max_sumnot + " max_expnot:" + father.max_expnot + " max_trdnot:" + father.max_trdnot + " max_posnot:" + father.max_posnot
					+ " zero_start:" + father.zero_start);

			ProcessBuilder pb = new ProcessBuilder(optbin, "optfile:" + optfilename, "min_iter:" + min_iter, "max_iter:" + max_iter, "num_secs:" + seccnt,
					"num_factors:" + factorcnt, "kappa:" + father.kappa, "slipCoef:" + father.slipCoef, "slipConst:" + slipConst, "max_sumnot:"
							+ father.max_sumnot, "max_expnot:" + father.max_expnot, "max_trdnot:" + father.max_trdnot, "max_posnot:" + father.max_posnot,
					"zero_start:" + father.zero_start);

			pb.directory(new File(System.getenv("BIN_DIR")));
			pb.redirectErrorStream(true);
			Process p = pb.start();

			IdealTrades idealPortfolio = new IdealTrades(trade_ts, seccnt, father.primaryExch);
			BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));
			boolean completed = false;
			for (String line = ""; line != null; line = reader.readLine()) {
				if (line.startsWith("T|")) {
					String[] fields = line.split("\\|");

					// XXX need to watch creating new securities
					Security sec = new Security(Integer.parseInt(fields[2]));

					// Set aggression level
					double hour_mu = hour_mus.get(sec) == null ? 0.0 : hour_mus.get(sec).get(Forecast.FULL);
					double day_mu = day_mus.get(sec) == null ? 0.0 : day_mus.get(sec).get(Forecast.FULL);

					idealPortfolio.add(
							sec,
							new OptInfo(Double.parseDouble(fields[3]), Double.parseDouble(fields[4]), Double.parseDouble(fields[5]), Double
									.parseDouble(fields[6]), Double.parseDouble(fields[7]), Double.parseDouble(fields[8]), hour_mu, day_mu, Double
									.parseDouble(fields[9])));
				}
				else if (line.equals("DONE")) {
					completed = true;
					break;
				}
				else {
					log("Optimizer: " + line);
				}
			}
			if (!completed) {
				// log the entire message now
				father.log.info(this.fullMsg.toString());
				throw new Exception("Optimization Failed!!");
			}
			p.destroy();

			// log the entire message now
			father.log.info(this.fullMsg.toString());

			return idealPortfolio;
		}

	}
}
