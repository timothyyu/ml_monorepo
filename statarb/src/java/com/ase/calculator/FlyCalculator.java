package ase.calculator;

import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class FlyCalculator extends Calculator {
    private static final Logger log = LoggerFactory.getLogger(FlyCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
        
    //XXX there are not fly backfilled data
    private static final long F_MAX_AGE = Time.fromDays(30);
    private static final long F_BACKFILL_OFFSET = Time.fromMinutes(30);
    private static final DbAttrType FLY1 = new DbAttrType("FLY1", "FLY1", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLY2 = new DbAttrType("FLY2", "FLY2", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYRATING = new DbAttrType("FRATING", "FRATING", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYEARN = new DbAttrType("FEARN", "FEARN", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYHOT = new DbAttrType("FHOT", "FHOT", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYRUMOR = new DbAttrType("FRUMOR", "FRUMOR", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYOPTION = new DbAttrType("FOPTION", "FOPTION", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYREC = new DbAttrType("FREC", "FREC", F_MAX_AGE, F_BACKFILL_OFFSET);
    private static final DbAttrType FLYSYND = new DbAttrType("FSYND", "FSYND", F_MAX_AGE, F_BACKFILL_OFFSET);
    
    private static final Map<DbAttrType, Double> attr2hl = new HashMap<DbAttrType,Double>() {{
        put(FLY1, 0.0);
        put(FLY2, 0.0);
        put(FLYRATING, 10.0);
        put(FLYEARN, 10.0);
        put(FLYHOT, 3.0);
        put(FLYRUMOR, 3.0);
        put(FLYOPTION, 3.0);
        put(FLYREC, 3.0);
        put(FLYSYND, 3.0);
    }};

    private final Map<DbAttrType, Map<Security, Double>> lastsummap = new HashMap<DbAttrType, Map<Security, Double>>();
    private final Map<DbAttrType, Map<Security, Double>> lastcntmap = new HashMap<DbAttrType, Map<Security, Double>>();
    private final Map<DbAttrType, Map<Security, Long>> lastdatemap = new HashMap<DbAttrType, Map<Security, Long>>();

    private final UnifiedDataSource uSource;
    private final TrendingCalculator trCalc;
    
    private static final long MAX_NEWS_DECAY_TIME = Time.fromDays(30);
    
    public FlyCalculator(UnifiedDataSource uSource, FactorCalculator fCalc) {
        this.uSource = uSource;
        this.trCalc = new TrendingCalculator(this.uSource, fCalc);
        
        for (DbAttrType attrname : attr2hl.keySet()) {
            lastsummap.put(attrname, new HashMap<Security, Double>());
            lastcntmap.put(attrname, new HashMap<Security, Double>());
            lastdatemap.put(attrname, new HashMap<Security, Long>());
        }
    }

    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
        if (!needToCalc(asof)) return null;
        for (DbAttrType attrType : attr2hl.keySet()) {
            log.info("Calculating " + attrType);
            
            Map<Security, Double> lastsum = lastsummap.get(attrType);
            Map<Security, Double> lastcnt = lastcntmap.get(attrType);
            Map<Security, Long> lastdate = lastdatemap.get(attrType);
            
            Map<Security, NavigableMap<Long,Attribute>> attrMap = uSource.attrSource.getRange(secs, attrType, asof - MAX_NEWS_DECAY_TIME, asof);
            for (Security sec : secs) {
                Double sum = lastsum.get(sec);
                if (sum == null) {
                    sum = new Double(0);
                    lastsum.put(sec, sum);
                }
                Double cnt = lastcnt.get(sec);
                if (cnt == null) {
                    cnt = new Double(0);
                    lastcnt.put(sec, cnt);
                }
                Long date = lastdate.get(sec);
                if (date == null) {
                    date = new Long(0);
                    lastdate.put(sec, date);
                }

                for (Attribute attr : attrMap.get(sec).values()) {
                    if (!Exchange.affectsSameDay(date, attr.date, sec.primaryExchange)) {
                        sum = 0.0;
                        cnt = 0.0;
                        date = 0L;
                    }
                    if (attrType == FLY1 || attrType == FLY2) {
                        if (attr.asDouble() == 0.0) {
                            sum += 1;
                        }
                        else {
                            continue;
                        }
                    }
                    else {
                        sum += attr.asDouble();
                    }
                    cnt += 1;
                    date = attr.date;
                }

                if (sum != 0 && cnt > 0 && asof - date < MAX_NEWS_DECAY_TIME) {
                    cr.add(sec, attrType, date, sum / cnt);
                }
                lastsum.put(sec, sum);
                lastcnt.put(sec, cnt);
                lastdate.put(sec, date);
            }
        }

        for (Map.Entry<DbAttrType, Double> ent : attr2hl.entrySet()) {
            double halflife = ent.getValue();
            if (halflife > 0.0) {
                AttrType dkAttr = DecayCalculator.calculate(cr, ent.getKey(), asof, (long)halflife*Time.fromDays(1), 3);
            }
        }
        
        BoundingCalculator bndCalc = new BoundingCalculator(BoundingCalculator.Mode.ABS);
        //TrendingCalculator trCalc = new TrendingCalculator(uSource); 
        AttrType fly_TC = trCalc.calculate(cr, FLY1, asof, TrendingCalculator.Mode.C2C);
        AttrType fly_TC_B = bndCalc.calculate(cr, fly_TC, 2500);
        DecayCalculator.calculate(cr, fly_TC_B, asof, Time.fromDays(5), 3);

        AttrType fly_TR = trCalc.calculate(cr, FLY1, asof, TrendingCalculator.Mode.RSDC2C);
        AttrType fly_TR_B = bndCalc.calculate(cr, fly_TR, 2500);
        DecayCalculator.calculate(cr, fly_TR_B, asof, Time.fromDays(5), 3);

        // o2cC-NAdj
        /*String calcname = calc_prefix + "ticker";
        String decaycalcname = DecayCalculator.decay(calcMap, calcname, calcdate, Time.fromDays(1));
        String adjcalcname = AdjustCalculator.adjust(calcMap, BoundingCalculator.getBndName(TickPriceCalculator.O2C_attName), decaycalcname, CalcMaster.NewsADJName, AdjustCalculator.Mode.NONE);*/

        // noflyticker2 reversion
        AttrType fly2_D = DecayCalculator.calculate(cr, FLY2, asof, Time.fromDays(3), 3);
        Map<Security, Attribute> fly2Attrs = cr.getResult(fly2_D);
        if (fly2Attrs.size() > secs.size() / 10) {
            CalcAttrType nofly2 = new CalcAttrType("nofly2");
            for (Map.Entry<Security, Attribute> ent : fly2Attrs.entrySet()) {
                cr.add(ent.getKey(), nofly2, ent.getValue().date, 1.0);
            }

            AttrType omftdk = RescaleCalculator.calculate(cr, nofly2, fly2_D, RescaleCalculator.Mode.MINUS);
            // cr.remove(fly2_D);
            AttrType nofly2_TC = trCalc.calculate(cr, nofly2, asof, TrendingCalculator.Mode.C2C);
            AttrType nofly2_TC_B = bndCalc.calculate(cr, nofly2_TC, 2500);
            AttrType nofly2_TR = trCalc.calculate(cr, nofly2, asof, TrendingCalculator.Mode.RSDC2C);
            AttrType nofly2_TR_B = bndCalc.calculate(cr, nofly2_TR, 2500);
            // cr.remove(nofly2);
            
            RescaleCalculator.calculate(cr, nofly2_TC_B, omftdk, RescaleCalculator.Mode.MULT);
            RescaleCalculator.calculate(cr, nofly2_TR_B, omftdk, RescaleCalculator.Mode.MULT);
            // calcMap.remove(omftdkcalcname);
        }
        else {
            log.severe("we don't appear to have enough flyticker2s to calculate, " + fly2Attrs.size() + " < " + secs.size());
        }
        return null;
    }
}

