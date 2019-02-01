package ase.datacube;

import ase.data.AttrType;

public class Tuple {
	final AttrType[] dimensions;
	final String[] measures;
	final Object[] dimensionValues;
	final Double[] measureValues;

	public Tuple(AttrType[] dimensions, String[] measures) {
		assert dimensions != null;
		assert measures != null;
		this.dimensions = dimensions;
		this.measures = measures;
		this.dimensionValues = new Object[dimensions.length];
		this.measureValues = new Double[measures.length];
	}

	public void setDimension(int i, Object x) {
		dimensionValues[i] = x;
	}

	public void setDimensionArray(Object [] in) {
		assert in.length == dimensions.length;
		for(int ii = 0; ii < in.length; ii++) {
			setDimension(ii, in[ii]);
		}
	}
	
	public void setMeasure(int i, Double x) {
		measureValues[i] = x;
	}

	public void setMeasureArray(Double [] in) {
		assert in.length == measures.length;
		for(int ii = 0; ii < in.length; ii++) {
			setMeasure(ii, in[ii]);
		}
	}
	
	public Object getDimension(int i) {
		return dimensionValues[i];
	}

	public Double getMeasure(int i) {
		return measureValues[i];
	}

//	public static Tuple createEmptyTuple(Tuple t) {
//		Tuple n = new Tuple(t.dimensions, t.measures);
//		System.arraycopy(t.dimensionValues, 0, n.dimensionValues, 0, t.dimensionValues.length);
//		Arrays.fill(n.measureValues, 0);
//		return n;
//	}
//
//	private boolean checkAgainstTuple(Tuple t) {
//		return dimensions == t.dimensions && measures == t.measures;
//	}
//
//	public void add(Tuple t) {
//		assert checkAgainstTuple(t);
//
//		for (int i = 0; i < measureValues.length; i++) {
//			Double x = t.measureValues[i];
//			if (x != null)
//				this.measures[i] += x;
//		}
//	}
}
