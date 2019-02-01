package ase.calculator;

import java.util.Collection;
import java.util.Map;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.LoggerFactory;

public class GroupMeanAdjustCalculator {
    protected static final Logger log = LoggerFactory.getLogger(GroupMeanAdjustCalculator.class.getName());

    public static AttrType calculate(CalcResults cr, AttrType partitionname, AttrType attr) throws Exception {
        AttrType resname = getResName(attr, partitionname);
        log.info("Calculating "+resname);
        Map<Security,Attribute> attrs = cr.getResult(attr);
        Map<String, Collection<Security>> partition = cr.partitions.get(partitionname);
        int totcnt = 0;
        for(Map.Entry<String, Collection<Security>> ent : partition.entrySet()) {
            double tally = 0.0;
            int cnt = 0;
            for( Security sec : ent.getValue() ) {
                if (attrs.containsKey(sec)) {
                    tally += attrs.get(sec).asDouble();
                    cnt++;
                }
            }
            if ( cnt < 3 ) {
                if ( partitionname != PassThruCalculator.SIC )
                    log.warning("Grouping "+ent.getKey()+" is too small (" + cnt + ") to mean adjust!");
                continue;
            }

            double mean = tally/cnt;
            for( Security sec : ent.getValue() ) {
                Attribute att = attrs.get(sec);
                if( att != null ) {
                    cr.add( sec, resname, att.date, att.asDouble() - mean);
                    totcnt++;
                }
            }
        }
        log.info("GroupMeanAdjustCalculator on " + attr + " with " + partitionname + " affected " + totcnt);
        return resname;
    }

    public static AttrType getResName(AttrType attr, AttrType partition) {
        return new CalcAttrType(attr.name + "_MA-" + partition.name, attr.datatype);
    }
}
