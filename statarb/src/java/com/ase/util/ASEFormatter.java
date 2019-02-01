package ase.util;

import java.text.DecimalFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;

public class ASEFormatter {
    private static ASEFormatter format;
    private final SimpleDateFormat dfLong;
    private final SimpleDateFormat dfMins;
    private final SimpleDateFormat dfShort;
    private final SimpleDateFormat dfDir;
    private final SimpleDateFormat dfHuman;
    private final SimpleDateFormat dfHumanShort;
    
    private final DecimalFormat ffDollars;
    private final DecimalFormat decayFormat;

    private ASEFormatter () {
        dfLong = new SimpleDateFormat("yyyyMMdd_HHmmss.SSS");
        dfLong.setTimeZone(Time.tz);
        dfMins = new SimpleDateFormat("yyyyMMdd_HHmm");
        dfMins.setTimeZone(Time.tz);
        dfShort = new SimpleDateFormat("yyyyMMdd");
        dfShort.setTimeZone(Time.tz);
        dfDir = new SimpleDateFormat("yyyy/MM/dd");
        dfDir.setTimeZone(Time.tz);
        dfHuman = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
        dfHuman.setTimeZone(Time.tz);
        dfHumanShort = new SimpleDateFormat("yyyyMMdd HH:mm:ss");
        dfHumanShort.setTimeZone(Time.tz);
        
        decayFormat = new DecimalFormat("0.0");
        ffDollars = new DecimalFormat("0.000");
    }

    synchronized public static ASEFormatter getInstance() {
        if (format == null) {
            format = new ASEFormatter();
        }
        return format;
    }

    synchronized public String format(Object millis) {
        return dfLong.format(millis);
    }
    
    synchronized public String dformat(Object date) {
        return dfShort.format(date);
    }
    
    synchronized public String debugFormat(Long date) {
        return "" + date + " (" + format(date) + ")"; 
    }
    
    synchronized public String fformat(Double d) {
        if (Double.isNaN(d)) return "NaN";
        else if (d==0) return "0";
        else return ffDollars.format(d);
    }
    
    synchronized public String toYYYYMMDD(long date) {
        return dfShort.format(new Date(date));
    }
    
    synchronized public long fromYYYYMMDD(String date) throws Exception {
        return dfShort.parse(date).getTime();
    }
    
    synchronized public String formatLong(Object millis) {
    	return dfLong.format(millis);
    }
    synchronized public Date parseLong(String date) throws ParseException {
    	return dfLong.parse(date);
    }
    
    synchronized public String formatShort(Object millis) {
    	return dfShort.format(millis);
    }
    synchronized public Date parseShort(String date) throws ParseException {
    	return dfShort.parse(date);
    }
    
    synchronized public String formatMins(Object millis) {
    	return dfMins.format(millis);
    }
    synchronized public Date parseMins(String date) throws ParseException {
    	return dfMins.parse(date);
    }
    
    synchronized public String formatHuman(Object millis) {
    	return dfHuman.format(millis);
    }
    synchronized public Date parseHuman(String date) throws ParseException {
    	return dfHuman.parse(date);
    }
    
    synchronized public String formatHumanShort(Object millis) {
    	return dfHumanShort.format(millis);
    }
    synchronized public Date parseHumanShort(String date) throws ParseException {
    	return dfHumanShort.parse(date);
    }
    
    synchronized public String formatDir(Object millis) {
    	return dfDir.format(millis);
    }
    synchronized public Date parseDir(String date) throws ParseException {
    	return dfDir.parse(date);
    }
    
    synchronized public String formatDecay(Object millis) {
    	return decayFormat.format(millis);
    }
    synchronized public Number parseDecay(String date) throws ParseException {
    	return decayFormat.parse(date);
    }
    
    synchronized public String formatDollars(Object millis) {
    	return ffDollars.format(millis);
    }
    synchronized public Number parseDollars(String date) throws ParseException {
    	return ffDollars.parse(date);
    }

    @Deprecated
    synchronized public long parse(String str) {
        Date d;
        try {
            d = dfMins.parse(str);
        } 
        catch ( Exception e ) {
            try {
                d = dfShort.parse(str);
            }
            catch ( Exception e2 ) {
                throw new RuntimeException("Couldn't parse date: " + str);
            }
        }
        return d.getTime();
    }
    
    public static void main(String[] argv) throws Exception {
        System.out.println(getInstance().dfShort.parse(argv[0]).getTime());
    }
}
