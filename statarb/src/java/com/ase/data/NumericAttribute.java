package ase.data;


public class NumericAttribute extends Attribute {
	public double value;
	public Currency currency;

	public NumericAttribute(AttrType type, Security sec, long date, double value, Currency currency, long born) {
		super(type, sec, date, born);
		
		assert type.datatype == AttrType.Type.N;
		assert !Double.isNaN(value);
		
		this.value = value;
		this.currency = currency;
	}

	public NumericAttribute(AttrType type, Security sec, long date, double value, long born) {
		this(type, sec, date, value, Currency.NA, born);
	}

    public String toString() {
        return sec.getSecId() + "|" + type.name + "|" + type.datatype + "|" + date + "|" + value + "|" + currency + "|" + born;
    }

	public String valueAsString() {
		return String.valueOf(value);
	}

	public String toReadableString() {
		return type.name + "|" + type.datatype + "|" + df.format(date) + "|" + value + "|"+currency+"|" + df.format(born);
	}
}
