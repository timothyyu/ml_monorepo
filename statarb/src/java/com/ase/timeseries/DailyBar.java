package ase.timeseries;

import java.util.Comparator;

import ase.data.Exchange;
import ase.data.Security;
import ase.util.Time;

public class DailyBar extends Bar {

	public final double div;
	public final double split;
	public double adjFactor;
	public double accDividends;

	public DailyBar(Security sec, long date, double open, double high, double low, double close, double volume, double div, double split) {
		this(sec, date, open, high, low, close, volume, div, split, sec.primaryExchange);
	}

	public DailyBar(Security sec, long date, double open, double high, double low, double close, double volume, double div, double split, Exchange.Type exch) {
		super(sec, Exchange.openTime(date, exch), Exchange.closeTime(date, exch), open, high, low, close, volume);

		this.div = div;
		this.split = split;
		this.adjFactor = 1;
		this.accDividends = 0;
	}

	public DailyBar(Bar bar, double div, double split) {
		super(bar);

		this.div = div;
		this.split = split;
		this.adjFactor = 1;
		this.accDividends = 0;
	}

	public boolean isValid() {
	    return super.isValid() && low > (.01 * close) && high < (100.0 * close);  
	}
	
	public String toString() {
		return "" + sec + "|" + open_ts + "|" + close_ts + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume + "|" + split + "|" + div + "|"
				+ adjFactor + "|" + accDividends;
	}

	public String toHRString() {
		return "" + sec + "|" + df.format(open_ts) + "|" + df.format(close_ts) + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume + "|" + split
				+ "|" + div + "|" + adjFactor + "|" + accDividends;
	}

	public static Comparator<DailyBar> getDayBasedComparator() {
		return new Comparator<DailyBar>() {
			public int compare(DailyBar o1, DailyBar o2) {
				return (int) Math.signum(Time.midnight(o1.close_ts) - Time.midnight(o2.close_ts));
			}
		};
	}
}
