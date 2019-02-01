package ase.apps;

import java.io.FileReader;
import java.io.Writer;
import java.util.Properties;
import java.util.logging.Level;
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

public class LiveCalc {
    private static final Logger log = LoggerFactory.getLogger(LiveCalc.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    private static final long SLEEP_MILLIS = 1000;
    private static final long MORNING_DELAY = Time.fromMinutes(6);
    
    private final long startdate, enddate, starttime, endtime, stepsize;
    private final String rundir;
    private final CalcMaster calc;
    private final Universe uni;
    private final Exchange.Type primaryExch;

    public LiveCalc(String rundir, Properties config) throws Exception {
        this.rundir = rundir;
        startdate = df.parseShort(config.getProperty("startdate")).getTime();
        enddate = df.parseShort(config.getProperty("enddate")).getTime();
        starttime = Time.fromMinutes(Integer.parseInt(config.getProperty("start_mins_before_close")));
        endtime = Time.fromMinutes(Integer.parseInt(config.getProperty("end_mins_before_close")));
        stepsize = Time.fromMinutes(Integer.parseInt(config.getProperty("stepsize")));
        primaryExch = Exchange.Type.valueOf(config.getProperty("primary_exchange"));
        log.info("beginning calculations, startdate: " + df.format(startdate) + ", enddate: " + df.format(enddate) + ", start_mins_before_close: "
                + Time.toMinutes(starttime) + ", end_mins_before_close: " + Time.toMinutes(endtime) + ", stepsize (mins): " + Time.toMinutes(stepsize));

        uni = new Universe(config, rundir, Time.now());
        log.info("Writing universe file");
        uni.dump(rundir+"/tickers.txt");
        calc = new CalcMaster(config, uni, CalcMaster.Mode.LIVE);
    }

    public void calculate() throws Exception {        
        long now = Time.now();
        long start = Exchange.openTime(now, primaryExch) + MORNING_DELAY;
        long end = Exchange.closeTime(now, primaryExch);
        
        if (Exchange.isHoliday(now, primaryExch) || now > end ) {
            log.info("Exchange closed...");
            return;
        }

        log.info("Calculating initial calcres...");
        CalcResults cr = new CalcResults(0L);
        calc.calculate(now, cr);
        dumpCalcRes(cr);
        
        log.info("Entering live loop...");
        for (long calctime = Math.max(start, now); calctime <= end; calctime += stepsize) {
            log.info("Next calcres at: " + df.format(calctime));
            while ( calctime > Time.now()) {
                try {
                    Thread.sleep(SLEEP_MILLIS);
                }
                catch( InterruptedException ex) {
                    log.severe("Main thread interrupted");
                }
            }            
            
            log.info("Creating calcres file for " + df.format(calctime));
            try {
                cr = calc.calculate(calctime, cr);
            }
            catch( Exception ex ) {
                log.severe("Encountered error in CalcMaster.calculate! ");
                System.exit(1);
            }
            dumpCalcRes(cr);
        }            
        log.info("Exiting LiveCalc normally...");
    }

    private void dumpCalcRes(CalcResults cr) {
        try {
            Pair<String,Writer> ent = FileUtils.openDataDumpFile(rundir + "/calcres", "calcres", cr.getAsOf());
            cr.dump(ent.second);
            ent.second.close();
            FileUtils.finalizeFile(ent.first);
        }
        catch( Exception ex ) {
            log.severe("Could not write calcres file.  Continuing...");
        }        
    }
    
    public static void main(String argv[]) {
        String rundir = null;
        String logfile = null;
        
        try {
            for (int ii = 0; ii < argv.length; ii++) {
                if (argv[ii].equals("-location")) rundir = argv[++ii];
                if (argv[ii].equals("-log")) logfile = argv[++ii];
            }
        }
        catch (Exception e) {
            System.out.println("Invalid arguments:" + e.toString());
            System.exit(1);
        }

        if (logfile != null) {
            LoggerFactory.setLoggerFile(logfile);
            LoggerFactory.setUnsupervisedMode(true);
        }
        Properties config = new Properties();
        try {
            String configfile = rundir +"/calc.cfg";
            log.info("Loading: " + configfile);
            config.load(new FileReader(configfile));
        }
        catch (Exception e) {
            log.log(Level.SEVERE, "Exception countered while loading config file", e);
            e.printStackTrace();
            System.exit(1);
        }

        LiveCalc calc = null;
        try {
            calc = new LiveCalc(rundir, config);
            calc.calculate();
        }
        catch (Exception e) {
            log.log(Level.SEVERE, "Caught Exception in calculate!", e);
			for (StackTraceElement ste : e.getStackTrace()) {
				log.severe(ste.toString());
			}
			e.printStackTrace();
			System.exit(1);
        }
    }
}
