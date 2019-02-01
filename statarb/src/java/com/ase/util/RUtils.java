package ase.util;

import java.util.Collection;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.Vector;

import ase.calculator.EstimatesCalculator;
import ase.data.DailyPriceSource;
import ase.data.DbAttrType;
import ase.data.EstimateSeries;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.widget.SQLEstimateWidget;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.DailyBarTimeSeries;

public class RUtils {

    public static Set<Security> createSecuritySet( int[] secids ) {
        Set<Security> res = new HashSet<Security>(secids.length);
        for( int i=0; i < secids.length; i++) {
            res.add(new Security(secids[i]));
        }
        return res;
    }

    public static Set<Security> createSecuritySet( String[] secids ) {
        Set<Security> res = new HashSet<Security>(secids.length);
        for( int i=0; i < secids.length; i++) {
            res.add(new Security(Integer.parseInt(secids[i])));
        }
        return res;
    }

    public static String toString(Map<? extends Object, ? extends Object> map) {
        String res = "";
        for( Map.Entry<? extends Object, ? extends Object> ent : map.entrySet() ) {
            res += ent.getKey()+"|"+ent.getValue()+"\n";
        }
        return res;
    }

    public static String toString(Collection<? extends Object> set) {
        String res = "";
        for( Object o : set ) {
            res += o.toString();
        }
        return res;
    }
    
    public static BarTimeSeries getStockPrices( Security sec, long t1, long t2 ) throws Exception {
        DailyPriceSource dpSource = new DailyPriceSource();
        Map<Security, DailyBarTimeSeries> pMap = dpSource.getTimeSeries(CollectionUtils.toSet(sec), t1, t2, Exchange.Type.NYSE);
        return pMap.get(sec);
    }

    public static Bar[] toPriceArray( Map<Security,DailyBarTimeSeries> pmap ) {
        //XXX should be size*bartimeseries size
        Vector<Bar> res = new Vector<Bar>(pmap.size());
        for( DailyBarTimeSeries bts : pmap.values() ) {
            res.addAll(bts.toVector());
        }
        return res.toArray(new Bar[0]);
    }
    
//    public static void getDetailed( Security sec, String estAttr, long asof ) {
//        try {
//            SQLEstimateWidget estWidget = SQLEstimateWidget.instance();
//            Set<Security> secs = CollectionUtils.toSet(sec);
//            DbAttrType attrType = new DbAttrType(estAttr);
//            Map<Security,Map<Integer,EstimateSeries<Double>>> secPastMap = estWidget.getDetailed(secs, attrType, SQLEstimateWidget.DateType.PAST, 
//                    asof, asof, asof - EstimatesCalculator.MAX_Q_DIFF_TIME, false);
//            Map<Integer,EstimateSeries<Double>> brokerMap = secPastMap.get(sec);
//            for (EstimateSeries<Double> series : brokerMap.values()) {
//                System.out.println(series.toString());
//                series.printSeries();
//            }
//        }
//        catch( Exception e) {
//            e.printStackTrace();
//        }
//    }
//    
//    public static void main(String[] argv) throws Exception {
//        RUtils.getDetailed(new Security(11482), "EPS_Q_DE", Time.now());
//    }
}