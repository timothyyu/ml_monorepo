package ase.data;

import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.widget.SQLAttributeWidget;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;

public class AttributeSource {
    private static final Logger log = LoggerFactory.getLogger(AttributeSource.class.getName());
    protected static final ASEFormatter df = ASEFormatter.getInstance();
    private final SQLAttributeWidget aw = SQLAttributeWidget.instance();

    public AttributeSource() {
    }

    public Map<Security,Attribute> getAttrAsOf(Set<Security> secs, DbAttrType attr, long asof) throws Exception {
        long oldest = 0L;
        if (attr.max_age > 0) {
            oldest = Math.max(asof-attr.max_age, 0);
        }
        return aw.get(secs, attr, asof, oldest);
    }
    
    public Map<Security, NavigableMap<Long, Attribute>> getRange(Set<Security> secs, DbAttrType attr, long t1, long t2) throws Exception {
        long oldest = 1L;
//        if (attr.max_age > 0) {
//            oldest = Math.max(t1-attr.max_age, oldest);
//        }
        return aw.getRange(secs, attr, t1, t2, oldest);
    }
    
    public Map<Security, Attribute> getUpcoming(Set<Security> secs, DbAttrType attr, long asof) throws Exception {
        return aw.getUpcoming(secs, attr, asof);
    }
    
    public Map<Security, Double> getAverage(Set<Security> secs, DbAttrType attr, long t1, long t2) throws Exception {
        long oldest = 1L;
//        if (attr.max_age > 0) {
//            oldest = Math.max(t1-attr.max_age, oldest);
//        }
        
        Map<Security,Double> res = new HashMap<Security,Double>(secs.size());
        Map<Security, NavigableMap<Long,Attribute>> aMap =  aw.getRange(secs, attr, t1, t2, oldest);
        for (Map.Entry<Security, NavigableMap<Long,Attribute>> secEnt : aMap.entrySet()) {
            double sum = 0.0;
            int cnt = 0;
            for(Attribute a : secEnt.getValue().values()) {
                sum += a.asDouble();
                cnt++;
            }
            res.put(secEnt.getKey(), sum/cnt);
        }
        return res;
    }
    
    public static void main(String[] argv) {
        try {
            AttributeSource attrSource = new AttributeSource();
            Set<Security> secs = CollectionUtils.toSet(new Security(16));
            DbAttrType attrType = new DbAttrType("CAPITALIZATION");
            long asof = df.parse("20091228");
            Map<Security,Attribute> capMap = attrSource.getAttrAsOf(secs, attrType, asof);
            System.out.println(capMap);
        }
        catch( Exception e) {
            log.severe(e.getMessage());
        }
    }
}

