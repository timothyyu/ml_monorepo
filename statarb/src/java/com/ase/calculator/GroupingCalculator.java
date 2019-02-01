package ase.calculator;

import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class GroupingCalculator {
    private static final Logger log = LoggerFactory.getLogger(GroupingCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    private static final Set<AttrType> groups = new HashSet<AttrType>() {{
        add(PassThruCalculator.SIC);
        add(BarraCalculator.IND1);
    }};

    public GroupingCalculator() {
    }

    public void calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        for( AttrType group : groups ) {
            Map<Security, Attribute> attrs = cr.getResult(group);
            Map<String, Collection<Security>> attr_partition = partitionByAttribute(attrs);
            
//            for(Map.Entry<String, Collection<Security>> ent : attr_partition.entrySet()) { 
//                System.out.println("PARTITION:" + ent.getKey());
//                for (Security sec : ent.getValue()) {
//                    System.out.println("MEMBER: " + sec);
//                }
//            }
            
            cr.addPartition(group, attr_partition);
            log.info("Created group for "+group+" size: "+attr_partition.size());
        }
    }  
    
    private static Map<String, Collection<Security>> partitionByAttribute(Map<Security, Attribute> map) {
        Map<String, Collection<Security>> res = new HashMap<String,Collection<Security>>();
        for( Map.Entry<Security, Attribute> ent : map.entrySet() ) {
            Collection<Security> set =  res.get(ent.getValue().valueAsString());
            if ( set == null ) {
                res.put(ent.getValue().valueAsString(), set = new HashSet<Security>());
            }
            set.add(ent.getKey());
        }
        return res;
    }

}
