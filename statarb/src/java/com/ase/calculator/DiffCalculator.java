package ase.calculator;

import java.util.Map;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class DiffCalculator {
    private static final Logger log = LoggerFactory.getLogger(DiffCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
        
    private static final double EPSILON = 0.00001;
    
    public DiffCalculator() {
    }
    
    public static AttrType calculate(CalcResults cr, AttrType attrType, long asof, long maxdiff) {
        AttrType res = getResName(attrType);
        Map<Security, Vector<Attribute>> secMap = cr.getResultHist(attrType);
        for (Map.Entry<Security, Vector<Attribute>> ent : secMap.entrySet()) {
            Security sec = ent.getKey();
            Vector<Attribute> attrs = ent.getValue();
            int sz = attrs.size();
            if ( sz < 2 ) continue;
            Attribute attr2 = attrs.get(sz - 1);
            Attribute attr1 = attrs.get(sz - 2);
            if ( (attr2.date - attr1.date) > maxdiff ) continue;
            
            double diff = attr2.asDouble() - attr1.asDouble();
            if (diff < EPSILON) continue; 
            cr.add(sec, res, attr2.date, Math.log(diff));
        }
        return res;
    }
    
    public static AttrType getResName(AttrType attr) {
        return new CalcAttrType(attr.name + "_Diff");
    }
}
