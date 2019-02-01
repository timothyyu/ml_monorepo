package ase.calculator;

import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.calculator.filter.SecurityFilter;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.BarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class ResidualCalculator {
    protected static final Logger log = LoggerFactory.getLogger(Calculator.class.getName());
    protected static final ASEFormatter df = ASEFormatter.getInstance();
    
    public static final CalcAttrType BARRA_RR = new CalcAttrType("barraRR");
    
    public ResidualCalculator() {
        
    }
    
    protected Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        
        for( int lag = -1; lag < 3; lag++) {
            Map<Security, Attribute> brrMap = cr.getResult(FactorCalculator.lattr(FactorCalculator.BARRA_RESIDUAL_RETURN, lag));
            for (Security sec : brrMap.keySet()) {
                Attribute brrAttr = brrMap.get(sec);
                double val = brrAttr.asDouble();
                cr.add(sec, lattr(BARRA_RR, lag), brrAttr.date, val);
            }
        }
        return null;
    }
    
    public static AttrType lattr(AttrType attr, int lag) {
        if (lag == -1) {
            return new CalcAttrType(attr.name + "C");
        }
        return new CalcAttrType(attr.name + lag);
    }
}
