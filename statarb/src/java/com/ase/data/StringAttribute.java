package ase.data;

import ase.util.ASEFormatter;

public class StringAttribute extends Attribute {
    public String value;
    
    public StringAttribute (AttrType type, Security sec, long date, String value, long born) {
        super(type, sec, date, born);
        assert type.datatype == AttrType.Type.S;
        this.value = value;
    }

    public String toString () {
        return sec.getSecId()+"|"+type.name+"|"+type.datatype + "|"+date + "|" + value + "|NA|" + born;
    }

    public String valueAsString() {
        return value;
    }

    public String toReadableString () {
        ASEFormatter format = ASEFormatter.getInstance();
        return type.name+"|"+type.datatype+"|"+format.format(date) + "|" + value + "|" + format.format(born);
    }

}
