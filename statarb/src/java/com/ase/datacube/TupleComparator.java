package ase.datacube;

import java.util.Comparator;

public class TupleComparator implements Comparator<Tuple> {

	@Override
	public int compare(Tuple o1, Tuple o2) {
		assert o1!=null;
		assert o2!=null;
		assert o1.dimensions==o2.dimensions;
		
		int comp=0;
		int pos=0;
		
		while (pos<o1.dimensions.length) {
			Object v1=o1.dimensionValues[pos];
			Object v2=o2.dimensionValues[pos];
			
			if (v1==null && v2==null)
				continue;
			else if (v1==null)
				return -1;
			else if (v2==null)
				return 1;
			
			switch (o1.dimensions[pos].datatype){
			case N:
				Double d1=(Double)v1;
				Double d2=(Double)v2;
				comp=Double.compare(d1, d2);
				if (comp!=0)
					return comp;
				break;
			case D:
				Long l1=(Long)v1;
				Long l2=(Long)v2;
				comp=(int)Math.signum(l1-l2);
				if (comp!=0)
					return comp;
				break;
			case S:
				String s1=(String)v1;
				String s2=(String)v2;
				comp=s1.compareTo(s2);
				if (comp!=0)
					return comp;
				break;
			default:
				throw new RuntimeException("This should have been unreachable");
			}
			
			pos++;
		}
		
		return 0;
	}
}
