package ase.datacube;

import gnu.trove.TDoubleArrayList;

import java.util.Arrays;
import java.util.Map;
import java.util.Vector;

import ase.data.DistributionSummary;
import ase.util.Pair;

public abstract class Aggregator {
	protected final Table table;
	
	public Aggregator(Table table) {
		this.table=table;
	}
	
	public Vector<Pair<String, DistributionSummary[]>> aggregate() {
		return null;
	}
	
	public String mapTupleToString(Tuple t) {
		return null;
	}
	
	protected TDoubleArrayList getAndInitArray(Map<Object, TDoubleArrayList[]> aggs, Object o, int measure, int numMeasures) {
		TDoubleArrayList[] all = aggs.get(o);
		if (all == null) {
			all = new TDoubleArrayList[numMeasures];
			Arrays.fill(all, null);
			aggs.put(o, all);

			for (int ii = 0; ii < all.length; ii++) {
				all[ii] = new TDoubleArrayList();
			}
		}

		return all[measure];
	}
}
