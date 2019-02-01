package ase.calculator.filter;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.AttributeSource;
import ase.data.DbAttrType;
import ase.data.Security;

public class SecurityStringAttrFilter extends SecurityFilter {

    private final AttrType attr;
    private final String constval;
    private final boolean equals;
    private final AttributeSource attrSource;

    public SecurityStringAttrFilter( AttrType attr, String constval, boolean equals, AttributeSource attrSource ) {
        this.attr = attr;
        this.constval = constval;
        this.equals = equals;

        this.attrSource = attrSource;
    }

    public Set<Security> filter( Set<Security> secs, long asof ) throws Exception {
        Map<Security,Attribute> attrs = attrSource.getAttrAsOf(secs, (DbAttrType) attr, asof);
        Set<Security> res = new HashSet<Security>(secs.size());
        for ( Security sec : secs ) {
            Attribute a = attrs.get(sec);
            if (a == null) continue;

            String val = a.asString();
            if ( (equals && constval.equals(val)) || (!equals && !constval.equals(val)) ) {
                res.add(sec);
            }
        }
        log.info("Filtering stocks on " + attr.name + ", kept " + res.size() + "/" + secs.size());
        return res;
    }

}

