package ase.portfolio;

import java.util.Map;

import ase.calculator.Forecast;
import ase.data.Security;
import ase.util.ASEFormatter;

public class Order implements Comparable<Order> {
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    public final long orderid;
    public final Security sec;
    public final long ts;
    public final int shares;
    public final double eslip;
    public final double dutil;
    public final double dmu;
    public final double drisk;
    public final double costs;
    public final double aggr;
    public final double prc;

    public final Map<Forecast, Double> mus;

    public Order(long orderid, Security sec, long ts, int shares, Map<Forecast, Double> mus, double dutil, double dmu, double drisk, double eslip, double costs, double aggr, double prc) {
        assert ts > 0;
        assert shares > -1000000 && shares < 1000000;
        assert eslip >= 0.0;
        //XXX dcost can be negative!!!
        //assert costs >= 0.0;
        
        this.orderid = orderid;
        this.sec = sec;
        this.ts = ts;
        this.shares = shares;
        this.mus = mus;
        this.eslip = eslip;
        this.dutil = dutil;
        this.dmu = dmu;
        this.drisk = drisk;
        this.costs = costs;
        this.aggr = aggr;
        this.prc = prc;
    }
        
    public int compareTo(Order order) {
        if (this.ts > order.ts) return 1;
        else if (this.ts < order.ts) return -1;
        else return 0;
    }
    
    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((sec == null) ? 0 : sec.hashCode());
        result = prime * result + shares;
        result = prime * result + (int) (ts ^ (ts >>> 32));
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        Order other = (Order) obj;
        if (sec == null) {
            if (other.sec != null)
                return false;
        } else if (!sec.equals(other.sec))
            return false;
        if (shares != other.shares)
            return false;
        if (ts != other.ts)
            return false;
        return true;
    }
    
    public static long getUniqOrderid(long millisPastMidnight, int secid) {
        return (millisPastMidnight * 1000000 + secid);
    }

    public String toString() {
        return "O|"+orderid+"|"+sec.getSecId() + "|" + df.format(ts) + "|" + shares + "|" + dutil + "|" + dmu + "|" + drisk + "|" + eslip + "|" + costs + "|" + aggr + "|" + prc;
    }
    
    public static String dumpHeader() {
        return "type|orderid|secid|ts|shares|dutil|dmu|drisk|eslip|costs|aggr|oprice";
    }
    
    public String dumpOutput() {
        return "O|" + orderid + "|" + sec.getSecId() + "|" + ts + "|" + shares + "|" + dutil + "|" + dmu + "|" + drisk + "|" + eslip + "|" + costs + "|" + aggr + "|" + prc + "\n";
    }
}
