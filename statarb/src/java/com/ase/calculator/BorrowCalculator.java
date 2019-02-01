package ase.calculator;

import java.util.HashSet;
import java.util.Map;
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

public class BorrowCalculator {
    private static final Logger log = LoggerFactory.getLogger(BorrowCalculator.class.getName());
    
    private static final double EPSILON = 1e-8;
    private static final double MAX_BORROW_RATE = -30.0;

    //XXX No point in setting a backfill offset for those. We always get them before 9.30am each day
    public static final DbAttrType BORROW_ALLOCATED = new DbAttrType("BORROW_ALLOCATED", "BORROW_ALLOCATED", Time.fromDays(1), 0L);
    public static final DbAttrType BORROW_REQUESTED = new DbAttrType("BORROW_REQUESTED", "BORROW_REQUESTED", Time.fromDays(1), 0L);
    public static final DbAttrType BORROW_RATE = new DbAttrType("BORROW_RATE", "BORROW_RATE", Time.fromDays(1), 0L);
    public static final DbAttrType BORROW_AVAILABILITY = new DbAttrType("BORROW_AVAILABILITY", "BORROW_AVAILABILITY", Time.fromDays(1), 0L);
    public static final DbAttrType BORROW_RATE_PUSHED = new DbAttrType("BORROW_RATE_PUSHED", "BORROW_RATE_PUSHED", Time.fromDays(1), 0L);
    
    public static final AttrType ADJ_BORROW_RATE = new CalcAttrType("AdjBorrowRate");
    
    private final UnifiedDataSource uSource;
    
    public BorrowCalculator(UnifiedDataSource uSource) {
        this.uSource = uSource;
    }
    
    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        log.info("Calculating Borrow...");
        Set<AttrType> res = new HashSet<AttrType>();  
        Map<Security, Attribute> allocMap = uSource.attrSource.getAttrAsOf(secs, BORROW_ALLOCATED, asof);
        Map<Security, Attribute> reqMap = uSource.attrSource.getAttrAsOf(secs, BORROW_REQUESTED, asof);
        Map<Security, Attribute> availMap = uSource.attrSource.getAttrAsOf(secs, BORROW_AVAILABILITY, asof);
        
        Map<Security, Attribute> advMap = cr.getResult(DailyPriceCalculator.ADVP);
        Map<Security, Attribute> prcMap = cr.getResult(DailyPriceCalculator.lattr(DailyPriceCalculator.PRC, -1));
                
        CalcAttrType retFracAttr = new CalcAttrType("BorrowReturnFrac");        
        CalcAttrType availFracAttr = new CalcAttrType("BorrowAvailMult");
        res.add(retFracAttr);
        res.add(availFracAttr);
        int cnt1 = 0, cnt2 = 0;
        for ( Security sec : secs ) {
            Attribute allocAttr = allocMap.get(sec);
            if ( allocAttr != null ) {
                double num = allocAttr == null ? 0.0 : allocAttr.asDouble(); 
                double frac = 1.0 - (num / reqMap.get(sec).asDouble());
                if (frac < EPSILON) continue;
                cr.add(sec, retFracAttr, allocAttr.date, frac);
                cnt1++;
            }
            res.add(retFracAttr);

            if (availMap.containsKey(sec) && prcMap.containsKey(sec) && advMap.containsKey(sec)) {
                Attribute availAttr = availMap.get(sec);
                double frac = availAttr.asDouble() / (advMap.get(sec).asDouble() / prcMap.get(sec).asDouble());
                if (frac < EPSILON) continue;
                cr.add(sec, availFracAttr, availAttr.date, frac);
                cnt2++;
            }
        }
        log.info("Calculated " + cnt1 + " of " + retFracAttr.name);
        log.info("Calculated " + cnt2 + " of " + availFracAttr.name);
        return res;
    }
    
    public Set<AttrType> calculateRates(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        log.info("Calculating Borrow Rates...");   
        Set<AttrType> res = new HashSet<AttrType>();  
        Map<Security, Attribute> rateMap = uSource.attrSource.getAttrAsOf(secs, BORROW_RATE, asof);
        Map<Security, Attribute> ratePushedMap = uSource.attrSource.getAttrAsOf(secs, BORROW_RATE_PUSHED, asof);
        
        CalcAttrType ratepAttr = new CalcAttrType("AdjPushedBorrowRate");
        for (Security sec : secs) {
            Attribute rAttr = rateMap.get(sec);
            if (rAttr != null) {
                double val = rAttr.asDouble();
                if (val < MAX_BORROW_RATE) {
                    log.severe("Suspicious borrow rate on " + sec.getSecId() + " of " + val);
                    val = MAX_BORROW_RATE;
                }
                cr.add(sec, ADJ_BORROW_RATE, rAttr.date, Math.min(0.0, val/100.0));
            }
            Attribute rpAttr = ratePushedMap.get(sec);
            if (rpAttr != null) {
                double val = rpAttr.asDouble();
                if (val < MAX_BORROW_RATE) {
                    log.severe("Suspicious pushed borrow rate on " + sec.getSecId() + " of " + val);
                    val = MAX_BORROW_RATE;
                }
                cr.add(sec, ratepAttr, rpAttr.date, Math.min(0.0, val/100.0));
            }
        }        
        return res;
    }
}
