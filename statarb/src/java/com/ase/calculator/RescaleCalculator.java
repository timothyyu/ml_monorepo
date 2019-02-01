package ase.calculator;

import java.util.Map;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Security;
import ase.util.LoggerFactory;

public class RescaleCalculator {
    private static final Logger log = LoggerFactory.getLogger(RescaleCalculator.class.getName());

    public enum Mode { INV, TANH, MINUS, MULT };

    public RescaleCalculator() {
    }

    public static AttrType calculate(CalcResults cr, AttrType attr, AttrType adjattr, Mode mode) {
        AttrType resattr = getResName(attr, adjattr);

        Map<Security,Attribute> attrs = cr.getResult(attr);
        Map<Security,Attribute> adjattrs = cr.getResult(adjattr);

        if (attrs == null) {
            log.severe("can't adjust " + attr + " by " + adjattr+ " because no attrs found");
            return null;
        }
        if (adjattrs == null) {
            log.severe("can't adjust " + attr + " by " + adjattr + " because no adjustment attrs found");
            return null;
        }
        log.info("RescaleCalculator adjusting " + mode + " " + attr + " by " + adjattr + ".  " + attrs.size() + " / " + adjattrs.size());

        int cnt = 0;
        
        //XXX do i really want defaults on adjustments instead of setting NaN if there are no adjattrs 
        for (Map.Entry<Security,Attribute> ent : attrs.entrySet()) {
            double val = Double.NaN;
            Security sec = ent.getKey();
            switch(mode) {
            case MINUS:
                val = ent.getValue().asDouble() - (adjattrs.containsKey(sec) ? adjattrs.get(sec).asDouble() : 0);
                break;
            case INV:
                val = ent.getValue().asDouble() / (adjattrs.containsKey(sec) ? adjattrs.get(sec).asDouble() : 1);
                break;
            case TANH:
                ///XXX: does not appear to normalize data before tanh adjustment??
                val = ent.getValue().asDouble() * (adjattrs.containsKey(sec) ? Math.tanh(adjattrs.get(sec).asDouble()) : 1);
                break;
            case MULT:
                val = ent.getValue().asDouble() * (adjattrs.containsKey(sec) ? adjattrs.get(sec).asDouble() : 1);
                break;
            }
            cr.add(sec, resattr, ent.getValue().date, val);
            cnt++;
        }
        log.info("RescaleCalculator on " + attr + " affected " + cnt + " / " + attrs.size() );
        return resattr;
    }

    public static AttrType getResName(AttrType attr, AttrType adjattr) {
        if (BarraCalculator.B_BETA.equals(adjattr)) {
            return new CalcAttrType(attr.name + "_BAdj", attr.datatype);
        }
        else if (adjattr.isSubType(DailyPriceCalculator.RV)) {
            return new CalcAttrType(attr.name + "_VAdj", attr.datatype);
        }
        else if (adjattr.name.startsWith("nofly")) {
            return new CalcAttrType(attr.name + "_FlyAdj", attr.datatype);
        }
        log.warning("Rescaling by unexpected attribute: " + adjattr);
        return new CalcAttrType(attr.name+"_"+adjattr.name+"Adj", attr.datatype);
    }
    
}
