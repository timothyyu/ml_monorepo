package ase.data;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.mail.EmailException;

import ase.apps.SimCalc;
import ase.calculator.PassThruCalculator;
import ase.calculator.filter.RankingFilter;
import ase.calculator.filter.SecurityFilter;
import ase.calculator.filter.SecurityStringAttrFilter;
import ase.data.widget.SQLSecurityWidget;
import ase.portfolio.Portfolio;
import ase.util.ASEFormatter;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Time;
import ase.util.math.ASEMath;

public class Universe {
	private static final Logger log = LoggerFactory.getLogger(Universe.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static final String TICKER_FILE = "tickers.txt";
	
	private SQLSecurityWidget secWidget = SQLSecurityWidget.instance();
	
	public final Set<Security> secs;
	public final Exchange.Type primaryExch;
	private boolean fromFile;
	private long uniDate;
	private long asof;

	public Universe(Exchange.Type primaryExch) {
		secs = new HashSet<Security>(2000);
		this.primaryExch = primaryExch;
	}

    public Universe(Properties config, String rundir, long asof) throws Exception {
        Set<Security> stocks;
        
        String unifile = config.getProperty("unifile");
        String oldUnifile = config.getProperty("old_unifile");
        String uniDateStr = config.getProperty("uni_date");
        primaryExch = Exchange.Type.valueOf(config.getProperty("primary_exchange"));                
        this.asof = asof;
        
        if (unifile != null) {
            stocks = loadFromFile(unifile);
            stocks.addAll(loadFromPortfolio(rundir+"/"+Portfolio.SOD_PORTFOLIO));
            fromFile = true;
            uniDate = FileUtils.getFileTs(unifile, FileUtils.UNI_PATTERN);
        }
        else if (oldUnifile != null) {
            stocks = loadFromOldFile(oldUnifile);
            stocks.addAll(loadFromPortfolio(rundir+"/"+Portfolio.SOD_PORTFOLIO));
            fromFile = true;
            uniDate = FileUtils.getFileTs(oldUnifile, FileUtils.UNI_PATTERN); 
        }
        else if (uniDateStr != null) {
        	uniDate = df.parseShort(uniDateStr).getTime();
            Country country = Country.valueOf(config.getProperty("countries"));
            Currency currency = Currency.valueOf(config.getProperty("currencies"));
            double lp = Double.parseDouble(config.getProperty("low_price"));
            double hp = Double.parseDouble(config.getProperty("high_price"));
            double advp = Double.parseDouble(config.getProperty("min_advp"));
            int adv_days = Integer.parseInt(config.getProperty("univ_adv_days"));
            int size = Integer.parseInt(config.getProperty("size"));
            log.info("Generating universe for date: " + df.format(uniDate) + " size: " + size + " advp: " + advp + " adv_days: " + adv_days);

            stocks = secWidget.getStocksAsOf(country, currency, hp, lp, advp, uniDate, adv_days);

            AttributeSource attrSource = new AttributeSource();

            // only grab common stocks
            SecurityFilter spf = new SecurityStringAttrFilter(PassThruCalculator.SECTYPE, "0", true, attrSource);
            // dangerous, but we don't have historical sectype attributes... also a bit of a fudget on the date
            stocks = spf.filter(stocks, Math.max(SimCalc.COMPUSTAT_START_DATE + Time.fromDays(30), uniDate));

            SecurityFilter capf = new RankingFilter(attrSource, PassThruCalculator.CAP, RankingFilter.Type.HIGH, size);
            stocks = capf.filter(stocks, uniDate);
            
            if (stocks.size() == 0) throw new RuntimeException("No stocks in universe!!");
            fromFile = false;
            asof = uniDate;
        }
        else {
            this.uniDate = asof;
            //XXX I don't like this...
            stocks = loadFromFile(rundir+"/"+TICKER_FILE);
        }
        secs = new HashSet<Security>(stocks.size());
        log.info("Universe size: " + stocks.size());
        secs.addAll(secWidget.loadStocks(stocks, asof));
	}

    @Deprecated
	public Universe(String filename, Exchange.Type primaryExch, boolean oldformat, long asof) throws Exception {
		secs = new HashSet<Security>();
		if (oldformat) {
		    secs.addAll(loadFromOldFile(filename));
		}
		else {
		    secs.addAll(Universe.loadFromFile(filename));
		}
		fromFile = true;
		this.primaryExch = primaryExch;
		this.asof = asof;
	}

	public long getAsof() {
		return asof;
	}
	
	public long getUniDate() {
		return this.uniDate;
	}
	
	public boolean fromFile() {
		return fromFile;
	}
	
	public Set<Security> getLivingUniverse() {
	    Set<Security> res = new HashSet<Security>(secs.size());
	    for (Security sec : secs) {
	        if ( sec.isAlive() ) res.add(sec);
	    }
	    return res;
	}

	public Set<Security> loadFromPortfolio(String filename) throws Exception{
		log.info("reading universe from portfolio "+filename);
		Set<Security> res = new HashSet<Security>();
		File file = new File(filename);
		if (!file.exists() || !file.isFile()) {
		    if ( Time.today(asof) == Time.today(Time.now()) ) {
			    log.severe("Could not find SOD portfolio for universe.");
		    }
			return res;
		}
		Portfolio portfolio = new Portfolio();
		portfolio.restore(file);
		res.addAll(portfolio.getSecurities());
		return res;
	}

	public static Set<Security> loadFromTickersFile(String filename) throws Exception {
		log.info("reading tickers file " + filename);
		Set<Security> secs = new HashSet<Security>();
		BufferedReader reader = new BufferedReader(new FileReader(filename));
		while (reader.ready()) {
			String line = reader.readLine();
			if (line.equals("")) continue;
			String[] fields = line.split("\\|");

			String secType = fields[2];
			Security sec;
			if (secType.equals("STOCK")) {
				Stock stock = new Stock(Integer.parseInt(fields[1]), Integer.parseInt(fields[3]), 
						fields[4], Exchange.Type.valueOf(fields[7]), Country.valueOf(fields[5]), Currency.valueOf(fields[6]), 
						fields[8].equals("A"));
				sec = (Security) stock;
			} 
			else {
				throw new Exception("Unknown Security Type: [" + line + "]");
			}
			secs.add(sec);
		}
		reader.close();
		return secs;
	}	
	
	public static Set<Security> loadFromFile(String filename) throws Exception {
		log.info("reading universe file " + filename);
		Set<Security> secs = new HashSet<Security>();
		BufferedReader reader = new BufferedReader(new FileReader(filename));
		while (reader.ready()) {
			String line = reader.readLine();
			if (line.equals("")) continue;
			String[] fields = line.split("\\|");

			Security.Type sectype = Security.Type.valueOf(fields[1]);
			Security sec;
			if (sectype == Security.Type.STOCK) {
				sec = (Security) Stock.restore(fields);
			} 
			else {
				throw new Exception("Unknown Security Type: [" + line + "]");
			}
			secs.add(sec);
		}
		reader.close();
		return secs;
	}

	@Deprecated
	public Set<Security> loadFromOldFile(String filename) throws Exception {
		log.info("reading old system universe file " + filename);

		File file = new File(filename);
		if (!file.exists() || !file.isFile()) {
			throw new Exception("Couldn't find old system universe file");
		}
		// get the date of the file
		String[] tokens = file.getName().split("\\.");
		long date = Time.now();
		try {
			date = df.parse(tokens[1]);
		} 
		catch (RuntimeException e) {
			log.warning("File not like uni.txt.YYYYMMDD, using time now...");
		}

		Set<String> cusips = new HashSet<String>();
		BufferedReader reader = new BufferedReader(new FileReader(filename));
		while (reader.ready()) {
            String line = reader.readLine();
            String[] fields = line.split("\\|");
            cusips.add(fields[3]);
		}
		reader.close();
		
		Set<Security> secSet = new HashSet<Security>();
		for (Security sec : secWidget.getStocksFromXref(cusips, XRef.CUSIP, date).values()) {
			if (sec!=null) secSet.add(sec);
		}
		log.info("Loaded " + secSet.size() + " / " + cusips.size() + " securities");
        return secSet;
	}

	public void dump(String filename) throws Exception {
	    Map<Security,String> tickerMap = secWidget.getXrefMap(secs, asof, XRef.TIC);
	    checkTickerConflicts(tickerMap);
	    
		FileWriter fw = new FileWriter(filename);
		for (Security sec : secs) {
		    String ticker = tickerMap.get(sec);
		    if (ticker == null) {
		        log.severe("Could not look up ticker for " + sec.getSecId());
		        ticker = "";		    
		    }
			fw.write(ticker + "|" + (Stock)sec + "\n");
		}
		fw.close();
	}	
	
	public void checkTickerConflicts(Map<Security,String> tickerMap) throws EmailException {
	    //Check if mapping is 1-to-1
	    Map<String, Vector<Security>> checkMap = new HashMap<String, Vector<Security>>();
	    for (Map.Entry<Security, String> e : tickerMap.entrySet()) {
	    	Security sec = e.getKey();
	    	String ticker = e.getValue();
	    	
	    	Vector<Security> tickerSecs = checkMap.get(ticker);
	    	if (tickerSecs == null) 
	    		checkMap.put(ticker, tickerSecs = new Vector<Security>());
	    	tickerSecs.add(sec);
	    }
	    
	    boolean postMessage = false;
	    StringBuilder sb = new StringBuilder();
	    for (Map.Entry<String, Vector<Security>> e : checkMap.entrySet()) {
	    	String ticker = e.getKey();
	    	Vector<Security> secs = e.getValue();
	    	if (secs.size() == 1)
	    		continue;
	    	
	    	postMessage = true;
	    	sb.append(secs.size());
	    	sb.append(" secids share ticker ");
	    	sb.append(ticker);
	    	sb.append(":");
	    	for (Security sec : secs)
	    		sb.append(" "+sec.getSecId());
	    	sb.append("\n");
	    }
	    
	    if (postMessage) {
	    	log.severe(sb.toString());
	    	Email.email("[ERROR] Ticker conflicts!", sb.toString());
	    }
	}
	
    public void checkUniverseSize(Set<Security> secs) {
        if (secs.size() < size() * 0.25) {
            log.severe("Filtered universe is too small: " + secs.size());
            throw new RuntimeException();
        }
    }

	public int size() {
		return secs.size();
	}

	public void add(Security sec) {
		if (!secs.add(sec)) {
			log.severe("security " + sec + " already existed in this universe.");
		}
	}

	public String toString() {
		String str = "";

		for (Security sec : secs) {
			str += sec + "\n";
		}
		return str;
	}

	public static void main(String[] argv) {
		try {		    
			Properties config = new Properties();
			config.load(new FileReader(argv[0]));
			Universe u = new Universe(config, null, 0L);
			System.out.println(u);
		} 
		catch (Exception e) {
			e.printStackTrace();
		}
	}

}
