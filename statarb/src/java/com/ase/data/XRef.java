package ase.data;

import gnu.trove.TIntObjectHashMap;

import java.util.EnumSet;

public enum XRef {
    CUSIP(1), TIC(2), SEDOL(3), ISIN(4), BARRAID(5), RIC(6), DISPLAYRIC(7), RKD(8);

    private static TIntObjectHashMap<XRef> lookup = new TIntObjectHashMap<XRef>();
    static {
        for (XRef c : EnumSet.allOf(XRef.class)) {
            lookup.put(c.getCode(), c);
        }
    }
    private int code;

    private XRef(int code) {
        this.code = code;
    }

    public int getCode() {
        return this.code;
    }

    public static XRef getXRef(int code) {
        return lookup.get(code);
    }
}
