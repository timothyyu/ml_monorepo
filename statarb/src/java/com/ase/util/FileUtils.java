package ase.util;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.util.Arrays;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

public class FileUtils {
    private static final Logger log = LoggerFactory.getLogger(FileUtils.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    public static final Pattern CALCRES_PATTERN = Pattern.compile(".*calcres\\.([0-9_]+)\\.txt\\.gz$");
    public static final Pattern INTRADAY_CALCRES_PATTERN = Pattern.compile(".*calcres_intraday\\.([0-9_]+)\\.txt\\.gz$");
    public static final Pattern FILLS_PATTERN = Pattern.compile(".*fills\\.([0-9_]+)\\.txt$");
    public static final Pattern POS_PATTERN = Pattern.compile(".*pos\\.([0-9_]+)\\.txt$");
    public static final Pattern MUS_PATTERN = Pattern.compile(".*mus\\.([0-9_]+)\\.txt$");
    public static final Pattern ORDERS_PATTERN = Pattern.compile(".*orders\\.([0-9_]+)\\.txt$");
    public static final Pattern STATS_PATTERN = Pattern.compile(".*stats\\.(.+)\\.txt$");
    public static final Pattern UNI_PATTERN = Pattern.compile(".*uni\\.(.+)\\.txt$");

    public static Writer makeWriter(String filename) throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new FileOutputStream(filename)));
    }
    
    public static Writer makeWriter(File file) throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file)));
    }
    
    public static String dataDumpFileName( String dir, String name, long date ) {
        ASEFormatter df = ASEFormatter.getInstance();
        String dateinfo = "";
        if ( date != 0 ) 
            dateinfo = "." + df.formatMins(date);
        String filename = dir + "/" + name + dateinfo + ".txt";
        return filename;
    }
    
    public static String finalizeFile(String filename) throws IOException {
        File from = new File(filename);
        int idx = filename.indexOf(".IN_PROCESS");
        if (idx > 0) {
            String newname = filename.substring(0, idx);
            from.renameTo(new File(newname));
            return newname;
        }
        else {
            return filename;
        }
    }
    
    public static Pair<String,Writer> openDataDumpFile( String dir, String name, long date, boolean compress ) throws IOException {
        (new File(dir)).mkdir();
        String filename = dataDumpFileName(dir, name, date);
        Writer ret = null;
        if (compress) {
            filename += ".gz.IN_PROCESS";
            ret = new BufferedWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(filename))));
        }
        else {
            filename += ".IN_PROCESS";
            ret = makeWriter(filename);
        }
        return new Pair<String,Writer>(filename,ret);
    }
    
    public static Pair<String,Writer> openDataDumpFile( String dir, String name, long date ) throws IOException {
        return openDataDumpFile(dir, name, date, true);
    }

    public static Pair<String,Writer> openDataDumpFile( String dir, String name ) throws IOException {
        return openDataDumpFile(dir, name, System.currentTimeMillis());
    }

    public static BufferedReader openZipReader(String filename) throws IOException {
        return new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(filename))));
    }
    public static BufferedReader openZipReader(File file) throws IOException {
        return new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(file))));
    }
    
    public static BufferedReader openFileReader(String filename) throws IOException {
        return new BufferedReader(new FileReader(filename));
    }
    
    public static BufferedReader openFileReader(File file) throws IOException {
        return new BufferedReader(new FileReader(file));
    }
    
    public static NavigableMap<Long,File> getDumpedFiles(String dir, Pattern pattern) throws Exception {
        File folder = new File(dir);
        if (!folder.exists()) {
            throw new RuntimeException("Directory " + dir + " does not exist!");
        }
        File[] files = folder.listFiles();
        Arrays.sort(files);
        NavigableMap<Long,File> res = new TreeMap<Long,File>();
        if (files == null || files.length == 0) {
            log.severe("Could not find files in " + dir);
            return null;
        }
        for(int ii=0; ii<files.length; ii++) {
            long datetime = getFileTs(files[ii].toString(), pattern);
            if (datetime > 0) {
                res.put(datetime,files[ii]);
            }
        }
        return res;
    }
    
    public static long getFileTs(String filename, Pattern pattern) throws Exception {
        Matcher matcher = pattern.matcher(filename);
        long res = -1;
        if (matcher.matches()) {
            try {
                res = df.parseMins(matcher.group(1)).getTime();
            }
            catch (Exception e) {
                res = df.parseShort(matcher.group(1)).getTime();
            }
        }
        return res;
    }
}

