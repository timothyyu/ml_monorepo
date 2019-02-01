package ase.calculator;

import java.util.Map;
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

public class DecayCalculator {
    private static final Logger log = LoggerFactory.getLogger(DecayCalculator.class.getName());
    private static final ASEFormatter df = ASEFormatter.getInstance();

    public static AttrType calculate(CalcResults cr, AttrType attrType, long asof, long halflife, int maxhalflives) {
        AttrType retType = getResName(attrType, halflife);
        log.info("Calculating " + attrType.name + " into " + retType.name);
        
        Map<Security, Attribute> unadjAttrs = cr.getResult(attrType);
        if ( unadjAttrs == null ) {
            log.severe("can't decay " + attrType + ".  it was never calculated.");
            return null;
        }
        int cnt = 0;
        for (Map.Entry<Security, Attribute> ent : unadjAttrs.entrySet()) {
            Security sec = ent.getKey();
            Attribute attr = ent.getValue();
            if (attr.date > asof) {
                log.severe("unadj.date > calcdate " + attr);
            }
            double halflives = ((double)Exchange.tradingTimeBetween(attr.date, asof, sec.primaryExchange))/halflife;
            if (halflives > maxhalflives) {
//                log.finest("Skipping " + attr + " because it is too old");
                continue;
            }
            if (halflives < 0) {
                log.severe("halflife < 0 " + attr);
            }
            double decayed = attr.asDouble() * Math.pow(2, -halflives);
            cr.add(sec, retType, attr.date, decayed);
            cnt++;
        }
        log.info("DecayCalculator on " + attrType + " affected " + cnt + " / " + unadjAttrs.size() + " creating " + retType.name );
        return retType;
    }
 
    public static AttrType getResName(AttrType attr, long halflife) {
        String halflifestr = df.formatDecay(new Double((double)halflife/Time.fromDays(1)));
        return new CalcAttrType(attr.name + "_D-" + halflifestr, attr.datatype);
    }
}
