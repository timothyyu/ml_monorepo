package ase.portfolio;

public class OptInfo {
    public final double target_position;
    public final double dutil;    
    public final double dmu;
    public final double drisk;
    public final double eslip;
    public final double costs;
    public final double eslipAdv;
    public final double hour_mu;
    public final double day_mu;
    public final double drisk2;
    
    public OptInfo(double target_position, double dutil, double dmu, double eslip, double costs, double eslipAdv, double hour_mu, double day_mu, double dutil2) {
        this.target_position = target_position;
        this.dutil = dutil;
        this.dmu = dmu;        
        this.eslip = eslip;
        this.costs = costs;
        this.drisk = dmu - dutil - eslip - costs;
        this.eslipAdv = eslipAdv;
        this.hour_mu = hour_mu;
        this.day_mu = day_mu;
        this.drisk2 = dmu - dutil2 - eslip - costs;
    }

    public String toString() {
        return target_position + "|" + dutil + "|" + dmu + "|" + drisk + "|" + eslip + "|" + costs + "|" + hour_mu + "|" + eslipAdv + "|" + drisk2;
    }
    
    public static String dumpHeader() {
        return "target_pos|dutil|dmu|drisk|eslip|costs|aggr|eslipAdv|drisk2";
    }
}
