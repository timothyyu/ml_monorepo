package ase.util;

import gnu.trove.TIntObjectHashMap;
import gnu.trove.TIntObjectIterator;
import gnu.trove.TObjectIntHashMap;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.PosixParser;

import ase.data.widget.AseDBConn;

@Deprecated
public class SecIdBimap {
    public static enum Identifier {
        CUSIP(1), TIC(2), SEDOL(3), ISIN(4), BARRAID(5);
        
        private int type;
        private Identifier(int type) {
            this.type = type;
        }

        public int getType() {
            return type;
        }
    }

    private TIntObjectHashMap<String> fromSecId;
    private TObjectIntHashMap<String> toSecId;
    private Identifier identifier;
    private int type;
    private long date;

    public SecIdBimap(int type, long date) {
        this.type = type;
        this.identifier = null;
        this.date = date;
        this.fromSecId = load();
        this.toSecId = invert(this.fromSecId);
        
        manualFixes();
    }

    public SecIdBimap(Identifier idType, long date) {
        this(idType.getType(), date);
    }

    public String fromSecId(int secId) {
        return fromSecId.get(secId);
    }
    
    public int toSecId(String value) {
        return toSecId.get(value);
    }
    
    private void manualFixes() {
        if (type == 2) {
            fromSecId.remove(330952);
            toSecId.remove("RRD");
            
            fromSecId.put(330952, "RRD");
            toSecId.put("RRD", 330952);
        }
    }

    private TIntObjectHashMap<String> load() {
        TIntObjectHashMap<ArrayList<String>> votes = new TIntObjectHashMap<ArrayList<String>>();
        
        try {
            Connection conn = AseDBConn.getConnection();

            // PreparedStatement statement = conn
            // .prepareStatement("SELECT x.secid,x.value "
            // + "FROM xref as x, stock as s "
            // +
            // "WHERE x.source>=2 AND x.xref_type=? AND x.born<=? AND (x.died>=? OR x.died IS NULL) AND x.secid=s.secid and s.country=1 "
            // + "ORDER BY x.secid ASC,x.source ASC,x.born DESC");
            PreparedStatement statement = conn
                .prepareStatement("SELECT x.secid,x.value "
                                  + "FROM xref as x, stock as s "
                                  + "WHERE (x.source=2 OR x.source=13) AND x.xref_type=? AND x.born<=? AND (x.died>=? OR x.died IS NULL) AND x.secid=s.secid and s.country=1 "
                                  + "ORDER BY x.secid ASC,x.source ASC,x.born DESC");
            statement.setFetchDirection(ResultSet.FETCH_FORWARD);
            statement.setFetchSize(10000);
            statement.setInt(1, this.type);
            statement.setLong(2, this.date);
            statement.setLong(3, this.date);
            
            ResultSet rs = statement.executeQuery();
            while (rs.next()) {
                int secId = rs.getInt(1);
                String value = rs.getString(2);
                
                ArrayList<String> arr = votes.get(secId);
                if (arr == null) {
                    arr = new ArrayList<String>();
                    votes.put(secId, arr);
                }
                arr.add(value);
            }

            AseDBConn.closeConnection();
        } 
        catch (Exception e) {
            e.printStackTrace();
        }

        // Vote and return
        return singleOutValue(votes);
    }

    private static TIntObjectHashMap<String> singleOutValue(TIntObjectHashMap<ArrayList<String>> votes) {
        TIntObjectIterator<ArrayList<String>> it = votes.iterator();
        TIntObjectHashMap<String> from = new TIntObjectHashMap<String>();
        
        while (it.hasNext()) {
            it.advance();
            from.put(it.key(), firstOneVote(it.value()));
        }
        from.compact();
        return from;
    }

    private static String firstOneVote(ArrayList<String> secVotes) {
        return secVotes.get(0);
    }
    
    private static String majorityVote(ArrayList<String> secVotes) {
        if (secVotes.size() == 0) {
            return null;
        }
        
        Collections.sort(secVotes);
        
        String best = secVotes.get(0);
        int bestCount = 1;
        String previous = best;
        String current = null;
        int countSoFar = 0;
        
        for (String v : secVotes) {
            current = v;
            
            if (current.equals(previous)) {
                countSoFar++;
            } 
            else {
                if (countSoFar > bestCount) {
                    bestCount = countSoFar;
                    best = previous;
                }
                countSoFar = 1;
            }
            previous = current;
        }
        if (countSoFar > bestCount) {
            best = current;
        }
        return best;
    }

    private static TObjectIntHashMap<String> invert(TIntObjectHashMap<String> from) {
        TIntObjectIterator<String> it = from.iterator();
        TObjectIntHashMap<String> to = new TObjectIntHashMap<String>();
        
        while (it.hasNext()) {
            it.advance();
            to.put(it.value(), it.key());
        }
        to.compact();
        return to;
    }

    public String asPythonString() {
        StringBuilder sb = new StringBuilder();
        TIntObjectIterator<String> it = fromSecId.iterator();
        
        boolean empty = true;
        sb.append("{\n");
        while (it.hasNext()) {
            empty = false;
            it.advance();
            
            // sb.append("\"");
            sb.append(it.key());
            // sb.append("\"");
            sb.append(" : ");
            sb.append("\"");
            sb.append(it.value());
            sb.append("\"");
            sb.append(",\n");
        }
        if (!empty) {
            sb.delete(sb.length() - 2, sb.length());
        }
        sb.append("\n}");
        return sb.toString();
    }

    private static void tests1() {
        ArrayList<String> votes = new ArrayList<String>();
        System.out.println(majorityVote(votes));
    }
    
    private static void tests2() {
        SecIdBimap map = new SecIdBimap(Identifier.TIC, Time.now());
        
        System.out.println(map.toSecId("ADCT"));
        System.out.println(map.fromSecId(327639));
    }
    
    public static void main(String[] args) {
        CommandLineParser parser = new PosixParser();
        
        Options options = new Options();
        options.addOption(new Option("t", "type", true, "External identifier type"));
        options.addOption(new Option("d", "date", true, "As of date"));
        options.addOption(new Option("ts", "timestamp", true, "As of timestamp"));
        options.addOption(new Option("now", "now", false, "As of now"));
        options.addOption(new Option("f", "format", true, "Output format"));
        
        int type = 0;
        long date = 0;
        String format = null;
        
        try {
            CommandLine line = parser.parse(options, args);
            String value;
            
            value = line.getOptionValue("t");
            type = (value == null ? 0 : Integer.parseInt(value));
            
            if (line.hasOption("d")) {
                value = line.getOptionValue("d");
                date = (value == null ? 0 : ASEFormatter.getInstance().parse(value));
            }
            if (line.hasOption("ts")) {
                value = line.getOptionValue("ts");
                date = (value == null ? 0 : Long.parseLong(value));
            }
            if (line.hasOption("now")) {
                date = Time.now();
            }
            
            format = line.getOptionValue("f");
        } 
        catch (Exception e) {
            e.printStackTrace();
            System.exit(1);
        }

        // Set of valid format types
        HashSet<String> validFormats = new HashSet<String>();
        validFormats.add("python");
        
        if (type == 0 || date == 0 || !validFormats.contains(format)) {
            System.err.println("Bad arguments");
            System.exit(1);
        }
        
        SecIdBimap map = new SecIdBimap(type, date);
        if (format.equals("python")) {
            System.out.println(map.asPythonString());
        }
    }
}
