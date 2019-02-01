package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class PassThruCalculator extends Calculator {
    private static final Logger log = LoggerFactory.getLogger(PassThruCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    private final UnifiedDataSource uSource;
        
    public static final DbAttrType LOTSIZE = new DbAttrType("LOTSIZE");
    public static final DbAttrType SECTYPE = new DbAttrType("TPCI", "TPCI", 0L, 0L, 3);
    public static final DbAttrType SIC = new DbAttrType("SICH", "SIC", 0L, Time.fromDays(90), 3);
    public static final DbAttrType CSHOQ = new DbAttrType("CSHOQ", "CSHOQ", 0L, Time.fromDays(20), 3);
    
    //XXX need to change this to a better mktcap!!
    public static final DbAttrType CAP = new DbAttrType("CAPITALIZATION", "CAPITALIZATION", Time.fromDays(365), 0L);    
    
    private static final long SQ_MAX_AGE = Time.fromDays(90);
    private static final long SQ_BF_OFFSET = 0L;
    public static final DbAttrType FLOAT = new DbAttrType("FLOAT", "FLOAT", SQ_MAX_AGE, SQ_BF_OFFSET);
    public static final DbAttrType DAYS_TO_COVER = new DbAttrType("DAYS_TO_COVER", "DAYS_TO_COVER", SQ_MAX_AGE, SQ_BF_OFFSET);
    public static final DbAttrType SQ_RANK = new DbAttrType("SQ_RANK", "SQ_RANK", SQ_MAX_AGE, SQ_BF_OFFSET);
    public static final DbAttrType PCT_INSTITUTIONAL = new DbAttrType("PCT_INSTITUTIONAL", "PCT_INSTITUTIONAL", SQ_MAX_AGE, SQ_BF_OFFSET);
    public static final DbAttrType PCT_INSIDERS = new DbAttrType("PCT_INSIDERS", "PCT_INSIDERS", SQ_MAX_AGE, SQ_BF_OFFSET);
        
    private static final Set<DbAttrType> attrs = new HashSet<DbAttrType>() {{
        add(BorrowCalculator.BORROW_ALLOCATED);
    //    add(BorrowCalculator.LIMEHTB);
        add(BorrowCalculator.BORROW_AVAILABILITY);
//      add("LOTSIZE");
        
        add(SIC);
        add(BarraCalculator.B_BETA);
        add(BarraCalculator.IND1);
        
        add(CAP);
        add(CSHOQ);
        add(FLOAT);
        add(DAYS_TO_COVER);
        add(SQ_RANK);
        add(PCT_INSTITUTIONAL);
        add(PCT_INSIDERS);
    }};

    public PassThruCalculator(UnifiedDataSource uSource) {
        this.uSource = uSource;
    }

    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        Set<AttrType> res = new HashSet<AttrType>();
    	
        for ( DbAttrType attr : attrs ) {
            log.info("Calculating " + attr.name + " as of " + df.format(asof));
            Map<Security,Attribute> r = uSource.attrSource.getAttrAsOf(secs, attr, asof);
            for( Map.Entry<Security,Attribute> ent : r.entrySet()) {
                cr.add(ent.getKey(), ent.getValue());
            }
            log.info("Calculated " + attr + " count: " + r.size());
            res.add(attr);
        }
                
        return res;
    }   
}
