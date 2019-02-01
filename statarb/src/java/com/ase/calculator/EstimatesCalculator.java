package ase.calculator;

import java.util.HashSet;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class EstimatesCalculator extends Calculator {
    private static final Logger log = LoggerFactory.getLogger(EstimatesCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    private final UnifiedDataSource uSource;
    
    private final EstDiffCalculator epsqCalc;
    private final EstDiffCalculator tgtDiffCalc;
    private final TargetCalculator tgtCalc;
    private final EarningsEstimatesCalculator ee2pCalc;
    
    public static final long MAX_Q_DIFF_TIME = Time.fromDays(120);
    public static final long MAX_DECAY_TIME = Time.fromDays(45);
    
    //XXX wrt decaying, may want to examing where out cutoff is...
    private static final long R_MAX_AGE = 0L;
    private static final long R_BF_OFFSET = Time.fromDays(1);
    public static final DbAttrType EEPSQ_C = new DbAttrType("EPS_Q_CE", "EPS_Q_CE", R_MAX_AGE, R_BF_OFFSET);
    public static final DbAttrType EEPSQ_D = new DbAttrType("EPS_Q_DE", "EPS_Q_DE", R_MAX_AGE, R_BF_OFFSET);
    public static final DbAttrType EEPSA_C = new DbAttrType("EPS_A_CE", "EPS_A_CE", R_MAX_AGE, R_BF_OFFSET);
    public static final DbAttrType TARGET_C = new DbAttrType("TARGETPRICE_CE", "TARGETPRICE_CE", R_MAX_AGE, R_BF_OFFSET);
    public static final DbAttrType TARGET_D = new DbAttrType("TARGETPRICE_DE", "TARGETPRICE_DE" , R_MAX_AGE, R_BF_OFFSET);
    
    public static final AttrType FUTURE_QUARTER_0 = PeriodCalculator.getResName(PeriodCalculator.quarterlyEstimatesPeriod, 0);
    public static final AttrType FUTURE_YEAR_0 = PeriodCalculator.getResName(PeriodCalculator.annualEstimatesPeriod, 0);
    
    public static final boolean CURRENCY_ADJ = true;
    public static final boolean SPLIT_ADJ = true;
    
    public EstimatesCalculator(UnifiedDataSource uSource, Exchange.Type primaryExch) {
        this.uSource = uSource;
        
        epsqCalc = new EstDiffCalculator(uSource, MAX_Q_DIFF_TIME, MAX_DECAY_TIME);
        tgtDiffCalc = new EstDiffCalculator(uSource, MAX_Q_DIFF_TIME, MAX_DECAY_TIME);
        tgtCalc = new TargetCalculator(uSource, MAX_Q_DIFF_TIME);
        ee2pCalc = new EarningsEstimatesCalculator(uSource, primaryExch);
    }
    
    public Set<AttrType> calculate(CalcResults cr, Set<Security> secs_p, Set<Security> secs_f, long asof) throws Exception {
        if (!needToCalc(asof)) return null;
        log.info("Calculating Estimates...");
        Set<AttrType> res = new HashSet<AttrType>();
        
        //Concensus estimates....
        AttrType epsq = epsqCalc.calculateConcensus(cr, EEPSQ_C, secs_p, FUTURE_QUARTER_0,asof);
        AttrType tgtdiff = tgtDiffCalc.calculateTargetConcensus(cr, TARGET_C, secs_p, asof);
        AttrType tgt = tgtCalc.calculateConcensus(cr, TARGET_C, secs_p, asof);
        Set<AttrType> ee2pAttrs = ee2pCalc.calculate(cr, EEPSA_C, secs_f, asof);
        
        //sigma bounding
        BoundingCalculator sbndCalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);
        AttrType epsq_bs = sbndCalc.calculate(cr, epsq, 5.0);
        AttrType epsq_bs_d5 = DecayCalculator.calculate(cr, epsq_bs, asof, Time.fromDays(5), 3);
        AttrType epsq_bs_d10 = DecayCalculator.calculate(cr, epsq_bs, asof, Time.fromDays(10), 3);        
        AttrType epsq_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, epsq_bs);
        AttrType epsq_bs_ba_d5 = DecayCalculator.calculate(cr, epsq_bs_ba, asof, Time.fromDays(5), 3);
        AttrType epsq_bs_ba_d10 = DecayCalculator.calculate(cr, epsq_bs_ba, asof, Time.fromDays(10), 3);
        AttrType epsq_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, epsq_bs);
        AttrType epsq_bs_sa_d5 = DecayCalculator.calculate(cr, epsq_bs_sa, asof, Time.fromDays(5), 3);
        AttrType epsq_bs_sa_d10 = DecayCalculator.calculate(cr, epsq_bs_sa, asof, Time.fromDays(10), 3);
        
        
        AttrType tgtdiff_bs = sbndCalc.calculate(cr, tgtdiff, 5.0);
        AttrType tgtdiff_bs_d5 = DecayCalculator.calculate(cr, tgtdiff_bs, asof, Time.fromDays(5), 3);
        AttrType tgtdiff_bs_d10 = DecayCalculator.calculate(cr, tgtdiff_bs, asof, Time.fromDays(10), 3);
        AttrType tgtdiff_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, tgtdiff_bs);
        AttrType tgtdiff_bs_ba_d5 = DecayCalculator.calculate(cr, tgtdiff_bs_ba, asof, Time.fromDays(5), 3);
        AttrType tgtdiff_bs_ba_d10 = DecayCalculator.calculate(cr, tgtdiff_bs_ba, asof, Time.fromDays(10), 3);
        AttrType tgtdiff_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, tgtdiff_bs);
        AttrType tgtdiff_bs_sa_d5 = DecayCalculator.calculate(cr, tgtdiff_bs_sa, asof, Time.fromDays(5), 3);
        AttrType tgtdiff_bs_sa_d10 = DecayCalculator.calculate(cr, tgtdiff_bs_sa, asof, Time.fromDays(10), 3);

        AttrType tgt_bs = sbndCalc.calculate(cr, tgt, 5.0);
        AttrType tgt_bs_d5 = DecayCalculator.calculate(cr, tgt_bs, asof, Time.fromDays(5), 3);
        AttrType tgt_bs_d10 = DecayCalculator.calculate(cr, tgt_bs, asof, Time.fromDays(10), 3);
        AttrType tgt_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, tgt_bs);
        AttrType tgt_bs_ba_d5 = DecayCalculator.calculate(cr, tgt_bs_ba, asof, Time.fromDays(5), 3);
        AttrType tgt_bs_ba_d10 = DecayCalculator.calculate(cr, tgt_bs_ba, asof, Time.fromDays(10), 3);
        AttrType tgt_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, tgt_bs);
        AttrType tgt_bs_sa_d5 = DecayCalculator.calculate(cr, tgt_bs_sa, asof, Time.fromDays(5), 3);
        AttrType tgt_bs_sa_d10 = DecayCalculator.calculate(cr, tgt_bs_sa, asof, Time.fromDays(10), 3);
        
        
        for(AttrType ee2p : ee2pAttrs) {
            AttrType ee2p_g = GaussianAdjustCalculator.calculate(cr, ee2p);
            AttrType ee2p_g_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, ee2p_g);
            AttrType ee2p_g_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, ee2p_g);
        }
        
        //Detailed Estimates...
        AttrType epsqD = epsqCalc.calculateDetailed(cr, EEPSQ_D, secs_p, FUTURE_QUARTER_0, asof);
        AttrType tgtdiffD = tgtDiffCalc.calculateTargetDetailed(cr, TARGET_D, secs_p, asof);
        AttrType tgtD = tgtCalc.calculateDetailed(cr, TARGET_D, secs_p, asof);

        //sigma boundings
        AttrType epsqD_bs = sbndCalc.calculate(cr, epsqD, 5.0);
        AttrType epsqD_bs_d5 = DecayCalculator.calculate(cr, epsqD_bs, asof, Time.fromDays(5), 3);
        AttrType epsqD_bs_d10 = DecayCalculator.calculate(cr, epsqD_bs, asof, Time.fromDays(10), 3);
        AttrType epsqD_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, epsqD_bs);
        AttrType epsqD_bs_ba_d5 = DecayCalculator.calculate(cr, epsqD_bs_ba, asof, Time.fromDays(5), 3);
        AttrType epsqD_bs_ba_d10 = DecayCalculator.calculate(cr, epsqD_bs_ba, asof, Time.fromDays(10), 3);
        AttrType epsqD_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, epsqD_bs);
        AttrType epsqD_bs_sa_d5 = DecayCalculator.calculate(cr, epsqD_bs_sa, asof, Time.fromDays(5), 3);
        AttrType epsqD_bs_sa_d10 = DecayCalculator.calculate(cr, epsqD_bs_sa, asof, Time.fromDays(10), 3);
        
        
        AttrType tgtdiffD_bs = sbndCalc.calculate(cr, tgtdiffD, 5.0);
        AttrType tgtdiffD_bs_d5 = DecayCalculator.calculate(cr, tgtdiffD_bs, asof, Time.fromDays(5), 3);
        AttrType tgtdiffD_bs_d10 = DecayCalculator.calculate(cr, tgtdiffD_bs, asof, Time.fromDays(10), 3);
        AttrType tgtdiffD_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, tgtdiffD_bs);
        AttrType tgtdiffD_bs_ba_d5 = DecayCalculator.calculate(cr, tgtdiffD_bs_ba, asof, Time.fromDays(5), 3);
        AttrType tgtdiffD_bs_ba_d10 = DecayCalculator.calculate(cr, tgtdiffD_bs_ba, asof, Time.fromDays(10), 3);      
        AttrType tgtdiffD_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, tgtdiffD_bs);
        AttrType tgtdiffD_bs_sa_d5 = DecayCalculator.calculate(cr, tgtdiffD_bs_sa, asof, Time.fromDays(5), 3);
        AttrType tgtdiffD_bs_sa_d10 = DecayCalculator.calculate(cr, tgtdiffD_bs_sa, asof, Time.fromDays(10), 3);      
        
        AttrType tgtD_bs = sbndCalc.calculate(cr, tgtD, 5.0);
        AttrType tgtD_bs_d5 = DecayCalculator.calculate(cr, tgtD_bs, asof, Time.fromDays(5), 3);
        AttrType tgtD_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, tgtD_bs);
        AttrType tgtD_bs_ba_d5 = DecayCalculator.calculate(cr, tgtD_bs_ba, asof, Time.fromDays(5), 3);
        AttrType tgtD_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, tgtD_bs);
        AttrType tgtD_bs_sa_d5 = DecayCalculator.calculate(cr, tgtD_bs_sa, asof, Time.fromDays(5), 3);
        
        return res;
    }
}
