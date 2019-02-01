package ase.data;

import gnu.trove.TIntObjectHashMap;

import java.util.EnumSet;

public enum Country {
	NA(0), US(1), CA(2);

	private static TIntObjectHashMap<Country> lookup = new TIntObjectHashMap<Country>();
	static {
		for (Country c : EnumSet.allOf(Country.class))
			lookup.put(c.getCode(), c);
	}
	private int code;

	private Country(int code) {
		this.code = code;
	}
	public int getCode() {
		return this.code;
	}
	public static Country getCountry(int code) {
		return lookup.get(code);
	}
}