package ase.apps;

import java.io.File;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.Vector;
import java.util.concurrent.Callable;
import java.util.logging.Logger;

import ase.apps.SimOpt.SimType;
import ase.calculator.BorrowCalculator;
import ase.calculator.Forecast;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Price;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.AseDBConn;
import ase.portfolio.Fill;
import ase.portfolio.IdealTrades;
import ase.portfolio.OptMaster;
import ase.portfolio.OptMaster.Mode;
import ase.portfolio.Portfolio;
import ase.portfolio.Portfolio.BorrowsUpdateMode;
import ase.portfolio.PortfolioUtils;
import ase.portfolio.SecurityTradeInfo;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.Pair;
import ase.util.Time;

public class SimOptWorker implements Callable<Boolean> {
	private static enum DelayType {EOD, MINS};
	private static final double MIN_BORROW_PCT = .8;

	private final Logger log;
	private final SimType simType;
	private final String simdir;
	private final String baseDir;
	private final String name;
	private final Portfolio portfolio;
	private final OptMaster opt;
	private final String borrowSource;
	private boolean microOpt = false;
	private final UnifiedDataSource uSource = new UnifiedDataSource(false);
	private final long delay;
	private final DelayType delayType;
	private final Exchange.Type primaryExch;
	private BorrowsUpdateMode bum;

	public SimOptWorker(SimType simType, String simdir, String name, Portfolio portfolio, Set<Forecast> affectedForecasts, Properties config, Logger log) {
		this.simType = simType;
		this.simdir = simdir;
		this.name = name;
		this.portfolio = portfolio;
		this.portfolio.setLogger(log);
		this.log = log;
		this.opt = new OptMaster(config, Mode.SIM);
		this.opt.setLogger(log);
		this.borrowSource = config.getProperty("borrow_source");
		this.microOpt = "true".equals(config.getProperty("microopt"));
		if (config.getProperty("delay").equalsIgnoreCase("eod")) {
			this.delayType = DelayType.EOD;
			this.delay = 0;
		}
		else {
			this.delayType = DelayType.MINS;
			this.delay = (long) (Double.parseDouble(config.getProperty("delay")) * Time.MILLIS_PER_MINUTE);
		}
		this.primaryExch = Exchange.Type.valueOf(config.getProperty("exchange"));
		
		if (this.borrowSource.equals("ms"))
			this.bum = BorrowsUpdateMode.INCREMENTAL;
		else if (this.borrowSource.equals("msglobal"))
			this.bum = BorrowsUpdateMode.ABSOLUTE;
		else
			throw new RuntimeException("Unknown borrows source");
		
		//simtype dependent portion
		switch (this.simType) {
		case FULL:
			this.baseDir = this.simdir;
			this.opt.setScrapDir(simdir+"/scrap", this.name);
			break;
		case MARGINAL:
			this.baseDir = this.simdir + "/marginals/"+this.name;
			this.opt.setScrapDir(simdir+"/scrap", "marginal_"+this.name);
			this.opt.enableAllForecasts();
			this.opt.disableForecasts(affectedForecasts);
			break;
		case SINGLE:
			this.baseDir = this.simdir + "/singles/"+this.name;
			this.opt.setScrapDir(simdir+"/scrap", "single_"+this.name);
			this.opt.disableForecasts(this.opt.getForecasts());
			this.opt.enableForecasts(affectedForecasts);
			break;
		default:
			throw new RuntimeException("Unknown simulation type");	
		}
	}
	
