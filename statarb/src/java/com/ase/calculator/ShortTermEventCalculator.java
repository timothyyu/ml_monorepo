package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class ShortTermEventCalculator {
    private static final Logger log = LoggerFactory.getLogger(ShortTermEventCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    public AttrType calculate(CalcResults cr, AttrType attrType, long asof, int cutoffInHours) {
    	return calculate(cr, cr, attrType, asof, cutoffInHours);
    }
    
    public AttrType calculate(CalcResults cr1, CalcResults cr2, AttrType attrType, long asof, int cutoffInHours) {
    	assert cutoffInHours > 0;
        AttrType retType = getResName(attrType, cutoffInHours);
        log.info("Calculating " + attrType.name + " into " + retType.name);
        
        Map<Security, Attribute> unadjAttrs = cr1.getResult(attrType);
        if ( unadjAttrs == null ) {
            log.severe("can't cutoff " + attrType + ".  it was never calculated.");
            return null;
        }
        int cnt = 0;
        for (Map.Entry<Security, Attribute> ent : unadjAttrs.entrySet()) {
            Security sec = ent.getKey();
            Attribute attr = ent.getValue();
            if (attr.date > asof) {
                log.severe("unadj.date > calcdate " + attr);
                continue;
            }
            long adjtime = Math.max(Exchange.openTime(attr.date, sec.primaryExchange),attr.date);
            if ( adjtime > asof ) continue;
            long distance = Exchange.tradingTimeBetween(adjtime, asof, sec.primaryExchange);
            if (distance > cutoffInHours * Time.MILLIS_PER_HOUR)
            	continue;
            
            cr2.add(sec, retType, attr.date, attr.asDouble());
            cnt++;
        }
        log.info("ShortTermCalculator on " + attrType + " let through " + cnt + " / " + unadjAttrs.size() + " creating " + retType.name );
        return retType;
    }
    
    public Set<AttrType> calculate(CalcResults cr, long asof, int cutoffInHours) {
    	return calculate(cr, cr, asof, cutoffInHours);
    }
    
    public Set<AttrType> calculate(CalcResults cr1, CalcResults cr2, long asof, int cutoffInHours) {
    	Set<AttrType> ret = new HashSet<AttrType>();
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_CE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_DE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_CE_Diff_BS"), asof, cutoffInHours));
        ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_DE_Diff_BS"), asof, cutoffInHours));
        
        //ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffC_BS_MA-BINDNAME1"), asof, cutoffInHours));
        //ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffD_BS_MA-BINDNAME1"), asof, cutoffInHours));
        ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffC_BS"), asof, cutoffInHours));
        ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffD_BS"), asof, cutoffInHours));

    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_CE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_DE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_CE_Diff_BS"), asof, cutoffInHours));
        ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_DE_Diff_BS"), asof, cutoffInHours));
        
    	//ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_CE_2P_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	//ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_DE_2P_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	//ret.add(calculate(cr1, cr2, new CalcAttrType("recentEarnings_T-C_BS"), asof, cutoffInHours));
    	return ret;
    }
    
    public Set<AttrType> calculate2(CalcResults cr1, CalcResults cr2, long asof, int cutoffInHours) {
    	Set<AttrType> ret = new HashSet<AttrType>();
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_CE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_DE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffC_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffD_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_CE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_DE_Diff_BS_MA-BINDNAME1"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("recentEarnings_T-C_BS"), asof, cutoffInHours));
    	
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_CE_Diff_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("EPS_Q_DE_Diff_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffC_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("ratDiffD_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_CE_Diff_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("TARGETPRICE_DE_Diff_BS"), asof, cutoffInHours));
    	ret.add(calculate(cr1, cr2, new CalcAttrType("recentEarnings_T-C_BS"), asof, cutoffInHours));
    	return ret;
    }
 
    public static AttrType getResName(AttrType attr, int cutoff) {
        return new CalcAttrType(attr.name + "_ST-" + cutoff, attr.datatype);
    }
}
