package ase.data;

import ase.util.ASEFormatter;

public class DateAttribute extends Attribute {
    public long value;
    
    public DateAttribute (AttrType type, Security sec, long date, long value, long born) {
        super(type, sec, date, born);
        assert type.datatype == AttrType.Type.D;
        this.value = value;
    }

    public String toString () {
        return sec.getSecId() + "|" + type.name +"|"+type.datatype+"|"+ date + "|" + value + "|NA|" + born;
    }

    public String valueAsString() {
        return ASEFormatter.getInstance().format(value);
    }

    public String toReadableString () {
        ASEFormatter format = ASEFormatter.getInstance();
        return type.name+"|"+type.datatype+"|"+ format.format(date) + "|" + format.format(value) + "|" + format.format(born);
    }
}
