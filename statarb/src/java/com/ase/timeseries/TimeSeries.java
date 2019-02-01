package ase.timeseries;

import java.util.Collections;
import java.util.Vector;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class TimeSeries<T> {
	protected static final Logger log = LoggerFactory.getLogger(TimeSeries.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	protected final Vector<Long> dates;
	protected final Vector<T> data;
	
	public int size() {
		return data.size();
	}
	
	public boolean isEmpty() {
		return data.isEmpty();
	}
	
	public TimeSeries() {
		dates = new Vector<Long>();
		data = new Vector<T>();
	}
	
	public TimeSeries(int initSize) {
		dates = new Vector<Long>(initSize);
		data = new Vector<T>(initSize);
	}
	
	// <=millis
	public T floor(long millis) {
		int index = Collections.binarySearch(dates, millis);
		index = (index < 0) ? -index - 2 : index;
		if (index < 0)
			return null;
		else
			return data.get(index);
	}
	
	public Pair<Long, T> floorEntry(long millis) {
		int index = Collections.binarySearch(dates, millis);
		index = (index < 0) ? -index - 2 : index;
		if (index < 0)
			return null;
		else
			return new Pair<Long, T>(dates.get(index), data.get(index));
	}
	
	public T getLag(int lag) {
		assert lag >= 0;
		assert data.size() > 0;

		if (lag >= data.size()) {
			return null;
		}
		else {
			return data.get(data.size() - 1 - lag);
		}
	}
	
	public void add(T b, long millis) {
		dates.add(millis);
		data.add(b);
	}
	
	public T getLastBar() {
	    if (data.size() > 0) {
	        return data.lastElement();
	    }
	    return null;
	}
		
	public String printDateRange() {
		return df.format(dates.firstElement()) + " - " + df.format(dates.lastElement());
	}

	public void print() {
	    System.out.println(toString());
	}

	public String toString() {
	    String str = "";
	    for (int ii = 0; ii < dates.size(); ii++) {
	        str += df.format(dates.get(ii)) + "|" + (data.get(ii) == null ? "NA" : data.get(ii).toString()) + "\n";
	    }
	    return str;
	}
}
