package ase.datacube;

import gnu.trove.TDoubleArrayList;

import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;
import java.util.Vector;

import ase.data.AttrType.Type;
import ase.data.DistributionSummary;
import ase.util.Pair;
import ase.util.math.ASEMath;

public class BucketAggregator extends Aggregator {
	public enum BoundaryType {
		PERCENTILE, BREAKPOINT
	}

	protected final String attrName;
	protected final double[] points;
	protected final double[] breakPoints;
	protected final BoundaryType type;
	protected final int dimension;

	public BucketAggregator(Table table, int dimension, double[] points, BoundaryType type) {
		super(table);
		this.dimension = dimension;
		assert table.getDimensions()[dimension].datatype == Type.N;
		this.type = type;
		this.points = points;
		this.attrName = table.getDimensions()[dimension].name;
		switch (type) {
		case PERCENTILE:
			this.breakPoints = getPercentiles();
			break;
		case BREAKPOINT:
			this.breakPoints = points;
			break;
		default:
			this.breakPoints = null;
			break;
		}
	}

	protected double[] getPercentiles() {
		TDoubleArrayList ds = new TDoubleArrayList();

		for (Tuple t : table.getTuples()) {
			Double d = (Double) t.getDimension(dimension);
			if (d != null)
				ds.add(d);
		}

		return ASEMath.percentiles(ds.toNativeArray(), points);
	}

	public Vector<Pair<String, DistributionSummary[]>> aggregate() {
		Map<Object, TDoubleArrayList[]> aggs = new TreeMap<Object, TDoubleArrayList[]>();

		for (Tuple t : table.getTuples()) {
			Object d = t.getDimension(dimension);
			if (d == null)
				continue;

			for (int measure = 0; measure < t.measures.length; measure++) {
				Double m = t.getMeasure(measure);
				if (m == null || m.isNaN() || m.isInfinite())
					continue;
				Integer bucket = getBucket((Double) d);
				TDoubleArrayList values = getAndInitArray(aggs, bucket, measure, t.measures.length);
				values.add(m);
			}
		}

		Vector<Pair<String, DistributionSummary[]>> result = new Vector<Pair<String, DistributionSummary[]>>();
		for (Map.Entry<Object, TDoubleArrayList[]> e : aggs.entrySet()) {
			Integer bucket = (Integer) e.getKey();
			TDoubleArrayList[] allMeasureValues = e.getValue();
			DistributionSummary[] allAggregates = new DistributionSummary[allMeasureValues.length];

			for (int i = 0; i < allMeasureValues.length; i++) {
				TDoubleArrayList values = allMeasureValues[i];
				Pair<Double, Double> ms = ASEMath.meansig(values.toNativeArray());
				values.sort();
				Double low = Double.NaN;
				Double high = Double.NaN;
				Double median = Double.NaN;
				if (values.size() > 0) {
					low = values.getQuick(0);
					high = values.getQuick(values.size() - 1);
					median = values.getQuick(values.size() / 2);
				}

				DistributionSummary dist = new DistributionSummary(ms.first.floatValue(), ms.second.floatValue(), low.floatValue(), median.floatValue(),
						high.floatValue(), values.size());
				allAggregates[i] = dist;
			}
			result.add(new Pair<String, DistributionSummary[]>(getName(bucket), allAggregates));
		}
		return result;
	}

	protected int getBucket(double v) {
		int xx;
		for (xx = 0; xx < breakPoints.length && v > breakPoints[xx]; xx++)
			;
		return xx;
	}

	protected String getName(int bucket) {
		int xx = bucket;
		String suffix = "";
		if (xx == 0) {
			if (type == BoundaryType.PERCENTILE) {
				suffix = "[00_" + (int) points[xx] + "]";
			}
			else if (type == BoundaryType.BREAKPOINT) {
				suffix = "[-Inf_" + points[xx] + "]";
			}
		}
		else if (xx == breakPoints.length) {
			if (type == BoundaryType.PERCENTILE) {
				suffix = "[" + (int) points[xx - 1] + "_100]";
			}
			else if (type == BoundaryType.BREAKPOINT) {
				suffix = "[" + points[xx - 1] + "_+Inf]";
			}
		}
		else {
			if (type == BoundaryType.PERCENTILE) {
				suffix = "[" + (int) points[xx - 1] + "_" + (int) points[xx] + "]";
			}
			else if (type == BoundaryType.BREAKPOINT) {
				suffix = "[" + points[xx - 1] + "_" + points[xx] + "]";
			}
		}

		return attrName + "_" + suffix;
	}

	public String mapTupleToString(Tuple t) {
		Object d = t.getDimension(dimension);
		if (d == null)
			return null;
		Integer bucket = getBucket((Double) d);
		return getName(bucket);
	}
}
