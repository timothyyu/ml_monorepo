package ase.portfolio;

public class SecurityTradeInfo {
    public static final double HARD_BOUND = 1.2;
    
    public double softmin = Double.NaN;
    public double softmax = Double.NaN;
    public double hardmin = Double.NaN;
    public double hardmax = Double.NaN;
    
    public int borrow = 0;
    public double borrow_rate = 0.0;
    public int lotsize = 0;
    public double advp = Double.NaN;
    
    public double max_pct_adv = Double.NaN;
    
    public boolean tradeable = false;
    public boolean expandable = false;
   
    private double lbound = 0.0;
    private double ubound = 0.0;
    
    public SecurityTradeInfo(int lotsize, double max_pct_adv) {
        assert lotsize > 0;
        
        this.lotsize = lotsize;
        this.max_pct_adv = max_pct_adv;
    }
    
    public SecurityTradeInfo(double softmin, double softmax, double hardmin, double hardmax, boolean tradeable, int lotsize, double max_pct_adv) {
        assert lotsize > 0;
        
        this.softmin = softmin;
        this.softmax = softmax;
        this.hardmin = hardmin;
        this.hardmax = hardmax;
        this.tradeable = tradeable;
        this.lotsize = lotsize;
        this.max_pct_adv = max_pct_adv;
    }
    
    public void setBorrow(int borrow) {
        assert borrow >= 0;
        this.borrow = borrow;
    }
    
    public void setLotSize(int lotsize) {
        assert lotsize > 0;
        this.lotsize = lotsize;
    }
    
    public void setAdvp(double advp) {
        assert advp > 0;
        this.advp = advp;
    }
    
    public void calcBounds(double position, double prc) {
        if ( expandable ) assert tradeable;
        
        double advbound = max_pct_adv * advp;
        
        if ( ! tradeable ) {
            lbound = ubound = position;
            return;
        }
        
        //XXX REMOVE ME!!
        int hackborrow = borrow > 100 ? borrow-100 : borrow;
        
        double tot_borrow_amt = -hackborrow * prc;
        
        double softmin_tmp = Math.max(-advbound, tot_borrow_amt);
        softmin = Double.isNaN(softmin) ? softmin_tmp : Math.max(softmin, softmin_tmp);
        
        double softmax_tmp = advbound;
        softmax = Double.isNaN(softmax) ? softmax_tmp : Math.min(softmax, softmax_tmp);
        
        //XXX this should really be based on mktcap or something...
        double hardmin_tmp = HARD_BOUND * softmin;
        hardmin = Double.isNaN(hardmin) ? hardmin_tmp : Math.max(hardmin, hardmin_tmp);
        
        double hardmax_tmp = HARD_BOUND * softmax;
        hardmax = Double.isNaN(hardmax) ? hardmax_tmp : Math.min(hardmax, hardmax_tmp);
        
        if ( position > 0 ) {
            if (! expandable) {
                lbound = 0;
                ubound = Math.min(hardmax, Math.min(position, softmax));
            } 
            else { 
                lbound = Math.max(softmin, hardmin);
                ubound = Math.min(hardmax, Math.max(position, softmax));
            }
        }
        else {
            if (! expandable) {
                lbound = Math.max(hardmin, Math.max(position, softmin));
                ubound = 0;
            }
            else { 
                lbound = Math.max(hardmin, Math.min(position, softmin));
                ubound = Math.min(softmax, hardmax);
            }
        }
        
        assert( !(lbound > ubound ) );
    }
    
    public double getLBound() {
        return lbound;
    }
    public double getUBound() {
        return ubound;
    }
}
