package ase.calculator;

import java.util.Map;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.util.LoggerFactory;

public class TimeCalculator {
    private static final Logger log = LoggerFactory.getLogger(TimeCalculator.class.getName());
    
    public enum Mode { REG, INV, REV };
    
    private final Exchange.Type exch;
    private final Mode mode;
    
    public TimeCalculator(Exchange.Type exch, Mode mode) {
        this.exch = exch;
        this.mode = mode;
    }

    public AttrType calculate(CalcResults cr, AttrType attr, long asof) {
        AttrType resattr = getResName(attr, mode);

        Map<Security,Attribute> attrs = cr.getResult(attr);

        if (attrs == null) {
            log.severe("can't adjust " + attr + " because no attrs found");
            return null;
        }
        int cnt = 0;
        
        double frac = Exchange.fractionOfDayPassed(exch, asof);
        if (frac < 0) {
            log.info("Not Calculating before market open!");
            return null;
        }
        double adj = frac;
        if (mode == Mode.INV) {
            adj = 1.0 - frac;
        } 
        else if (mode == Mode.REV) {
            if ( frac >= 0.5 ) {
                adj = -2.0 + 2.0 * frac;
            }
            else {
                adj = 1.0 - 2.0 * frac; 
            }
        }
        
        assert adj <= 1.0;
        for (Map.Entry<Security,Attribute> ent : attrs.entrySet()) {
            double val = ent.getValue().asDouble() * adj;
            Security sec = ent.getKey();
            
            cr.add(sec, resattr, ent.getValue().date, val);
            cnt++;
        }
        log.info("TimeCalculator on " + attr + " affected " + cnt + " / " + attrs.size() );
        return resattr;
    }
    
    public static AttrType getResName(AttrType attr, Mode mode) {
        return new CalcAttrType(attr.name+"_TAdj-"+mode, attr.datatype);
    }
}
