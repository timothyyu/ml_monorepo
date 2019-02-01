package ase.data;

public class AttrType implements Comparable<AttrType> {
    public static enum Type { N, S, D, P };
    
    public final String name;
    public Type datatype;

    public AttrType(String name, Type datatype) {
        this.name = name;
        this.datatype = datatype;        
    }
    
    public AttrType(String name) {
        this(name, null);
    }
    
    public String toString() {
        return name;
    }
    
    public boolean isSubType(AttrType attr) {
        return name.startsWith(attr.name);
    }
    
    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((name == null) ? 0 : name.hashCode());
        return result;
    }

    @Override
    //ignores datatype!!!
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if ( !(obj instanceof AttrType) )
            return false;   
        AttrType other = (AttrType) obj;
        if (name == null) {
            if (other.name != null)
                return false;
        } else if (!name.equals(other.name))
            return false;
        return true;
    }

    public int compareTo(AttrType o) {
        return name.compareTo(o.name);
    }
}
