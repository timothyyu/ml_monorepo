package ase.data;

public class Security implements Comparable<Security> {
    private final Integer secid;
    public final Exchange.Type primaryExchange;
    
    public static enum Type { UNKNOWN, STOCK, FACTOR, FUTURE, CURRENCY, COMMODITY };
    
    public static final Security FACTOR_SEC = new Security(-1); // XXX lets just explicitly store different sec tyupes
    public static final Security MARKET_SEC = new Security(-2);
    
    public Security( int secid, Exchange.Type exch ) {
        this.secid = new Integer(secid);
        this.primaryExchange = exch;
    }
    
    public Security(int secid) {
        this(secid, Exchange.Type.NYSE);
    }
    
    public int getSecId() { 
        return secid.intValue(); 
    }
    
    public boolean isAlive() {
        if ( this instanceof Stock ) {
            return ((Stock)this).alive;
        }
        return true;
    }

    public boolean equals(Object o) {
        if ( o instanceof Security ) {
            Security s2 = (Security)o;
            if ( this.secid.intValue() == s2.secid.intValue() ) return true;
        }
        return false;
    }

    public String toString() {
        return secid.toString();
    }

    public int hashCode() {
        return secid.hashCode();
    }

    public int compareTo(Security s) {
        return secid.compareTo(s.secid);
    }

    public boolean isIBM() {
        return secid.intValue() == 5334;
    }
    
    public static void main (String[] argv) {
        Security s1 = new Security(12345);
        Security s2 = new Security(12345);

        if ( s1 == s2 ) System.out.println("equals (=)");
        if ( s1.equals(s2) ) System.out.println("equals (equals)");
        System.out.println("compare2: " + s1.compareTo(s2) );
        System.out.println("hash1: " + s1.hashCode() + ", s2: " + s2.hashCode() );
    }
}
