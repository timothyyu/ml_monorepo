package ase.calculator;

import java.util.Collection;
import java.util.Map;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.Pair;
import ase.util.LoggerFactory;

public class BoundingCalculator {
    public enum Mode { ABS, SIGMA };

    private static final Logger log = LoggerFactory.getLogger(BoundingCalculator.class.getName());

    public final Mode mode;
    
    public BoundingCalculator( Mode mode ) {
        this.mode = mode;
    }
    
    @Deprecated 
    public AttrType calculate(CalcResults cr, AttrType attr, double bound) {
        //should never be centering by zero 
        return calculate(cr, attr, bound, 0.0);
    }
    
    public AttrType calculate(CalcResults cr, AttrType attr, double bound, double center) {
        AttrType resname = getResName(attr, mode);
        Map<Security,Attribute> attrs = cr.getResult(attr);
        if ( attrs == null ) {
            log.severe("can't bound " + attr + ".  it was never calculated.");
            return null;
        }

        double ub = Double.NaN;
        double lb = Double.NaN;
        if (mode == Mode.SIGMA) {
            Pair<Double,Double> meansig = calcMeanSigma( attrs.values() );
            ub = meansig.first + bound * meansig.second;
            lb = meansig.first - bound * meansig.second;
        }
        else if (mode == Mode.ABS) {
            ub = center + bound/10000.0;
            lb = center - bound/10000.0;
        }

        int cnt = 0;
        for( Map.Entry<Security,Attribute> ent : attrs.entrySet() ) {
            double val = ent.getValue().asDouble();
            if( val > ub ) {
                val = ub;
                cnt++;
            } else if ( val < lb ) {
                val = lb;
                cnt++;
            }
            cr.add(ent.getKey(), resname, ent.getValue().date, val);
        }
        log.info("BoundingCalculator on " + attr + " affected " + cnt + " / " + attrs.size() );
        return resname;
    }
        
    public static AttrType getResName(AttrType attr, Mode type) {
        if (type == Mode.ABS) {
            return new CalcAttrType(attr.name + "_B", attr.datatype);
        }
        else {
            return new CalcAttrType(attr.name + "_BS", attr.datatype);
        }
    }

    private static Pair<Double,Double> calcMeanSigma( Collection<Attribute> vals ) {
        double sum = 0;
        double sumsq = 0.0;
        double cnt = vals.size();
        for( Attribute v : vals ) {
            double d = v.asDouble();
            sum += d;
            sumsq += d*d;
        }
        return new Pair<Double,Double>(sum/cnt, Math.sqrt(sumsq/cnt - (sum/cnt)*(sum/cnt)));
    }

    @Deprecated
    public static double boundDouble(double val, double center, int bound) {
        double ub = center + bound/10000.0;
        double lb = center - bound/10000.0;
        if ( val > ub ) val = ub;
        else if ( val < lb ) val = lb;
        return val;
    }
}
