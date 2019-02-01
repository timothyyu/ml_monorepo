package ase.calculator.filter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.AttributeSource;
import ase.data.DbAttrType;
import ase.data.NumericAttribute;
import ase.data.Security;

public class RankingFilter extends SecurityFilter {
    //TODO: implement high vs low
    public enum Type {HIGH, LOW};

    private final AttributeSource attrSource;
    private final Type type;
    private final AttrType attrType; 
    private final int size; 
    
    public RankingFilter(AttributeSource attrSource, AttrType attrType, Type type, int size) {
        this.attrSource = attrSource;
        this.attrType = attrType;
        this.type = type;
        this.size = size;
    }
    
    @Override
    public Set<Security> filter(Set<Security> secs, long asof) throws Exception {
        Set<Security> res = new HashSet<Security>(secs.size());
        Map<Security,Attribute> capMap = attrSource.getAttrAsOf(secs, (DbAttrType)attrType, asof);
        ArrayList<Attribute> stocks = new ArrayList<Attribute>(capMap.values());
        Collections.sort(stocks, new Comparator<Attribute>() { 
                                            public int compare( Attribute a, Attribute b ) {
                                                return Double.compare(((NumericAttribute)b).value, ((NumericAttribute)a).value); 
                                            }
                                          });
        int cnt = 0;
        for( Attribute attr : stocks) {
            if (++cnt > size) break;
            res.add(attr.sec);
        }
        return res;
    }

}
