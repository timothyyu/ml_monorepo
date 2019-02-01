package ase.calculator;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.NavigableSet;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.DistributionSummary;
import ase.data.Estimate;
import ase.data.EstimateSeries;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLEstimateWidget;
import ase.timeseries.DailyBar;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class EarningsEstimatesCalculator {
    private static final Logger log = LoggerFactory.getLogger(TargetCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    private final UnifiedDataSource uSource;
    private final Exchange.Type primaryExch;
    
    public EarningsEstimatesCalculator(UnifiedDataSource uSource, Exchange.Type exch) {
        this.uSource = uSource;
        this.primaryExch = exch;
    }
    
    public Set<AttrType> calculate(CalcResults cr, DbAttrType attrType, Set<Security> secs, long asof) throws Exception {
        Set<AttrType> res = new HashSet<AttrType>();
        assert attrType.dbname.contains("_A_");
        
        Map<Security,DailyBar> priceMap = uSource.dailySource.getBarAsOf(secs, asof, primaryExch);
        Map<Security, NavigableSet<Long>> periodMap = uSource.estWidget.getCalendarPeriods(secs, PeriodCalculator.PERIOD_YEARS, asof);
        for (int ii = 0; ii < 3; ii++) {
            long periodDateFloor = Time.addDays(Time.today(asof), ii*365);
            //For each sec, get the date when annual results are released, after periodDateFloor
            Map<Security, Long> secAndDate = new HashMap<Security, Long>();
            for (Security sec : secs) {
            	NavigableSet<Long> periods = periodMap.get(sec);
            	if (periods == null)
            		continue;
            	Long period = periods.ceiling(periodDateFloor);
            	if (period == null)
            		continue;
            	secAndDate.put(sec, period);
            }
            
            Map<Security,EstimateSeries<?>> estsMap = uSource.estWidget.getConsensus(secAndDate, attrType, asof, asof - Time.fromDays(365));
            log.info("Retrieved " + attrType.name + " on " + estsMap.size() + "/" + secs.size() + " stocks for " + df.format(periodDateFloor));
            
            AttrType tAttr = getResName(ii);
            for (Security sec : secs) {       
                EstimateSeries<DistributionSummary> estSeries = (EstimateSeries<DistributionSummary>)estsMap.get(sec);            
                if (estSeries == null) {
                    log.warning("No attribute " + attrType + " for " + sec);
                    continue;
                }
                Estimate<DistributionSummary> est = estSeries.getLaggedEstimate(0);
                if ( est == null ) {
                    log.severe("Could not find lag 0 estimate for " + estSeries);
                    continue;
                }
                                
                DailyBar db = priceMap.get(sec);
                if ( db == null ) {
                    log.severe("Could not find price for " + sec.getSecId() + " asof " + df.debugFormat(asof));
                    continue;
                }
                double price =db.close;
    			if (EstimatesCalculator.SPLIT_ADJ) {
    				double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(db.close_ts), asof);
    				if (splitAdj != 1)
    					log.info("Adjusting price of secid="+sec.getSecId()+" with adj="+splitAdj+" between ("+df.debugFormat(db.close_ts)+", "+df.debugFormat(asof)+"]");
    				price /= splitAdj;
    			}
    			
                Double currencyAdj = uSource.exWidget.estimateToUSD(sec, est, EstimatesCalculator.CURRENCY_ADJ);
                if (currencyAdj == null)
                	continue;
    			
                double val = currencyAdj * est.value.mean / price;
                cr.add(sec, tAttr, est.orig, val);
            }
            res.add(tAttr);
        }
        return res;
    }
    
    public static AttrType getResName(int num) {
        return new CalcAttrType("ee2p" + num);
    }
}
