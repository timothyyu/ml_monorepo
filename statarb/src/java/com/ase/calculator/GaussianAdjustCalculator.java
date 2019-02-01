package ase.calculator;

import java.util.Collections;
import java.util.Map;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.math.distribution.NormalDistribution;
import org.apache.commons.math.distribution.NormalDistributionImpl;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.LoggerFactory;

public class GaussianAdjustCalculator {
    private static final Logger log = LoggerFactory.getLogger(GaussianAdjustCalculator.class.getName());
    
    public static AttrType calculate(CalcResults cr, AttrType attrname) throws Exception {
        return calculate(cr, attrname, 0.0, 1.0, 5.0);
    }

    public static AttrType calculate(CalcResults cr, AttrType attr, double mean, double sigma, double sigmalimit) throws Exception {
        AttrType resname = getResName(attr);
        Map<Security,Attribute> attrs = cr.getResult(attr);

        int count = attrs.size();
        Vector<Attribute> sortedAttrs = new Vector<Attribute>(attrs.values()); 
        Collections.sort(sortedAttrs, Attribute.getValueComparator());

        NormalDistribution nd = new NormalDistributionImpl(mean, sigma);

        Attribute att;
        int cnt = 0;
        for ( int ii = 0; ii < count-1; ii++ ) {
            att = sortedAttrs.get(ii);
            double adjval = nd.inverseCumulativeProbability((1.0+ii)/count);
            if (adjval < mean-sigmalimit*sigma) adjval = mean - sigmalimit*sigma;
            if (adjval > mean+sigmalimit*sigma) adjval = mean + sigmalimit*sigma;

            // once securities have been adjusted, they shouldn't be decayed
            cr.add(att.sec, resname, att.date, adjval);
            cnt++;
        }
        
        log.info("GaussianAdjustCalculator on " + attr + " affected " + cnt + " / " + attrs.size() );
        return resname;
    }
    
    public static AttrType getResName(AttrType attr) {
        return new CalcAttrType(attr.name + "_GA", attr.datatype);
    }
}