	public Boolean call() throws Exception {
		try {
			calculate();
			log.info("Thread completed successfully");
			return true;
		}
		catch (Throwable e) {
			log.severe("Exception encountered during calcs for Optimization");
			log.severe(e.toString());
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
			}
			return false;
		}
	}

	public boolean calculate() throws Exception {
		log.info("Operating on portfolio " + name);
		long lastupdate = 0L;
		(new File(this.baseDir)).mkdirs();

		NavigableMap<Long, File> calcresFiles = null;
		synchronized (FileUtils.class) {
			calcresFiles = FileUtils.getDumpedFiles(simdir + "/calcres", FileUtils.CALCRES_PATTERN);
		}

		// see if the calcres file timestamps are properly spaced
		if (!validateDelay(delay, calcresFiles.keySet())) {
			log.severe("Provided delay and calcreses are incompatible. Not computing");
			throw new Exception("Provided delay and calcreses are incompatible. Not computing");
		}

		for (Map.Entry<Long, File> file : calcresFiles.entrySet()) {
			log.info("Restoring " + file.getValue());
			CalcResults calcres = CalcResults.restore(file.getValue(), file.getKey());
			// The borrows update mode for this iteration only
			BorrowsUpdateMode iterationBum;

			// if new day
			if (Time.midnight(calcres.getAsOf()) != Time.midnight(lastupdate)) {
				portfolio.clearFills();
				portfolio.updateSplitsAndDividends(calcres, true);
				iterationBum = bum;
			}
			// if same day
			else {
				iterationBum = BorrowsUpdateMode.IGNORE;
			}

			// /XXX reset status, it will be updated from scratch
			Iterator<Map.Entry<Security, SecurityTradeInfo>> stii = portfolio.getSecurityTradeInfo();
			while (stii.hasNext()) {
				SecurityTradeInfo sti = stii.next().getValue();
				sti.tradeable = false;
				sti.expandable = false;
			}

			portfolio.updateAttrs(calcres, getBorrow(calcres, portfolio), iterationBum);
			opt.loadQuotes(portfolio);

			Pair<IdealTrades, IdealTrades> idealLongShort = opt.optimize(portfolio, calcres, microOpt);
			IdealTrades idealTradesFull = idealLongShort.first;
			if (idealTradesFull == null) {
				return false;
			}
			IdealTrades idealTradesShort = idealLongShort.second;

			Map<Security, Price> fillPrices = null;
			long fillTs = getFillTs(calcres.getAsOf());
			if (fillTs != calcres.getAsOf()) {
				// XXX remove this at some point
				if (Exchange.closeTime(calcres.getAsOf(), primaryExch) == calcres.getAsOf()) {
					log.severe("Calcres timestamp at close of day " + calcres.getAsOf() + " and delay>0. Will fill at the end of day price");
					fillTs = calcres.getAsOf();
				}
				else {
					//fillTs = calcres.getAsOf() + delay;
					fillPrices = this.uSource.getPriceAtTs(portfolio.getSecurities(), fillTs, primaryExch);
					portfolio.updatePrices2(fillPrices, fillTs);
				}
			}

			List<Fill> fills = null;
			if (calcres.getAsOf() - Exchange.openTime(calcres.getAsOf(), primaryExch) > Time.MILLIS_PER_HOUR) {
				if (idealTradesShort == null || (Exchange.closeTime(calcres.getAsOf(), primaryExch) - calcres.getAsOf()) < Time.MILLIS_PER_HOUR * .75) {
					log.info("Using full trade list...");
					idealTradesFull.dumpMus(baseDir + "/mus", "mus");
					idealTradesFull.dumpOrders(baseDir + "/orders", "orders");
					fills = portfolio.addIdealTrades(idealTradesFull.getOrders(), fillPrices, fillTs);
				}
				else {
					log.info("Using short trade list...");
					idealTradesShort.dumpMus(baseDir + "/mus", "mus");
					idealTradesShort.dumpOrders(baseDir + "/orders", "orders");
					fills = portfolio.addIdealTrades(idealTradesShort.getOrders(), fillPrices, fillTs);
				}
			}
			else {
				log.info("Waiting until 10:30 to make tradelist...");
			}

			portfolio.updatePortfolioStats();
			log.info(portfolio.name + "|" + portfolio.stats.getLatestStats().toString());

			// XXX The portfolio at any time contains the day's fills. We want to dump only this iterations fills
			// portfolio.dumpFills(baseDir + "/fills");
			if (fills != null) {
				PortfolioUtils.dumpFills(baseDir + "/fills", fills, portfolio.getAsOf());
			}
			portfolio.dumpPositions(baseDir + "/positions");
			portfolio.dumpMuPortfolios(baseDir + "/positions");

			lastupdate = calcres.getAsOf();
		}

		portfolio.dumpStats(baseDir + "/stats");
		return true;
	}

	private long getFillTs(long calcTs) {
		if (calcTs == Exchange.closeTime(calcTs, primaryExch) && delayType == DelayType.MINS && delay > 0) {
			log.severe("Calcres timestamp at end of day and fill delay >0... You shouldn't be doing stuff like this mister");
			return calcTs;
		}
		else if (delayType == DelayType.EOD) {
			return Exchange.closeTime(calcTs, primaryExch);
		}
		else if (delayType == DelayType.MINS) {
			return calcTs + delay;
		}
		else {
			throw new RuntimeException("We should have never reached this point");
		}
	}
	
	private boolean validateDelay(long delay, Set<Long> calcresTs) {
		Vector<Long> cts = new Vector<Long>(calcresTs);
		for (int i = 0; i < cts.size(); i++) {
			long pasof = (i > 0) ? cts.get(i - 1) : 0;
			long casof = cts.get(i);

			if (getFillTs(casof) > Exchange.closeTime(casof, this.primaryExch)) {
				log.severe("Problematic calcres ts: " + ASEFormatter.getInstance().debugFormat(casof));
				return false;
			}
			if (getFillTs(pasof) >= casof) {
				log.severe("Problematic calcres tss: " + ASEFormatter.getInstance().debugFormat(pasof) + " " + ASEFormatter.getInstance().debugFormat(casof));
				return false;
			}
		}

		return true;
	}

	private Map<Security, Integer> getBorrow(CalcResults calcres, Portfolio port) {
		Set<Security> secs = new HashSet<Security>();
		secs.addAll(calcres.getSecurities());
		secs.addAll(port.getSecurities());

		Map<Security, Integer> res = new HashMap<Security, Integer>();

		Map<Security, Attribute> borrow = null;
		if ("ms".equals(borrowSource)) {
			log.info("Using MS borrow allocated amounts");
			borrow = calcres.getResult(BorrowCalculator.BORROW_ALLOCATED);
		}
		else if ("msglobal".equals(borrowSource)) {
			log.info("Using MS borrow global amounts");
			borrow = calcres.getResult(BorrowCalculator.BORROW_AVAILABILITY);
		}
		else {
			throw new RuntimeException("Unknown borrow source: " + borrowSource);
		}

		if (borrow.size() > MIN_BORROW_PCT * secs.size()) {
			for (Security sec : secs) {
				int avail_borrow_amt = borrow.containsKey(sec) ? (int) borrow.get(sec).asDouble() : 0;
				res.put(sec, Math.max(avail_borrow_amt, avail_borrow_amt));
			}
			return res;
		}
		log.severe("Too few borrows found (" + borrow.size() + "), Falling back on previous days borrows!");
		Iterator<Map.Entry<Security, SecurityTradeInfo>> itr = port.getSecurityTradeInfo();
		while (itr.hasNext()) {
			Map.Entry<Security, SecurityTradeInfo> ent = itr.next();
			res.put(ent.getKey(), ent.getValue().borrow);
		}
		return res;
	}
}
