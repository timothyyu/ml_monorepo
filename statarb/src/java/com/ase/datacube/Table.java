package ase.datacube;

import java.util.List;
import java.util.Vector;

import ase.data.AttrType;

public class Table {
	private final AttrType[] dimensions;
	private final String[] measures;
	private final Vector<Tuple> tuples = new Vector<Tuple>();

	public Table(AttrType[] dimensions, String[] measures) {
		this.dimensions = dimensions;
		this.measures = measures;
	}

	public Tuple createTuple() {
		return new Tuple(dimensions, measures);
	}

	public void addTuple(Tuple t) {
		tuples.add(t);
	}
	
	public List<Tuple> getTuples() {
		return tuples;
	}
	
	public AttrType[] getDimensions() {
		return dimensions;
	}
	
//	protected void sort() {
//		Collections.sort(tuples, new TupleComparator());
//	}
//	
//	public Table aggregate(){
//		sort();
//		Table table=new Table(dimensions, measures);
//		TupleComparator tc=new TupleComparator();
//		
//		int start=0;
//		int end=0;
//		int n=tuples.size();
//		
//		while (start<n) {
//			while (end<n && tc.compare(tuples.get(start), tuples.get(end))==0) {
//				end++;
//			}
//			
//			Tuple agg=Tuple.createEmptyTuple(tuples.get(start));
//			for (int ii=start; ii<end; ii++) {
//				agg.add(tuples.get(ii));
//			}
//			table.addTuple(agg);
//			
//			start=end;
//			
//		}
//		
//		return table;
//	}
}
