package ase.calculator;

import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;
import ase.util.math.ASEMath;

public class NewsCalculator {
    private static final Logger log = LoggerFactory.getLogger(NewsCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();    
    
    private static final DbAttrType RNEWS_TOT = new DbAttrType("RNEWS_TOTAL", "RNEWS_TOTAL", Time.fromDays(30), Time.fromMinutes(5));
    public static final CalcAttrType newsAttr = new CalcAttrType("rnews");
    public static final long MAX_NEWS_DECAY_TIME = Time.fromDays(10);
    
    private final UnifiedDataSource uSource; 
    
    public NewsCalculator(UnifiedDataSource uSource) {
        this.uSource = uSource;
    } 
    
    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        Map<Security, NavigableMap<Long,Attribute>> attrMap = uSource.attrSource.getRange(secs, RNEWS_TOT, asof - MAX_NEWS_DECAY_TIME, asof); 
        for (Map.Entry<Security, NavigableMap<Long, Attribute>> ent : attrMap.entrySet()) {
            NavigableMap<Long, Attribute> newsMap = ent.getValue();
            if (newsMap.size() < 1) continue;
            long latest = ent.getValue().lastKey();
            
            Map<Long, Vector<Double>> dayAvgs = new HashMap<Long,Vector<Double>>();
            
            for ( Attribute attr : ent.getValue().values()) {
                Vector<Double> items = dayAvgs.get(Time.midnight(attr.born));
                if (items == null) {
                    items = new Vector<Double>();
                    dayAvgs.put(Time.midnight(attr.born), items);
                }
                items.add(attr.asDouble());
            }
            Vector<Double> latestRes = dayAvgs.get(Time.midnight(latest));
            if (latestRes != null) {
                cr.add(ent.getKey(), newsAttr, latest, ASEMath.mean(latestRes));
            }
        } 
        DecayCalculator.calculate(cr, RNEWS_TOT, asof, Time.fromDays(1), 3);
        return null;
    }
}

