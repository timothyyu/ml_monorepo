package ase.apps;

import java.io.FileReader;
import java.io.Writer;
import java.util.Properties;
import java.util.logging.Logger;

import ase.calculator.CalcMaster;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Universe;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class SimCalc {
    private static final Logger log = LoggerFactory.getLogger(SimCalc.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    public static long COMPUSTAT_START_DATE = df.parse("20080901");
    
    private final long startdate, enddate, starttime, endtime, stepsize;
    private final String location;

    private final CalcMaster calc;
    private final Universe uni;

    public SimCalc(String location, Properties config) throws Exception {
        this.location = location;
        startdate = df.parseShort(config.getProperty("startdate")).getTime();
        enddate = df.parseShort(config.getProperty("enddate")).getTime();
        starttime = Time.fromMinutes(Integer.parseInt(config.getProperty("start_mins_before_close")));
        endtime = Time.fromMinutes(Integer.parseInt(config.getProperty("end_mins_before_close")));
        stepsize = Time.fromMinutes(Integer.parseInt(config.getProperty("stepsize")));
        log.info("beginning calculations, startdate: " + df.format(startdate) + ", enddate: " + df.format(enddate) + ", start_mins_before_close: " + Time.toMinutes(starttime) 
                 + ", end_mins_before_close: " + Time.toMinutes(endtime) + ", stepsize (mins): " + Time.toMinutes(stepsize));

        uni = new Universe(config, location, startdate);
        if ( !uni.fromFile()) {      	
            String unifile = location + "/uni." + df.format(uni.getUniDate()) + ".txt";
            log.info("Dumping universe file to " + unifile);
            uni.dump(unifile);
        }
        
        if ( uni.getUniDate() > startdate - Time.fromDays(90)) {
            log.severe("Universe date of " + df.format(uni.getUniDate()) + " too late for simulation!");
        }
        
        calc = new CalcMaster(config, uni, CalcMaster.Mode.SIM);
    }

    public void calculate() throws Exception {
        for (long adate = startdate; adate <= enddate; adate += Time.fromDays(1)) {
        	long startcalc = Exchange.closeTime(adate, uni.primaryExch) - (starttime - Exchange.earlyCloseDiff(adate, uni.primaryExch));
            long endcalc = Exchange.closeTime(adate, uni.primaryExch) - endtime;
            CalcResults lastresults = new CalcResults(0L);
            for (long calcdate = startcalc; calcdate <= endcalc; calcdate += stepsize) {
                if ( !Exchange.isOpen(calcdate, uni.primaryExch) ) { 
                    continue;
                }
                log.info("performing calculations for: " + df.format(calcdate));
                CalcResults results = calc.calculate(calcdate, lastresults);
                
                log.info("writing daily 4cast summary");
                Pair<String,Writer> resfile = FileUtils.openDataDumpFile(location+"/calcres", "calcres", calcdate);
                Writer writer = resfile.second;
                results.dump(writer);
                writer.close();
                FileUtils.finalizeFile(resfile.first);
                lastresults = results;
            }
        }
        log.info("calculations for sim complete");
    }

    public static void main(String argv[]) {
        String location = null;
        String cfg_file = "calc.cfg";
        
        try {
            for (int i = 0; i < argv.length; i++) {
                if ( argv[i].equals("-location") )
                    location = argv[++i];
                if ( argv[i].equals("-cfg_file") )
                    cfg_file = argv[++i];
            }
        }
        catch ( Exception e ) {
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
            e.printStackTrace();
            System.exit(1);
        }

        try {
            SimCalc calc = new SimCalc(location, config);
            calc.calculate();
        } 
        catch (Exception e) {
			log.severe("Exception encountered in SimCalc during calculation");
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
			}
			e.printStackTrace();
			System.exit(1);
        }
    }
}
