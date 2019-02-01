package ase.data;

import gnu.trove.TIntObjectHashMap;

import java.util.EnumSet;

public enum Currency {
	NA(0), USD(1), CAD(2), GBP(8), EUR(9), JPY(14);

	private static TIntObjectHashMap<Currency> lookup = new TIntObjectHashMap<Currency>();
	static {
		for (Currency c : EnumSet.allOf(Currency.class))
			lookup.put(c.getCode(), c);
	}
	private int code;

	private Currency(int code) {
		this.code = code;
	}

	public int getCode() {
		return this.code;
	}

	public static Currency getCurrency(int code) {
		return lookup.get(code);
	}
}
