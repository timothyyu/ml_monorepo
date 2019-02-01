package ase.data.widget;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.logging.Logger;

import org.yaml.snakeyaml.Yaml;

import ase.data.ExecPosition;
import ase.data.Quote;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class LiveQuoteWidgetWorker implements Runnable {
    private static final int MAX_ATTEMPTS = 10;
    private static final double MIN_QUOTE_PCT = .90;
	private static final int TIMEOUT_INCREMENT = 300; // in milliseconds
    private static final int SLEEP_TIME = 600; // thread sleeps for so many milliseconds between connection attempts
    protected ExecServerConn execServerConn = null;
    protected final Yaml yaml = new Yaml();
    public Properties config;
    private String host = "";
    private int port = 0;
    protected static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(LiveQuoteWidgetWorker.class.getName());
	public Map<Security, Quote> quoteMap = new HashMap<Security, Quote>();
	private Set<Security> secs = new HashSet<Security>();
	public Map<Security, ExecPosition> positions = new HashMap<Security, ExecPosition>();
	public String identifier = "";
	private boolean interrupted = false;
	
    public LiveQuoteWidgetWorker(Pair<String,Integer> hostPort, Properties config) {
        host = hostPort.first;
        port = hostPort.second.intValue();
        this.config = config;
    }

    private boolean connect() throws InterruptedException {
    	log.info("Entered connect() in LQWWorker (" + host + "," + port + ")");
        int numAttempts = 0;
        String account = config.getProperty("account");
        String password = config.getProperty("password");

        Map<String, String> connectMap = new HashMap<String, String>();
        connectMap.put("message", "connect");
        connectMap.put("account", account);
        connectMap.put("password", password);
        connectMap.put("name", "LiveQuoteWidget from " + System.getenv("HOSTNAME") + " processID = " + LiveQuoteWidget.processID + " identifier = " + LiveQuoteWidget.processIdentifier);
        String connectString = yaml.dump(connectMap) + "---\n";

        /*
         * If we are only interested in getting quotes, then it is more efficient to send a connect message and a status message together. However, in order to
         * keep the implementation clean, we first send a connect message to get the symbols, and then send a status message to obtain quotes.
         * 
         * connectMap = new HashMap<String, String>(); connectMap.put("message", "status"); connectString += yaml.dump(connectMap) + "---\n";
         */

        boolean success = false;
        
        while ((numAttempts < MAX_ATTEMPTS) && (success == false)) {
        	numAttempts += 1;
        	closeConnection();
        	//GV: Remove the following 'if' statement to actually make MAX_ATTEMPTS attempts
        	if (numAttempts > 1) {
        		break;
        	}
            success = true;            
            execServerConn = new ExecServerConn(host, port);
            execServerConn.identifier = identifier;
            if (execServerConn.connect()) {
                log.info("Successfully created connection object for host - " + host + ":" + port);
                execServerConn.write(connectString);
                // Parse server's reply and populate universe
                String connReplyStr = execServerConn.read();
                Map<String, Object> serverMsg = getServerMessage(connReplyStr);
                if (serverMsg == null) {
                    log.severe("Failed to get symbols list from host - " + host + ":" + port);
                    success = false;
                    execServerConn.setTimeoutMillis(execServerConn.getTimeoutMillis() + TIMEOUT_INCREMENT);
                    Thread.sleep(SLEEP_TIME);
                    continue;
                }
                List<String> symbList = (List<String>) serverMsg.get("symbol");
                if (!execServerConn.setUniverse(symbList)) {
                    log.severe("Failed to set symbol list for host - " + host + ":" + port);
                }
            }
            else {
                success = false;
                Thread.sleep(SLEEP_TIME);
                continue;
            }
        }

        if(success == false) {
            log.severe("Failed to connect to " + host + ":" + port + " and/or get status info. Giving up.");
            closeConnection();
        }
        log.info("Leaving connect() in LQWWorker (" + host + "," + port + ")");
        return success;
    }
    
    protected Map<String, Object> getServerMessage(String replyStr) {
        for (Object data : yaml.loadAll(replyStr)) {
            List<Map<String, Object>> singleYamlMsg = (List<Map<String, Object>>) data;
            if (singleYamlMsg == null) {
                continue;
            }
            for (Map<String, Object> singleExecMsg : singleYamlMsg) {
                Object msgType = singleExecMsg.get("message");
                if (msgType == null) {
                    continue;
                }
                if (msgType.toString().equals("server")) {
                    return singleExecMsg;
                }
            }
        }
        return null;
    }

    protected List<Map<String, Object>> getInfoMessages(String replyStr) {
        List<Map<String, Object>> retVal = new ArrayList<Map<String, Object>> (400);
        for (Object data : yaml.loadAll(replyStr)) {
            List<Map<String, Object>> singleYamlMsg = (List<Map<String, Object>>) data;
            if (singleYamlMsg == null) {
                continue;
            }
            for (Map<String, Object> singleExecMsg : singleYamlMsg) {
                Object msgType = singleExecMsg.get("message");
                if (msgType == null) {
                    continue;
                }
                if (msgType.toString().equals("info")) {
                    retVal.add(singleExecMsg);
                }
            }
        }
        return retVal;
    }

    public void setSecurity(Set<Security> secs) {
    	this.secs = secs;
    }
    
    public void closeConnection() {
        if(execServerConn == null) {
            return;
        }
        execServerConn.close();
    }

    private Map<String, Security> getTicker2Sec(Set<Security> secs) throws FileNotFoundException, IOException {
    	String tickerFileName = System.getenv("RUN_DIR") + "/tickers.txt";
    	log.info("Reading tickers file: " + tickerFileName);
    	Map<Integer,String> secID2ticker = new HashMap<Integer, String>(secs.size());
		BufferedReader reader = new BufferedReader(new FileReader(tickerFileName));
		while (reader.ready()) {
			String line = reader.readLine();
			if (line.equals("")) continue;
			String[] fields = line.split("\\|");
            secID2ticker.put(new Integer(fields[1]), fields[0]);
		}
		reader.close();

		Map<String, Security> ticker2sec = new HashMap<String, Security>();
		for(Security sec: secs) {
			String ticker = secID2ticker.get(sec.getSecId());
			if (ticker == null) {
				continue;
			}
			ticker2sec.put(ticker, sec);
		}
		return ticker2sec;
    }
    
    public void getPrices(Set<Security> secs) throws InterruptedException, FileNotFoundException, IOException {
    	log.info("Entered getPrices() in LQWWorker (" + host + "," + port + ")");
    	if(execServerConn != null) {
    		execServerConn.resetTimeout();
    	}
        int numAttempts = 0;
        boolean success = false;
        Map<String, String> messageMap = new HashMap<String, String>();
        messageMap.put("message", "status");
        String messageString = yaml.dump(messageMap) + "---\n";
        Map<String, Security> ticker2sec = getTicker2Sec(secs);
        
        while((numAttempts < MAX_ATTEMPTS) && (success == false)) {
            numAttempts += 1;
            success = true;

            if(!connect()) {
                log.severe("Could not connect to exec servers. (" + host + "," + port + ")");
                success = false;
                continue;
            }

            quoteMap = new HashMap<Security, Quote>(400);
        
            // Get a list of quotes for all symbols housed by an execution server. For each
            // symbol, if it is present in the input secs, add the quote to the quoteMap.
            execServerConn.write(messageString);
            String statusReplyStr = execServerConn.read();
            closeConnection();
            if(statusReplyStr.equals("")) {
            	log.severe("Got empty reply string from " + host + ":" + port);
            	success = false;
            	execServerConn.setTimeoutMillis(execServerConn.getTimeoutMillis() + TIMEOUT_INCREMENT);
                Thread.sleep(SLEEP_TIME);
                continue;
            }
            int totalCount = 0, validCount = 0;
            List<Map<String, Object>> infoMsgs = getInfoMessages(statusReplyStr);
            for (Map<String, Object> singleInfoMsg : infoMsgs) {
                String symbol = singleInfoMsg.get("symbol").toString();
                Security sec = ticker2sec.get(symbol);
                if (sec != null) {
                	totalCount++;
                    Quote qq = parseInfoMsg(singleInfoMsg);
                    if (qq.isValid()) {
                    	validCount++;
                        quoteMap.put(sec, qq);
                    }
                }
            }

            log.info("Valid quotes: " + validCount + " / " + totalCount + " from " + host + ":" + port);
            if(((double)validCount)/((double)totalCount) < MIN_QUOTE_PCT) {
                if (numAttempts < MAX_ATTEMPTS) {
                    log.severe("Did not get enough valid quotes in getPrices() for " + host + ":" + port + ". Retrying to get validQuotes.");
                    success = false;
                    continue;
                }
            }
        }

        if (success == false) {
        	quoteMap = new HashMap<Security, Quote>();
        }

        log.info("Leaving getPrices() in LQWWorker (" + host + "," + port + ")");
    }

    public void getPositions() throws InterruptedException, FileNotFoundException, IOException {
    	log.info("Entered getPositions() in LQWWorker (" + host + "," + port + ")");
    	if(execServerConn != null) {
    		execServerConn.resetTimeout();
    	}
        int numAttempts = 0;
        boolean success = false;
        Map<String, String> messageMap = new HashMap<String, String>();
        messageMap.put("message", "status");
        String messageString = yaml.dump(messageMap) + "---\n";

        Map<String, ExecPosition> ticker2position = new HashMap<String, ExecPosition>(400);
        positions = new HashMap<Security, ExecPosition>(400);

        //GV: For now, only making one successful attempt to get positions
        while((numAttempts < MAX_ATTEMPTS) && (success == false)) {
            numAttempts += 1;
            success = true;

            if(!connect()) {
                log.severe("Could not connect to exec servers. (" + host + "," + port + ")");
                success = false;
                continue;
            }

            execServerConn.write(messageString);
            String statusReplyStr = execServerConn.read();
            closeConnection();
            if(statusReplyStr == "") {
            	log.severe("Got empty reply string from " + host + ":" + port);
            	execServerConn.setTimeoutMillis(execServerConn.getTimeoutMillis() + TIMEOUT_INCREMENT);
                Thread.sleep(SLEEP_TIME);
                success = false;
            	continue;
            }
            for (Map<String, Object> singleInfoMsg : getInfoMessages(statusReplyStr)) {
                String symbol = singleInfoMsg.get("symbol").toString();
                long ts = (long) Math.floor(Double.parseDouble(singleInfoMsg.get("time").toString()) * 1000);
                int position = Integer.parseInt(singleInfoMsg.get("position").toString());
                ExecPosition posObject = new ExecPosition(position, ts);
                ticker2position.put(symbol, posObject);
            }
        }
        
        String tickerFileName = System.getenv("RUN_DIR") + "/tickers.txt";
    	log.info("Reading tickers file: " + tickerFileName);
    	Map<String, Security> ticker2sec = new HashMap<String, Security>();
    	BufferedReader reader = new BufferedReader(new FileReader(tickerFileName));
		while (reader.ready()) {
			String line = reader.readLine();
			if (line.equals("")) continue;
			String[] fields = line.split("\\|");
            ticker2sec.put(fields[0], new Security(Integer.parseInt(fields[1])));
		}
		reader.close();
		
        for (Map.Entry<String, ExecPosition> ee : ticker2position.entrySet()) {
            Security sec = ticker2sec.get(ee.getKey());
            if (sec == null) {
            	if (ee.getKey().equals("SPY")) {
            		continue;
            	}
                log.severe("LiveQuoteWidget.getPositions() failed to map ticker " + ee.getKey() + " to a secid! " + host + ":" + port);
                continue;
            }
            positions.put(sec, ee.getValue());
        }
        log.info("Leaving getPositions() in LQWWorker (" + host + "," + port + ")");
    }

    private Quote parseInfoMsg(Map<String, Object> quoteInfo) {
        double bid = Double.parseDouble(quoteInfo.get("bid").toString());
        double ask = Double.parseDouble(quoteInfo.get("ask").toString());
        long ts = (long) Math.floor(Double.parseDouble(quoteInfo.get("time").toString()) * 1000);
        Quote qq = new Quote(bid, ask, ts);
        return qq;
    }    

    public boolean isInterrupted() {
    	return interrupted;
    }
    
    @Override
    public void run() {
    	if(Thread.currentThread().getName().equals("getPrices")) {    		
    		try {
    			getPrices(secs);
    		}
    		catch (InterruptedException ee) {
    			interrupted = true;
    			closeConnection();
    			log.severe("Was interrupted while trying to get prices in thread " + host + ":" + port);
    			return;
    		}
    		catch (Exception ee) {
    			closeConnection();
    			log.severe("Encountered exception in getPrices.");
    			ee.printStackTrace();
    			return;
    		}
    	}
    	
    	if(Thread.currentThread().getName().equals("getPositions")) {
    		try {
    			getPositions();
    		}
    		catch (InterruptedException ee) {
    			interrupted = true;
    			closeConnection();
    			log.severe("Was interrupted while trying to get positions in thread " + host + ":" + port);
    			return;
    		}
    		catch (Exception ee) {
    			closeConnection();
    			log.severe("Encountered exception in getPrices.");
    			ee.printStackTrace();
    			return;
    		}
    	}
    }

}
