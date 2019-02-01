package ase.data;

import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.TreeMap;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class FactorLoadings {
    private static final Logger log = LoggerFactory.getLogger(FactorLoadings.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    public static final String FACTOR_PREFIX = "F:";
    public static final String MONITOR_FACTOR_PREFIX = "M:";
    
    private Map<Security, Map<AttrType,NavigableMap<Long,Attribute>>> factorLoadings = new HashMap<Security, Map<AttrType, NavigableMap<Long, Attribute>>>();    
    
    public void init(Security[] secs) {
        for (Security sec : secs) {
            if (! factorLoadings.containsKey(sec)) {
                factorLoadings.put(sec, new HashMap<AttrType, NavigableMap<Long, Attribute>>());
            }
        }
    }
    
    public void reset() {
    	factorLoadings.clear();
    }

    public Set<Security> getSecurities() {
        return factorLoadings.keySet();
    }
    
    public void setFactor(Security sec, AttrType attrType, long asof, double val) {
        Map<AttrType,NavigableMap<Long,Attribute>> attrTypeMap = factorLoadings.get(sec);
        NavigableMap<Long,Attribute> attrHistMap = attrTypeMap.get(attrType);
        if (attrHistMap == null) {
            attrTypeMap.put(attrType, attrHistMap = new TreeMap<Long,Attribute>());
        }
        //make sure lastcalc is correct here...
        attrHistMap.put(asof, new NumericAttribute(attrType, sec, asof, val, asof));
    }

    public double getLoadingAsOf(Security sec, AttrType attr, long asof) {
        NavigableMap<Long,Attribute> factorHist = factorLoadings.get(sec).get(attr);
        if (factorHist == null) {
            return Double.NaN;
        }
        Map.Entry<Long, Attribute> entry = factorHist.floorEntry(asof); 
        if (entry == null || entry.getValue() == null) {
            log.warning("No entry for " + attr.name + " at " + df.debugFormat(asof) + " for " + sec.getSecId() 
                    + ". Hist: " + df.debugFormat(factorHist.firstKey()) + " - " + df.debugFormat(factorHist.lastKey()));
            return Double.NaN;
        }
        return entry.getValue().asDouble();
    }
    
    public void clearOldLoadings(AttrType attr, long oldestAsOfNeeded) {
    	for (Map<AttrType, NavigableMap<Long, Attribute>> secLoadings : factorLoadings.values()) {
    		NavigableMap<Long, Attribute> loadings=secLoadings.get(attr);
    		if (loadings == null) continue;
    		Long oldest=loadings.floorKey(oldestAsOfNeeded);
    		if (oldest == null) continue;
    		while (!loadings.isEmpty()) {
    			Long key=loadings.firstKey();
    			if (key<oldest) 
    				loadings.pollFirstEntry();
    			else
    				break;
    		}
    	}
    }
        
    public void record(CalcResults cr, long asof) {
        for (Map.Entry<Security, Map<AttrType,NavigableMap<Long,Attribute>>> se : factorLoadings.entrySet()) {
            for (Map.Entry<AttrType, NavigableMap<Long,Attribute>> fe : se.getValue().entrySet()) {
                NavigableMap<Long,Attribute> ts = fe.getValue();
                if ( ts != null ) {
                    Map.Entry<Long, Attribute> a = ts.floorEntry(asof);
                    if ( a != null && a.getValue() != null ) {
                        cr.add(se.getKey(), fe.getKey(), a.getKey(), a.getValue().asDouble());
//                        cr.add(a.getValue().sec, a.getValue());
                    }       
                }
            }
        }
    }
}
