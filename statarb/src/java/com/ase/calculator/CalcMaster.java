package ase.calculator;

import java.io.FileReader;
import java.util.Properties;
import java.util.Set;
import java.util.logging.Logger;

import ase.calculator.filter.SecurityFilter;
import ase.calculator.filter.SecurityNumericAttrFilter;
import ase.calculator.filter.SecurityPriceFilter;
import ase.data.CalcResults;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.Universe;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class CalcMaster {
    public enum Mode { SIM, LIVE };
    
    private static final Logger log = LoggerFactory.getLogger(CalcMaster.class.getName());
    private static final ASEFormatter df  = ASEFormatter.getInstance();

    private final UnifiedDataSource uSource;
    
    private final Universe uni;
    public final Mode mode;
    
    private final int advdays;
    
    private final SecurityPriceFilter fexp_p;
    private final SecurityPriceFilter fprc_p;
    private final SecurityPriceFilter ffnd_p;
    private final SecurityPriceFilter ftrd_p;

    private final SecurityNumericAttrFilter fexp_c;
    private final SecurityNumericAttrFilter fprc_c;
    private final SecurityNumericAttrFilter ffnd_c;
    private final SecurityNumericAttrFilter ftrd_c;

    private final GroupingCalculator gCalc;
    private final PassThruCalculator ptCalc;
    private final DailyPriceCalculator dpCalc;
    private final FactorCalculator factCalc;
    private final FundamentalCalculator fundCalc;
    private final FlyCalculator newsCalc;
    private final EstimatesCalculator estCalc;
    private final EarningsDateCalculator earningsCalc;
    private final RatingsCalculator ratingsCalc;
    private final PeriodCalculator periodCalc;
    private final BorrowCalculator borrowCalc;
    private final BuybackCalculator bbCalc;
    private final ShortInterestCalculator siCalc;
    private final IntradayBarCalculator ibCalc;
    private final ResidualCalculator rrCalc;
    private final PcaCalculator pcaCalc;
    private final PcaCalculator pcaDailyCalc;
    //private final PcaCalculator_EXP pcaCalcExp;
    private final ShortTermEventCalculator steCalc;
    private final NewsCalculator nCalc;

    public CalcMaster(Properties config, Universe uni, Mode mode) {
        this.mode = mode;
        this.uni = uni;

        advdays = Integer.parseInt(config.getProperty("adv_days"));

        uSource = new UnifiedDataSource(mode == Mode.LIVE);

        //init calculators
        ptCalc = new PassThruCalculator(uSource);
        dpCalc = new DailyPriceCalculator(uSource, Integer.parseInt(config.getProperty("adv_days")), uni.primaryExch);
        gCalc = new GroupingCalculator();
        factCalc = new FactorCalculator(uSource, Integer.parseInt(config.getProperty("factor_days_lookback")), 
                                        Integer.parseInt(config.getProperty("num_factor_days")), uni.primaryExch);
        fundCalc = new FundamentalCalculator(uSource);
        newsCalc = new FlyCalculator(uSource, factCalc);
        estCalc = new EstimatesCalculator(uSource, uni.primaryExch);
        earningsCalc = new EarningsDateCalculator(uSource, factCalc);
        ratingsCalc = new RatingsCalculator(uSource, uni.primaryExch);
        periodCalc = new PeriodCalculator();
        borrowCalc = new BorrowCalculator(uSource);
        bbCalc = new BuybackCalculator(uSource);
        siCalc = new ShortInterestCalculator(uSource);
        ibCalc = new IntradayBarCalculator(uSource, uni.primaryExch);
        rrCalc = new ResidualCalculator();
        pcaCalc = new PcaCalculator(uSource, uni.primaryExch, Time.MILLIS_PER_HOUR, false);
        pcaDailyCalc = new PcaCalculator(uSource, uni.primaryExch, Time.MILLIS_PER_HOUR, true);
        //pcaCalcExp = new PcaCalculator_EXP(uSource, uni.primaryExch, Time.MILLIS_PER_HOUR);
        steCalc = new ShortTermEventCalculator();
        nCalc = new NewsCalculator(uSource);

        //init security filters
        ftrd_p = new SecurityPriceFilter( Double.parseDouble(config.getProperty("t_lp")), 
                                          Double.parseDouble(config.getProperty("t_hp")), 
                                          Double.parseDouble(config.getProperty("t_min_advp")),
                                          advdays,
                                          uSource.dailySource, uni.primaryExch);
        fexp_p = new SecurityPriceFilter( Double.parseDouble(config.getProperty("e_lp")), 
                                          Double.parseDouble(config.getProperty("e_hp")), 
                                          Double.parseDouble(config.getProperty("e_min_advp")),
                                          advdays,
                                          uSource.dailySource, uni.primaryExch);
        fprc_p = new SecurityPriceFilter( Double.parseDouble(config.getProperty("p_lp")), 
                                          Double.parseDouble(config.getProperty("p_hp")), 
                                          Double.parseDouble(config.getProperty("p_min_advp")),
                                          advdays,
                                          uSource.dailySource, uni.primaryExch);
        ffnd_p = new SecurityPriceFilter( Double.parseDouble(config.getProperty("f_lp")), 
                                          Double.parseDouble(config.getProperty("f_hp")), 
                                          Double.parseDouble(config.getProperty("f_min_advp")),
                                          advdays,
                                          uSource.dailySource, uni.primaryExch);

        fexp_c = new SecurityNumericAttrFilter( PassThruCalculator.CAP, Double.parseDouble(config.getProperty("e_min_mktcap")), Double.MAX_VALUE, uSource.attrSource);
        fprc_c = new SecurityNumericAttrFilter( PassThruCalculator.CAP, Double.parseDouble(config.getProperty("p_min_mktcap")), Double.MAX_VALUE, uSource.attrSource);
        ffnd_c = new SecurityNumericAttrFilter( PassThruCalculator.CAP, Double.parseDouble(config.getProperty("f_min_mktcap")), Double.MAX_VALUE, uSource.attrSource);
        ftrd_c = new SecurityNumericAttrFilter( PassThruCalculator.CAP, Double.parseDouble(config.getProperty("t_min_mktcap")), Double.MAX_VALUE, uSource.attrSource);
    }

    public CalcResults calculate(long calctime, CalcResults cr) throws Exception {
        cr.setAsOf(calctime);

        // filter the universe today
        log.info("filtering universe for " + df.format(calctime));
        Set<Security> secs = mode == Mode.LIVE ? uni.getLivingUniverse() : uni.secs;
        
        Set<Security> utrd = SecurityFilter.calculateFilterAttributes(cr, SecurityFilter.TRADEABLE, ftrd_c.filter(ftrd_p.filter(secs,calctime),calctime), calctime);
        Set<Security> uexp = SecurityFilter.calculateFilterAttributes(cr, SecurityFilter.EXPANDABLE, fexp_c.filter(fexp_p.filter(secs,calctime),calctime), calctime);
        Set<Security> uprc = SecurityFilter.calculateFilterAttributes(cr, SecurityFilter.PRICE_FORECASTABLE, fprc_c.filter(fprc_p.filter(secs,calctime),calctime), calctime);
        Set<Security> ufnd = SecurityFilter.calculateFilterAttributes(cr, SecurityFilter.FUND_FORECASTABLE, ffnd_c.filter(ffnd_p.filter(secs,calctime),calctime), calctime);

        log.info("FILTERS: calctime: " + df.format(calctime) 
                 + " expandable: " + uexp.size()
                 + ", prc 4castable: " + uprc.size() 
                 + ", fnd 4castable: " + ufnd.size()
                 + ", tradeable: " + utrd.size() );

        uni.checkUniverseSize(uexp);
        uni.checkUniverseSize(uprc);
        uni.checkUniverseSize(ufnd);
        uni.checkUniverseSize(utrd);
        
        //load live bars
        if (mode == Mode.LIVE) {
            log.info("Preloading live bars...");
        	uSource.barSource.preload(secs, Time.today(calctime), Time.today(calctime));
        }
        ptCalc.calculate(cr, secs, calctime);
        gCalc.calculate(cr, secs, calctime);
        periodCalc.calculate(cr, uexp, calctime);
        dpCalc.calculate(cr, secs, calctime, mode);
        fundCalc.calculate(cr, ufnd, calctime);
        //XXX newsCalc and earningsCalc depend on factCalc being executed though a trending calculator
        factCalc.calculate(cr, utrd, calctime);
        newsCalc.calculate(cr, uprc, calctime);
        estCalc.calculate(cr, uprc, ufnd, calctime);
        earningsCalc.calculate(cr, uprc, calctime);
        ratingsCalc.calculate(cr, uprc, calctime);
        borrowCalc.calculate(cr, uprc, calctime);
        borrowCalc.calculateRates(cr, secs, calctime);
        bbCalc.calculate(cr, uprc, calctime);
        siCalc.calculate(cr, uprc, calctime);
        ibCalc.calculate(cr, secs, calctime);
        rrCalc.calculate(cr, uprc, calctime);
        pcaCalc.calculate(cr, uprc, calctime);
        pcaDailyCalc.calculate(cr, uprc, calctime);
        steCalc.calculate(cr, calctime, 1);
        nCalc.calculate(cr, uprc, calctime);
        //pcaCalcExp.calculate(cr, uprc, calctime);
        
        return cr;
    }
    
    public Set<Security> getSecurities() {
        return uni.secs;
    }

    public static void main(String[] argv) {
        try {
            Properties config_uni = new Properties();
            Properties config_calc = new Properties();

            config_uni.load(new FileReader(argv[1]));
            config_calc.load(new FileReader(argv[2]));

            Universe u = new Universe(config_uni, System.getenv("RUN_DIR"), Time.now());
            CalcMaster calc = new CalcMaster(config_calc, u, Mode.SIM);
            
        } catch ( Exception e ) {
            e.printStackTrace();
        }
    }
}
