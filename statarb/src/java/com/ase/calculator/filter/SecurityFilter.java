package ase.calculator.filter;

import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public abstract class SecurityFilter {
    protected static final Logger log = LoggerFactory.getLogger(SecurityFilter.class.getName());
    protected static final ASEFormatter df = ASEFormatter.getInstance();

    public static final AttrType TRADEABLE = new CalcAttrType("TRADEABLE");
    public static final AttrType EXPANDABLE = new CalcAttrType("EXPANDABLE");
    public static final AttrType PRICE_FORECASTABLE = new CalcAttrType("PRICE_FORECASTABLE");
    public static final AttrType FUND_FORECASTABLE = new CalcAttrType("FUND_FORECASTABLE");
    
    public abstract Set<Security> filter( Set<Security> secs, long asof ) throws Exception;
    
    public static Set<Security> calculateFilterAttributes( CalcResults cr, AttrType attrType, Set<Security> secs, long asof ) {
        for (Security sec : secs) {
            cr.add(sec, attrType, asof, 1.0);
        }
        return secs;
    }
}
