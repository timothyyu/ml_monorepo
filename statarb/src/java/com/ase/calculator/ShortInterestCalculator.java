package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.LoggerFactory;
import ase.util.Time;

public class ShortInterestCalculator { 
    private static final Logger log = LoggerFactory.getLogger(ShortInterestCalculator.class.getName());
    
    private static final long LOOKBACK = Time.fromDays(31); 
    private static final double EPSILON = 1e-6;
    
    //XXX backfill offset of 0. We used file timestamps for born times
    public static final DbAttrType TOTAL_SHORT_INTEREST = new DbAttrType("TOTAL_SHORT_INTEREST", "TOTAL_SHORT_INTEREST", Time.fromDays(90), 0L);
    public static final CalcAttrType siAttr = new CalcAttrType("SIFrac");
    
    private final UnifiedDataSource uSource;
    
    public ShortInterestCalculator(UnifiedDataSource uSource) {
        this.uSource = uSource;
    }
    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        Set<AttrType> res = new HashSet<AttrType>();  
        long startdate = Time.today(asof - Time.fromDays(90));
        Map<Security, NavigableMap<Long,Attribute>> siMap = uSource.attrSource.getRange(secs, TOTAL_SHORT_INTEREST, startdate, asof);
        Map<Security, NavigableMap<Long,Attribute>> floatMap = uSource.attrSource.getRange(secs, PassThruCalculator.FLOAT, startdate, asof);
        
        int cnt = 0;
        for ( Security sec : siMap.keySet() ) {
            NavigableMap<Long, Attribute> siSecMap = siMap.get(sec);
            NavigableMap<Long, Attribute> floatSecMap= floatMap.get(sec);
            if (floatSecMap == null) {
                log.warning("No float attributes for security: " + sec.getSecId());
                continue;
            }
            Map.Entry<Long, Attribute> si2ent = siSecMap.lastEntry();
            if (si2ent == null) {
                log.warning("No Short interest found for " + sec.getSecId());
                continue;
            }
            Attribute si2 = si2ent.getValue();
            Attribute ft2 = floatSecMap.floorEntry(si2.date).getValue();
            if ( si2 == null || ft2 == null || ft2.asDouble() <= 0 || si2.asDouble() < EPSILON) continue;
            cr.add(sec, siAttr, si2.date, si2.asDouble()/ft2.asDouble());
            
            Map.Entry<Long, Attribute> si1ent = siSecMap.floorEntry(si2.date - LOOKBACK);
            if (si1ent == null) continue;
            Attribute si1 = si1ent.getValue();
            Attribute ft1 = floatSecMap.floorEntry(si1.date).getValue();
            if ( si1 == null || ft1 == null || ft1.asDouble() <= 0 || si1.asDouble() < EPSILON) continue;
            cr.add(sec, siAttr, si1.date, si1.asDouble()/ft1.asDouble());
            
            cnt++;
        }
        AttrType si_diff = DiffCalculator.calculate(cr, siAttr, asof, Time.fromDays(45));
        AttrType si_diff_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, si_diff);
        AttrType si_diff_ma_d = DecayCalculator.calculate(cr, si_diff_ma, asof, Time.fromDays(10), 3);
        AttrType si_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, siAttr);
        AttrType si_ma_d = DecayCalculator.calculate(cr, si_ma, asof, Time.fromDays(10), 3);
        res.add(siAttr);
        res.add(si_diff);
        res.add(si_diff_ma_d);
        res.add(si_ma_d);

        log.info("Calculated " + cnt + " of " + siAttr.name);
        return res;
    }    
}
