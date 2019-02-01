package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.util.Time;
import ase.data.DbAttrType;
import ase.data.Exchange;
import ase.data.FactorLoadings;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.LoggerFactory;

public class CreditCalculator {
    private static final Logger log = LoggerFactory.getLogger(CreditCalculator.class.getName());
    
    //XXX for live data, the delay seems to be about 2 days. The backfilled data in the db had their born time already pushed forward by a day. So,
    //push forward an additional day
    public static final DbAttrType LONGTERM = new DbAttrType("SPLTICRM", "SPLTICRM", Time.fromDays(365), Time.fromDays(1));
    public static final DbAttrType SHORTTERM = new DbAttrType("SPSTICRM", "SPSTICRM", Time.fromDays(365), Time.fromDays(1));
    
    CalcAttrType A_RAT = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "CR_A");
    CalcAttrType B_RAT = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "CR_B");
    CalcAttrType C_RAT = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "CR_C");
    CalcAttrType REST_RAT = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "CR_THEREST");
    
    private final UnifiedDataSource uSource;
    private final int days_back;
    private final Exchange.Type primaryExch;
    
    public CreditCalculator(UnifiedDataSource uSource, int days_back, Exchange.Type primaryExch) {
        this.uSource = uSource;
        this.days_back = days_back;
        this.primaryExch = primaryExch;
    }
    
    private CalcAttrType credit2bucket(String cred) {
        if (cred.startsWith("A")) {
            return A_RAT;
        }
        else if (cred.startsWith("B")) {
            return B_RAT;
        }
        else {
            return REST_RAT;
        }
    }
    
    public Set<AttrType> calculate(FactorLoadings factorLoadings, long asof) throws Exception {
        log.info("Calculating Credit Attributes...");
        
        Set<AttrType> credGroups = new HashSet<AttrType>();
        credGroups.add(A_RAT);
        credGroups.add(B_RAT);
        credGroups.add(REST_RAT);
        Set<Security> secs = factorLoadings.getSecurities();
        
        long date1 = Time.today(Exchange.subtractTradingDays(asof, days_back + 1, primaryExch));
        
        Map<Security, NavigableMap<Long,Attribute>> cMap = uSource.attrSource.getRange(secs, LONGTERM, date1, asof);
        
        for (Security sec : cMap.keySet()) {
            NavigableMap<Long,Attribute> attrMap = cMap.get(sec);
            for ( Attribute attr : attrMap.values()) {
                factorLoadings.setFactor(sec, credit2bucket(attr.asString()), attr.date, 1.0);
            }
        }
        return credGroups;
    }
}
