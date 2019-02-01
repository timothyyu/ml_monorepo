package ase.data.widget;

import java.io.File;
import java.io.FileReader;
import java.lang.management.ManagementFactory;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.StringTokenizer;
import java.util.logging.Logger;

import ase.data.Exchange;
import ase.data.ExecPosition;
import ase.data.Quote;
import ase.data.Security;
import ase.portfolio.Portfolio;
import ase.timeseries.Bar;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class LiveQuoteWidget {
	public static final Properties execConfig = new Properties();
    public static final int MAX_WAIT_TIME = 10000; // number of milliseconds within which we must return from LiveQuoteWidget
	protected static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(LiveQuoteWidget.class.getName());

	private static LiveQuoteWidget instance;
	public static String processID = "";
	public static String processIdentifier = "";

	public Pair<String,Integer>[] execServers = null;
	private Set<Security> secs = new HashSet<Security>();
	
	public static final LiveQuoteWidget instance() {
		if (instance == null) {
			instance = new LiveQuoteWidget();
		}
		return instance;
	}

	private LiveQuoteWidget() {
		try {
			String execConfigFile = System.getenv("CONFIG_DIR") + "/exec.conf";
			log.fine("Loading: " + execConfigFile);
			execConfig.load(new FileReader(execConfigFile));
			processID = ManagementFactory.getRuntimeMXBean().getName().split("@")[0];
			StringTokenizer strTok = new StringTokenizer(execConfig.getProperty("servers"));
            int numExecServers = strTok.countTokens();
            execServers = new Pair[numExecServers];
    		for (int ii = 0; ii < numExecServers; ii++) {
    		    String hostPort = strTok.nextToken();
    			StringTokenizer hostPortTok = new StringTokenizer(hostPort, ":");
    			String host = hostPortTok.nextToken();
    			Integer port = new Integer(hostPortTok.nextToken());
    			execServers[ii] = new Pair<String,Integer>(host, port);
    		}
		}
		catch (Exception ee) {
			log.severe("Exception encountered while loading exec config file");
			ee.printStackTrace();
			System.exit(1);
		}
	}
	
	// Calling processes can set the identifier to help with debugging on the execution server
	public void setIdentifier(String identifier) {
		processIdentifier = identifier;
	}
	
	private LiveQuoteWidgetWorker[] runThreads(String programName) throws InterruptedException {
		int numExecServers = execServers.length;
        LiveQuoteWidgetWorker[] workers = new LiveQuoteWidgetWorker[numExecServers];
        Thread[] threads = new Thread[numExecServers];
        long startTime = System.currentTimeMillis();

        for(int ii = 0; ii < numExecServers; ii++) {
        	workers[ii] = new LiveQuoteWidgetWorker(execServers[ii], execConfig);
        	workers[ii].identifier = processIdentifier;
        	if (programName == "getPrices") {
        		workers[ii].setSecurity(secs);
        	}
        	threads[ii] = new Thread(workers[ii], programName);
        	threads[ii].start();
        }
        
        // Sleep for a second, before we start polling each worker thread to check whether it has returned
        Thread.sleep(1000);
        
        boolean threadsStopped = false;
        while(!threadsStopped) {
        	threadsStopped = true;
		    for(int ii = 0; ii < numExecServers; ii++) {
		    	if(threads[ii].isAlive()) {
		    		log.info("In LQW: Thread " + ii + " is alive. MS elapsed: " + (System.currentTimeMillis() - startTime));
		    		threadsStopped = false;
		    		if (System.currentTimeMillis() - startTime < MAX_WAIT_TIME) {
		    			Thread.sleep(300);
		    		}
		    		else {
		    			log.info("In LQW: Thread " + ii + " is alive. MS elapsed: " + (System.currentTimeMillis() - startTime));
		    			threads[ii].interrupt();
		    			// Will die very soon now. So we can wait to join
		    			try {
		    				threads[ii].join();
		    			}
		    			catch (InterruptedException ee) {
		    				log.info("Interrupted thread for " + execServers[ii].first + ":" + execServers[ii].second + " since it was taking too long!");
		    			}
		    		}
		    	}
		    }
        }
        for (int ii = 0; ii < numExecServers; ii++) {
    		log.info("In LQW: Thread " + ii + " is stopped. MS elapsed: " + (System.currentTimeMillis() - startTime));
    		workers[ii].closeConnection();
    	}
        log.info("Returning from LiveQuoteWidget in about " + (System.currentTimeMillis() - startTime) + " milliseconds.");
        return workers;
	}

	public Map<Security, Quote> getPrices(Set<Security> secs) throws InterruptedException {
		boolean isInterrupted = false;
		boolean isEmpty = false;
		this.secs = secs;
		LiveQuoteWidgetWorker[] workers = runThreads("getPrices");
		int numExecServers = execServers.length;
        Map<Security, Quote> quoteMap = new HashMap<Security, Quote>(secs.size());
        for(int ii = 0; ii < numExecServers; ii++) {
        	if (workers[ii].isInterrupted()) {
        		isInterrupted = true;
        	}
        	if(workers[ii].quoteMap.size() == 0) {
        		isEmpty = true;
        	}
        	quoteMap.putAll(workers[ii].quoteMap);
        }
        if (isInterrupted || isEmpty) {
        	quoteMap = new HashMap<Security, Quote>();
        	log.severe("Returning 0 quotes, since we were not able to get a reply from at least one exec server.");
        }
        return quoteMap;
	}
	
	public Map<Security, ExecPosition> getPositions() throws InterruptedException {
		boolean isInterrupted = false;
		boolean isEmpty = false;
		LiveQuoteWidgetWorker[] workers = runThreads("getPositions");
		int numExecServers = execServers.length;
        Map<Security, ExecPosition> positions = new HashMap<Security, ExecPosition>(300);
        for(int ii = 0; ii < numExecServers; ii++) {
        	if (workers[ii].isInterrupted()) {
        		isInterrupted = true;
        	}
        	if(workers[ii].positions.size() == 0) {
        		isEmpty = true;
        	}
        	positions.putAll(workers[ii].positions);
        }
        if (isInterrupted || isEmpty) {
        	positions = new HashMap<Security, ExecPosition>();
        	log.severe("Returning 0 positions, since we were not able to get a reply from at least one exec server.");
        }
        return positions;
	}
	
	public Map<Security, Bar> getDayBar(Set<Security> secs, Exchange.Type exch) throws InterruptedException {
        Map<Security, Quote> quotes = getPrices(secs);
        long now = Time.now();
        long open = Exchange.openTime(now, exch);

        Map<Security, Bar> bars = new HashMap<Security, Bar>();
        for (Map.Entry<Security, Quote> qq : quotes.entrySet()) {
            //validity check is probably redundant
            if (qq.getValue().isValid()) {
                bars.put(qq.getKey(), new Bar(qq.getKey(), open, now, Double.NaN, Double.NaN, Double.NaN, qq.getValue().getPrice(), Double.NaN));
            }
        }
        return bars;
    }

	public static void main(String[] argv) throws Exception {
		LiveQuoteWidget lqw = LiveQuoteWidget.instance();
		lqw.setIdentifier("Testing new LQW");
		Portfolio portfolio = new Portfolio();
		portfolio.restore(new File("/apps/ase/run/useq-live/20110308/sodPort.txt"));

		Map<Security, Quote> res1 = lqw.getPrices(portfolio.getSecurities());

		for (Map.Entry<Security, Quote> me : res1.entrySet()) {
			System.out.println(me.getKey() + ":" + me.getValue().getBid() + "," + me.getValue().getAsk() + "," + me.getValue().getTs());
		}
		Map<Security, ExecPosition> res2 = lqw.getPositions();
		for (Map.Entry<Security, ExecPosition> me : res2.entrySet()) {
			System.out.println(me.getKey() + ":" + me.getValue().getPosition() + " at " + me.getValue().getTs());
		}
	}

}
