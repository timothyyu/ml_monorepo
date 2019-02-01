package ase.data;

import ase.util.ASEFormatter;

public class ExecPosition {
    private static final ASEFormatter df = ASEFormatter.getInstance();

    private final int position;
    private final long ts;

    public ExecPosition(int position, long ts) {
        assert ts > 0;

        this.position = position;
        this.ts = ts;
    }

    public int getPosition() {
        return position;
    }

    public long getTs() {
        return ts;
    }

    public String toString() {
        return "P|" + position + "|" + df.format(ts);
    }
    
    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        long temp = Double.doubleToLongBits(position);
        result = prime * result + (int) (temp ^ (temp >>> 32));
        result = prime * result + (int) (ts ^ (ts >>> 32));
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null) return false;
        if (getClass() != obj.getClass()) return false;
        ExecPosition other = (ExecPosition) obj;
        if (position != other.position) return false;        
        if (ts != other.ts) return false;
        return true;
    }
}