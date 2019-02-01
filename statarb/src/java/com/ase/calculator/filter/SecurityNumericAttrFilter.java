package ase.calculator.filter;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.AttributeSource;
import ase.data.DbAttrType;
import ase.data.Security;

public class SecurityNumericAttrFilter extends SecurityFilter {

    private final AttrType attr;
    private final double min;;
    private final double max;
    private final AttributeSource attrSource;

    public SecurityNumericAttrFilter( AttrType attr, double min, double max, AttributeSource attrSource ) {
        this.attr = attr;
        this.min = min;
        this.max = max;
        this.attrSource = attrSource;
    }

    public Set<Security> filter( Set<Security> secs, long asof ) throws Exception {
        Map<Security,Attribute> attrs = attrSource.getAttrAsOf(secs, (DbAttrType) attr, asof);
        Set<Security> res = new HashSet<Security>(secs.size());
        for (Security sec : secs) {
            Attribute a = attrs.get(sec);
            if (a == null) {
                log.warning("Filtering " + sec.getSecId() + " on " + attr.name + " due to no attribute");
                continue;
            }

            double val = a.asDouble();
            if (val >= min && val <= max) {
                res.add(sec);
            }
        }
        log.info("Filtering stocks on " + attr.name + ", kept " + res.size() + "/" + secs.size());
        return res;
    }
}
