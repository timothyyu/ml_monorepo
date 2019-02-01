package ase.datacube;

import gnu.trove.TDoubleArrayList;

import java.util.Map;
import java.util.TreeMap;
import java.util.Vector;

import ase.data.DistributionSummary;
import ase.util.Pair;
import ase.util.math.ASEMath;

public class MultiDimAggregator extends Aggregator {

	protected final Aggregator[] aggregators;
	protected final StringBuilder sb;
	protected final String separator = " && ";
	
	public MultiDimAggregator(Table table, Aggregator[] aggregators) {
		super(table);
		assert aggregators != null && aggregators.length > 0;
		this.aggregators = aggregators;
		this.sb = new StringBuilder();
	}
	
	public String mapTupleToString(Tuple t) { 
		sb.setLength(0);
		for (Aggregator agg : aggregators) {
			String m = agg.mapTupleToString(t);
			if (m == null)
				return null;
			sb.append(m);
			sb.append(separator);
		}
		
		return sb.substring(0, sb.length() - separator.length());
	}
	
	public Vector<Pair<String, DistributionSummary[]>> aggregate() {
		Map<Object, TDoubleArrayList[]> aggs = new TreeMap<Object, TDoubleArrayList[]>();

		for (Tuple t : table.getTuples()) {
			String d = mapTupleToString(t);
			if (d == null)
				continue;

			for (int measure = 0; measure < t.measures.length; measure++) {
				Double m = t.getMeasure(measure);
				if (m == null || m.isNaN() || m.isInfinite())
					continue;
				TDoubleArrayList values = getAndInitArray(aggs, d, measure, t.measures.length);
				values.add(m);
			}
		}

		Vector<Pair<String, DistributionSummary[]>> result = new Vector<Pair<String, DistributionSummary[]>>();
		for (Map.Entry<Object, TDoubleArrayList[]> e : aggs.entrySet()) {
			Object o = e.getKey();
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
			result.add(new Pair<String, DistributionSummary[]>(o.toString(), allAggregates));
		}
		return result;
	}
}
