package ase.data;

import ase.util.ASEFormatter;

public class Quote implements Price {
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    public final static double MAX_SPREAD_BPS = 50.0;
    
    private final double bid;
    private final double ask;
    private final long ts;
    
    public Quote(double bid, double ask, long ts) {
        assert ts > 0;
        
        this.bid = bid;
        this.ask = ask;
        this.ts = ts;
    }

    public double getBid() {
        return bid;
    }
    
    public double getAsk() {
        return ask;
    }
    
    public long getTs() {
        return ts;
    }
    
    public double getPrice() {
    	return (bid+ask)/2;
    }
    
    public double getSpread() {
        return ask-bid;
    }
    
    public double getSpreadBps() {
        return 10000.0 * getSpread()/getPrice();
    }
    
    public boolean isValid() {
        return bid > 0 && ask > 0 && bid < ask && getSpreadBps() < MAX_SPREAD_BPS;
    }
    
    public String toString() {
        return "Q|" + bid + "|" + ask + "|" + df.format(ts);
    }
    
    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        long temp1, temp2;
        temp1 = Double.doubleToLongBits(bid);
        temp2 = Double.doubleToLongBits(ask);
        result = prime * result + (int) (temp1 ^ (temp1 >>> 32));
        result = prime * result + (int) (temp2 ^ (temp2 >>> 32));
        result = prime * result + (int) (ts ^ (ts >>> 32));
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null) return false;
        if (getClass() != obj.getClass()) return false;
        Quote other = (Quote) obj;
        if (Double.doubleToLongBits(bid) != Double.doubleToLongBits(other.bid)) return false;
        if (Double.doubleToLongBits(ask) != Double.doubleToLongBits(other.ask)) return false;        
        if (ts != other.ts) return false;
        return true;
    }
}
