package ase.calculator;

import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public abstract class Calculator {
    protected static final Logger log = LoggerFactory.getLogger(Calculator.class.getName());
    protected static final ASEFormatter df = ASEFormatter.getInstance();
    
    protected long lastcalc = 0L;
    protected final boolean oncePerDay;
    
//    public abstract Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception;
        
    public Calculator() {
        this.oncePerDay = false;
    }
    
    public Calculator(boolean oncePerDay) {
        this.oncePerDay = oncePerDay;
    }
    
    protected boolean needToCalc(long asof) {
        if (oncePerDay && Time.midnight(asof) == Time.midnight(lastcalc)) {
            log.info("Not Calculating " + getClass().getName() + " Waiting until tomorrow");
            return false;
        }
        lastcalc = asof;
        return true;
    }

}
