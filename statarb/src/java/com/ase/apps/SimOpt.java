package ase.apps;

import java.io.File;
import java.io.FileReader;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.logging.Level;
import java.util.logging.Logger;

import ase.calculator.Forecast;
import ase.portfolio.OptMaster;
import ase.portfolio.Portfolio;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;

public class SimOpt {
	public static enum SimType {FULL, MARGINAL, SINGLE};	
	
	private static final Logger log = LoggerFactory.getLogger(SimOpt.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final String simdir;
	private final OptMaster opt;
	private final Portfolio portfolio;
	private final Map<Forecast, Portfolio> marginalPortfolios = new HashMap<Forecast, Portfolio>();
	private final Map<Forecast, Portfolio> singlePortfolios = new HashMap<Forecast, Portfolio>();
	private final boolean doMarginals;
	private final boolean doSingles;
	private final ExecutorService threadPool;
	private final Properties config;

	public SimOpt(String simdir, Properties config, boolean doMarginals, boolean doSingles, boolean doMuPortfolios, int threads) throws Exception {
		this.simdir = simdir;
		this.threadPool = Executors.newFixedThreadPool(threads);
		this.config = config;
		this.opt = new OptMaster(config, OptMaster.Mode.SIM);
		this.portfolio = new Portfolio(config);
		this.doMarginals = doMarginals;
		this.doSingles = doSingles;

		this.portfolio.setMuPortfoliosAutoUpdate(doMuPortfolios);

		// set the folder where opt files go
		String scrapDir = simdir + "/scrap";
		if ((new File(this.simdir).exists())) {
			(new File(scrapDir)).mkdirs();
		}
		opt.setScrapDir(scrapDir);

		// check if there is a start of day portfolio and use it
		File sodFile = new File(simdir + "/" + Portfolio.SOD_PORTFOLIO);
		if (sodFile.exists()) {
			this.portfolio.restore(sodFile);
			this.portfolio.setAsOf(this.portfolio.getMostRecentPriceTs());
			this.portfolio.updatePortfolioStats();
			log.info("Restoring SOD portfolio " + sodFile.toString());

			if (doMarginals) {
				for (Forecast f : opt.getForecasts()) {
					Portfolio p = new Portfolio(config);
					p.setMuPortfoliosAutoUpdate(false);
					p.restore(sodFile);
					p.setAsOf(this.portfolio.getMostRecentPriceTs());
					p.updatePortfolioStats();
					p.name = f.name;
					marginalPortfolios.put(f, p);
				}
			}
			
			//XXX Singles always start from an empty portfolio
			if (doSingles) {
				for (Forecast f : opt.getForecasts()) {
					Portfolio p = new Portfolio(config);
					p.setMuPortfoliosAutoUpdate(false);
					p.updatePortfolioStats();
					p.name = f.name;
					singlePortfolios.put(f, p);
				}
			}
		}
		else {
			this.portfolio.updatePortfolioStats();
			
			if (doMarginals) {
				for (Forecast f : opt.getForecasts()) {
					Portfolio p = new Portfolio(config);
					p.setMuPortfoliosAutoUpdate(false);
					p.updatePortfolioStats();
					p.name = f.name;
					marginalPortfolios.put(f, p);
				}
			}
			
			if (doSingles) {
				for (Forecast f : opt.getForecasts()) {
					Portfolio p = new Portfolio(config);
					p.setMuPortfoliosAutoUpdate(false);
					p.updatePortfolioStats();
					p.name = f.name;
					singlePortfolios.put(f, p);
				}
			}
		}
	}

	public void calculate() throws Exception {
		File optlogdir = new File(simdir + "/optlogs");
		optlogdir.mkdir();
		// full portfolio
		HashSet<Callable<Boolean>> tasks = new HashSet<Callable<Boolean>>();
		tasks.add(new SimOptWorker(SimType.FULL, simdir, "FULL", portfolio, new HashSet<Forecast>(), config, LoggerFactory.getIndependentLogger("full", Level.INFO, simdir
				+ "/optlogs/opt.full.log")));
		if (doMarginals) {
			for (Forecast f : this.marginalPortfolios.keySet()) {
				Portfolio p = marginalPortfolios.get(f);
				tasks.add(new SimOptWorker(SimType.MARGINAL, simdir, f.name, p, CollectionUtils.toSet(f), config, LoggerFactory.getIndependentLogger("marginal_"+f.name, Level.INFO, simdir
						+ "/optlogs/opt.marginal." + f.name + ".log")));
			}
		}
		if (doSingles) {
			for (Forecast f : this.singlePortfolios.keySet()) {
				Portfolio p = singlePortfolios.get(f);
				tasks.add(new SimOptWorker(SimType.SINGLE, simdir, f.name, p, CollectionUtils.toSet(f), config, LoggerFactory.getIndependentLogger("single_"+f.name, Level.INFO, simdir
						+ "/optlogs/opt.single." + f.name + ".log")));
			}
		}
		
		boolean allOk = true;
		try {
			List<Future<Boolean>> results = threadPool.invokeAll(tasks);
			threadPool.shutdown();
			log.info("Completed!");

			for (Future<Boolean> result : results) {
				log.info("Task cancelled? " + result.isCancelled() + ". Returned " + result.get());
				allOk &= result.get();
			}
		}
		catch (InterruptedException e) {
			log.severe("Who interrupted my sleep?");
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
				log.severe(e.toString());
			}
			allOk = false;
		}

		if (!allOk) {
			throw new Exception("Some thread threw an exception or the main thread was interrupted! Check the thread logs under optlogs");
		}
	}

	public static void main(String argv[]) {
		String location = null;
		String cfg_file = "opt.cfg";
		int threads = 1;
		String delay = "0";
		boolean doMarginals = false;
		boolean doSingles = false;
		boolean doMuPortfolios = false;
		try {
			for (int i = 0; i < argv.length; i++) {
				if (argv[i].equals("-location"))
					location = argv[++i];
				if (argv[i].equals("-cfg_file"))
					cfg_file = argv[++i];
				if (argv[i].equals("-marginals"))
					doMarginals = true;
				if (argv[i].equals("-singles"))
					doSingles = true;
				if (argv[i].equals("-muportfolios"))
                    doMuPortfolios = true;
				if (argv[i].equals("-threads"))
					threads = Integer.parseInt(argv[++i]);
				if (argv[i].equals("-fill_delay_mins"))
					delay = argv[++i];
			}
		}
		catch (Exception e) {
			log.severe("Invalid arguments:" + e.toString());
			System.exit(1);
		}
		if (location == null) {
			log.severe("Must specify -location");
			System.exit(1);
		}

		Properties config = new Properties();
		try {
			String configfile = location + "/" + cfg_file;
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

		//add delay to config
		config.put("delay", delay);
		
		try {
			SimOpt calc = new SimOpt(location, config, doMarginals, doSingles, doMuPortfolios, threads);
			calc.calculate();
		}
		catch (Exception e) {
			log.severe(e.toString());
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
				log.severe(e.toString());
			}
			System.exit(1);
		}
	}
}
