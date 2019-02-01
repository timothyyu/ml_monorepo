package ase.calculator.filter;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import ase.data.DailyPriceSource;
import ase.data.Exchange;
import ase.data.Security;
import ase.timeseries.Bar;
import ase.timeseries.DailyBarTimeSeries;
import ase.util.Time;

public class SecurityPriceFilter extends SecurityFilter {
    private final double hp;
    private final double lp;
    private final double advp;
    private final int advdays;
    private final DailyPriceSource dpSource;
    private final Exchange.Type exch;

    public SecurityPriceFilter( double lp, double hp, double advp, int advdays, DailyPriceSource dpSource, Exchange.Type exch ) {
        assert hp >= lp;

        this.hp = hp;
        this.lp = lp;
        this.advp = advp;
        this.advdays = advdays;
        this.dpSource = dpSource;
        
        this.exch = exch;
    }

    public Set<Security> filter( Set<Security> secs, long asof ) throws Exception {
        Set<Security> res = new HashSet<Security>(secs.size());
        
        //filter as of last full day of prices...
        //long today = Time.midnight(asof);
        ///XXX [asof-advdays,asof-1]
        Map<Security, DailyBarTimeSeries> pMap = dpSource.getTimeSeries(secs, Time.today(Exchange.subtractTradingDays(asof, advdays, exch)), Exchange.prevTradingDay(asof, exch), exch);
        for (Security sec : secs) {
            DailyBarTimeSeries dbts = pMap.get(sec);
            Bar b = dbts.getLastBar();
            
            if ( b == null || Double.isNaN(b.close) ) {
                log.warning("Could not look up price for security " + sec + " asof " + df.formatShort(Exchange.prevTradingDay(asof, exch))+"]");
                continue;
            }
            double secadvp = dbts.getAverageVolPrice(advdays, 0);
            if ( Double.isNaN(secadvp) || secadvp < advp ) {
                log.warning("Filtered " + sec + " on advp: " + secadvp);
                continue;
            }
            
            if ( b.close < lp || b.close > hp ) {
                log.warning("Filtered " + sec + " on close: " + b.close);
                continue;
            }
            res.add(sec);
        }
        log.info("Filtering stocks on price and adv, Kept " + res.size() + "/" + secs.size());
        return res;
    }
}
