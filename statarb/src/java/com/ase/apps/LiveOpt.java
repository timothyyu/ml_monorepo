package ase.apps;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.HashSet;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

import ase.calculator.filter.SecurityFilter;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.ExecPosition;
import ase.data.Quote;
import ase.data.Attribute;
import ase.calculator.BorrowCalculator;
import ase.data.Security;
import ase.data.Universe;
import ase.data.widget.LiveQuoteWidget;
import ase.portfolio.IdealTrades;
import ase.portfolio.OptMaster;
import ase.portfolio.Order;
import ase.portfolio.Portfolio;
import ase.portfolio.Portfolio.BorrowsUpdateMode;
import ase.portfolio.Position;
import ase.portfolio.SecurityTradeInfo;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class LiveOpt {
	private static final Logger log = LoggerFactory.getLogger(LiveOpt.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static final String OVERRIDE_FILE = "overrides.txt";

	private final LiveQuoteWidget lpWidget = LiveQuoteWidget.instance();
	{
		lpWidget.setIdentifier("liveopt");
	}

	private static final double MAX_POSITION_DIFF = 200;
	private static final double MAX_PORT_NOTIONAL_DIFF = 0.10;
	private static final double MAX_BAD_QUOTES = 0.04;
	private static final double MAX_BAD_POSITIONS = 0.05;
	private static final double MIN_BORROW_PCT = .7;

	private static final long SLEEP_MILLIS = 1000L;
	private boolean microopt = false;
	
	private final File FILLS_FILE;

	private final Set<Long> seenFiles = new HashSet<Long>(50);

	private final Properties config;
	private final Exchange.Type primaryExch;
	private final String rundir;
	private final OptMaster opt;
	private Portfolio portfolio;
	private String borrowSource;

	public LiveOpt(String rundir, Exchange.Type primaryExch, Properties config) throws Exception {
		this.rundir = rundir;
		this.primaryExch = primaryExch;
		this.config = config;
		this.borrowSource = config.getProperty("borrow_source");
		this.microopt = "true".equals(config.getProperty("microopt"));
		this.opt = new OptMaster(config, OptMaster.Mode.LIVE);
		this.opt.setScrapDir(System.getenv("SCRAP_DIR"), "live");
		FILLS_FILE = new File(rundir, "fills." + System.getenv("DATE") + ".txt");
	}

	private void loadPortfolio() throws Exception {
		portfolio = new Portfolio(config);
		//for efficiency, disable mu portfolios
		portfolio.setMuPortfoliosAutoUpdate(false);
		portfolio.restore(new File(rundir, Portfolio.SOD_PORTFOLIO));
		portfolio.loadAdjustmentsFile(new File(rundir, Portfolio.DAY_CAPADJUSTMENTS));
	}

	private boolean seen(long ts) {
		boolean seen = seenFiles.contains(ts);
		seenFiles.add(ts);
		return seen;
	}

	public void loadOverridesFile(File overrides) throws Exception {
		log.info("Loading overrides file: " + overrides.getAbsolutePath());
		BufferedReader reader = FileUtils.openFileReader(overrides);
		int cnt = 0;
		for (String line = ""; line != null; line = reader.readLine()) {
			if (line.length() <= 0 || line.startsWith("#"))
				continue;
			handleOverride(line);
			cnt++;
		}
		log.info("Loaded " + cnt + " overrides.");
		reader.close();
	}

	private void handleOverride(String line) throws Exception {
		log.info("Adding override: " + line);
		int comment_pos = line.indexOf("#");
		if (comment_pos > 0) {
			line = line.substring(0, comment_pos);
		}

		String[] fields = line.split("\\|");
		Security sec = new Security(Integer.parseInt(fields[0]));
		String type = fields[2];
		double val = Double.parseDouble(fields[3]);
		if ("rvolAdjust".equals(type)) {
			opt.adjustRVar(sec, val);
		}
		else {
			SecurityTradeInfo tradeInfo = portfolio.getSecurityTradeInfo(sec);
			if (tradeInfo == null) {
				throw new RuntimeException("Could not lookup tradeinfo on " + sec.getSecId());
			}
			if ("softMin".equals(type)) {
				tradeInfo.softmin = val;
			}
			else if ("softMax".equals(type)) {
				tradeInfo.softmax = val;
			}
			else if ("hardMin".equals(type)) {
				tradeInfo.hardmin = val;
			}
			else if ("hardMax".equals(type)) {
				tradeInfo.hardmax = val;
			}
			else if ("noTrade".equals(type)) {
				tradeInfo.tradeable = false;
				tradeInfo.expandable = false;
			}
			else if ("noExpand".equals(type)) {
                tradeInfo.expandable = false;
            }
			else {
				throw new RuntimeException("Unknown instuction in override file: " + type);
			}
		}
	}

	public void run() throws Exception {
		while (true) {
			try {
				Thread.sleep(SLEEP_MILLIS);
			}
			catch (InterruptedException ex) {
				log.severe("Main thread interrupted");
			}
			long now = Time.now();
			if (now > Exchange.closeTime(now, primaryExch)) {
				log.info("Closing time...");
				break;
			}
			NavigableMap<Long, File> crFiles = FileUtils.getDumpedFiles(rundir + "/calcres", FileUtils.CALCRES_PATTERN);
			if (crFiles.size() == 0) {
				log.severe("No calcres files found.  Waiting...");
				continue;
			}
			Long lasttime = crFiles.lastKey();
			if (!seen(lasttime)) {
			    int tries = 0;
			    while( ! calculate(crFiles.get(lasttime)) && tries++ < 10) {
			        try {
		                Thread.sleep(1000 * 20);
		            }
		            catch (InterruptedException ex) {
		                log.severe("Main thread interrupted");
		            }
			    }
			}
		}
	}

	private int checkBadPositions(Portfolio port) throws Exception {
		// The portfolio doesn't have information about whether a security
		// is alive or dead. So need to get that from the tickers file.
		File tickersFile = new File(System.getenv("RUN_DIR")+"/"+Universe.TICKER_FILE);
		Set<Security> candidates = null;
		if (tickersFile.exists()) { 
			candidates = Universe.loadFromTickersFile(tickersFile.toString());
		}
		else {
			log.severe("Failed to load tickers file " + tickersFile.toString());
			return port.size();
		}

		Map<Security, ExecPosition> posMap = lpWidget.getPositions();
		if (posMap.size() == 0) {
			log.severe("Failed to get positions from LiveQuoteWidget.");
			return port.size();
		}
		int bad = 0;
		for (Security sec : candidates) {
        	if (!sec.isAlive()) {
        		//log.warning("Skipping dead security " + sec.getSecId());
				continue;
        	}
        	Position pos = port.getPosition(sec);
        	if (pos == null) {
        		ExecPosition execPos = posMap.get(sec);
        		if(execPos != null && execPos.getPosition() != 0) {
        			bad++;
        			log.severe("Mismatched positions on " + sec.getSecId() + " us: null, them: " + execPos.getPosition());
        		}
        		continue;
        	}
        	int portPos = pos.getIntShares();
        	ExecPosition execPos = posMap.get(sec);
        	if (execPos == null) {
        		log.warning("Mismatched positions on " + sec.getSecId() + " us: " + portPos + ", them: null");
        		bad++;
        		continue;
        	}
        	if (Math.abs(execPos.getPosition() - portPos) > MAX_POSITION_DIFF) {
        		log.warning("Mismatched positions on " + sec.getSecId() + " us: " + portPos + ", them: " + execPos.getPosition());
				bad++;
        	}
		}
		
		return bad;
	}
	
	private Map<Security, Integer> getBorrow(CalcResults calcres) {
	    Map<Security, Integer> res = new HashMap<Security, Integer>();   
	    if ("ms".equals(borrowSource)) {
            log.info("Using MS borrow amounts");
            Map<Security, Attribute> borrow = calcres.getResult(BorrowCalculator.BORROW_ALLOCATED);
            if (borrow.size() > 0) {
                if (borrow.size() < MIN_BORROW_PCT * calcres.getSecurities().size()) {
                    throw new RuntimeException("Too few borrows found: " + borrow.size());
                }
                for (Security sec : borrow.keySet()) {
                    res.put(sec, (int) borrow.get(sec).asDouble());
                }
                return res;
            }
            log.severe("No MS borrows found!");
        }
	    throw new RuntimeException("Unknown borrow source: " + borrowSource);
	}

	public boolean calculate(File calcresFile) throws Exception {
		log.info("Restoring " + calcresFile.toString());

		// i'd really like not to have to create a portfolio from scratch
		// each time, should be able to load recent fills (but be careful with this!)
		// note that since the portfolio information is reloaded, tradeinfo is also recreated
		// so everything is again by default tradeable, expandable
		loadPortfolio();

		(new File(rundir + "/orders")).mkdir();
		(new File(rundir + "/ideal")).mkdir();
		(new File(rundir + "/mus")).mkdir();

		CalcResults calcres = CalcResults.restore(calcresFile, FileUtils.getFileTs(calcresFile.getName(), FileUtils.CALCRES_PATTERN));
		
		//Note that attributes are updated before fills are applied
		//Because of this, borrow ammounts are applied on the start of day position and bounds are colaculated around the start of day position.
		//Let us keep this in mind.
		///XXX Note also how updateAttrs updates prices from the calcres file, so we have up to date prices for securities from the calcres.
		portfolio.updateAttrs(calcres, getBorrow(calcres), BorrowsUpdateMode.INCREMENTAL);
		loadOverridesFile(new File(rundir, OVERRIDE_FILE));
		portfolio.loadFillsFile(FILLS_FILE);

		int badPositions = checkBadPositions(portfolio);
		if (badPositions > MAX_BAD_POSITIONS * portfolio.size()) {
			log.severe("Too many bad positions: " + badPositions + " / " + portfolio.size() + " not calculating!");
			return false;
		}

		Set<Security> tradeable = calcres.getResult(SecurityFilter.TRADEABLE).keySet();
		Map<Security, Quote> quoteMap = lpWidget.getPrices(tradeable);
		if (tradeable.size() - quoteMap.size() > MAX_BAD_QUOTES * tradeable.size()) {
			log.severe("Missing too many quotes: " + quoteMap.size() + " / " + tradeable.size() + " not calculating!");
			return false;
		}
		portfolio.updatePrices2(quoteMap, Time.now());
		opt.loadQuotes(quoteMap);

		Pair<IdealTrades,IdealTrades> idealLongShort = opt.optimize(portfolio, calcres, microopt);
		IdealTrades idealTradesFull = idealLongShort.first;
		if (idealTradesFull == null) {
			return false;
		}
		IdealTrades idealTradesShort = idealLongShort.second;
		
		if ((idealTradesFull.getNotional() - portfolio.getNotional()) / portfolio.getNotional() > MAX_PORT_NOTIONAL_DIFF) {
			log.severe("Large Portfolio Change! Optimize portfolio vs. actual at: " + idealTradesFull.getNotional() + " / " + portfolio.getNotional());
			idealTradesFull.dumpIdealPortfolio(rundir + "/ideal", calcres.getAsOf(), "ideal.BAD");
			idealTradesFull.dumpMus(rundir + "/mus", "mus.BAD");
			idealTradesFull.dumpOrders(rundir + "/orders", "orders.FULL.BAD");
			return false;
		}
		
	    idealTradesFull.dumpIdealPortfolio(rundir + "/ideal", calcres.getAsOf(), "ideal.FULL");
        idealTradesFull.dumpMus(rundir + "/mus", "mus.FULL");
        idealTradesFull.dumpOrders(rundir + "/orders", "orders.FULL");
		if (idealTradesShort != null) { 
		    idealTradesShort.dumpIdealPortfolio(rundir + "/ideal", calcres.getAsOf(), "ideal.SHORT");
		    idealTradesShort.dumpMus(rundir + "/mus", "mus.SHORT");
		    idealTradesShort.dumpOrders(rundir + "/orders", "orders.SHORT");
            for (Order o : idealTradesShort.getOrders()) {
                Order longorder = idealTradesFull.getOrder(o.sec);
                if ( longorder == null ) {
                    log.warning("No matching long order for " + o);
                }
                else if ( !ASEMath.sameSign(o.shares, longorder.shares) ) {
                    log.warning("Going in different directions! short: " + o + " long: " + longorder);
                }
            }
		}
		if (calcres.getAsOf() - Exchange.openTime(calcres.getAsOf(), primaryExch) > Time.MILLIS_PER_HOUR) {
		    if ( idealTradesShort == null || (Exchange.closeTime(calcres.getAsOf(), primaryExch) - calcres.getAsOf()) < Time.MILLIS_PER_HOUR * .75) {
		        idealTradesFull.dumpIdealPortfolio(rundir + "/ideal", calcres.getAsOf(), "ideal");
		        idealTradesFull.dumpMus(rundir + "/mus", "mus");
		        idealTradesFull.dumpOrders(rundir + "/orders", "orders");
		    }
		    else {
                idealTradesShort.dumpIdealPortfolio(rundir + "/ideal", calcres.getAsOf(), "ideal");
                idealTradesShort.dumpMus(rundir + "/mus", "mus");
                idealTradesShort.dumpOrders(rundir + "/orders", "orders");		        
		    }
		}
		return true;
	}

	public static void main(String argv[]) {
		String location = null;
		String logfile = null;
		Exchange.Type exch = null;

		try {
			for (int i = 0; i < argv.length; i++) {
				if (argv[i].equals("-location"))
					location = argv[++i];
				if (argv[i].equals("-exchange"))
					exch = Exchange.Type.valueOf(argv[++i]);
				if (argv[i].equals("-log"))
					logfile = argv[++i];
			}
		}
		catch (Exception e) {
			System.out.println("Invalid arguments:" + e.toString());
			System.exit(1);
		}
		if (location == null || exch == null) {
			System.out.println("Must specify -location and -exchange");
			System.exit(1);
		}
		if (logfile != null) {
			LoggerFactory.setLoggerFile(logfile);
			LoggerFactory.setUnsupervisedMode(true);
		}

		Properties config = new Properties();
		try {
			config.load(new FileReader(location + "/opt.cfg"));
		}
		catch (Exception e) {
			log.log(Level.SEVERE, "Exception countered while loading config file", e);
			e.printStackTrace();
			System.exit(1);
		}

		try {
			LiveOpt calc = new LiveOpt(location, exch, config);
			calc.run();
		}
		catch (Exception e) {
			log.severe("Exception encountered during calcs for Optimization");
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
			}
			e.printStackTrace();
			System.exit(1);
		}
	}
}
