package ase.data;

import java.util.Comparator;

import ase.util.ASEFormatter;
import ase.util.INumber;

public abstract class Attribute implements Comparable<Attribute>, INumber {
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public final Security sec;
	public final AttrType type;
	public final long date;
	public final long born;

	public Attribute(AttrType type, Security sec, long date, long born) {
		assert date >= 0;
		assert born >= 0;

		this.type = type;
		this.sec = sec;
		this.date = date;
		this.born = born;
	}

	public abstract String valueAsString();

	public double asDouble() {
		return ((NumericAttribute) this).value;
	}

	public String asString() {
		return ((StringAttribute) this).value;
	}

	public long asDate() {
		return ((DateAttribute) this).value;
	}

	public boolean equals(Object o) {
		if (o instanceof Attribute) {
			Attribute a2 = (Attribute) o;
			if (this.type.equals(a2.type) && this.date == a2.date && this.valueAsString().equals(a2.valueAsString()))
				return true;
		}
		return false;
	}

	public int compareTo(Attribute a) {
		if (this.date > a.date)
			return 1;
		else if (this.date < a.date)
			return -1;
		else
			return -0;
	}

	public int hashCode() {
		return toString().hashCode();
	}

	public String toString() {
		return type + "|" + df.format(date);
	}
	
	public static Comparator<Attribute> getValueComparator() {
	    return new Comparator<Attribute>() { public int compare( Attribute a, Attribute b) { return (int)Math.signum(a.asDouble() - b.asDouble()); } };
	}

	public static Attribute restore(String str) throws Exception {
		String[] fields = str.split("\\|");
		if (fields.length < 7) {
		    throw new RuntimeException("Bad attribute line: " + str);
		}
		
		if (AttrType.Type.N.name().equals(fields[2])) {
			return new NumericAttribute(new AttrType(fields[1], AttrType.Type.N), new Security(Integer.parseInt(fields[0])), Long.parseLong(fields[3]),
					Double.parseDouble(fields[4]), Currency.valueOf(fields[5]), Long.parseLong(fields[6]));
		}
		else if (AttrType.Type.S.name().equals(fields[2])) {
			return new StringAttribute(new AttrType(fields[1], AttrType.Type.S), new Security(Integer.parseInt(fields[0])), Long.parseLong(fields[3]),
					fields[4], Long.parseLong(fields[6]));
		}
		else if (AttrType.Type.D.name().equals(fields[2])) {
			return new DateAttribute(new AttrType(fields[1], AttrType.Type.D), new Security(Integer.parseInt(fields[0])), Long.parseLong(fields[3]),
					Long.parseLong(fields[4]), Long.parseLong(fields[6]));
		}

		throw new Exception("Unknown attribute type: " + str);
	}
}
