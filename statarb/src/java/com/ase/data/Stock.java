package ase.data;

public final class Stock extends Security {
    private final int coid;
    private final String issueid;
    public final Currency curr;
    public final Country country;
    public final boolean alive;

    public Stock (int secid, int coid, String issueid, Exchange.Type exch, Country country, Currency curr, boolean alive) {
        super(secid, exch);
        this.coid = coid;
        this.issueid = issueid;
        this.country = country;
        this.curr = curr;
        this.alive = alive;
    }

    public static Stock restore(String[] fields) {
        return new Stock( Integer.parseInt(fields[0]), 
                Integer.parseInt(fields[2]), 
                fields[3], Exchange.Type.valueOf(fields[6]),
                Country.valueOf(fields[4]),
                Currency.valueOf(fields[5]), fields[7].equals("A") );
    }
    
    public String toString() {
        return super.toString() + "|" + Type.STOCK + "|" + coid + "|" + issueid + "|" + country + "|" + curr + "|" + primaryExchange+ "|" + (alive ? "A" : "D");
    }
}
