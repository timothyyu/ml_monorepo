package ase.timeseries;

import java.text.ParseException;
import java.util.Arrays;
import java.util.Collections;
import java.util.ListIterator;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.BarSource;
import ase.data.Exchange;
import ase.data.Exchange.Type;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class BarTimeSeries {
	protected static final Logger log = LoggerFactory.getLogger(BarTimeSeries.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	protected final Vector<Long> dates = new Vector<Long>();
	protected final Vector<Bar> bars = new Vector<Bar>();
	public final long period;

	public BarTimeSeries(Vector<Bar> bv, long[] close_tss, long period) {
		this(period);

		dates.ensureCapacity(close_tss.length);
		bars.ensureCapacity(close_tss.length);

		int ii = 0;
		for (int tt = 0; tt < close_tss.length; tt++) {
			while (ii < bv.size() && bv.get(ii).close_ts < close_tss[tt]) {
				ii++;
			}
			if (ii < bv.size() && bv.get(ii).close_ts == close_tss[tt]) {
				dates.add(close_tss[tt]);
				bars.add(bv.get(ii));
			}
			else {
				dates.add(close_tss[tt]);
				bars.add(null);
			}
		}
	}

	public BarTimeSeries(Vector<Bar> bars, long period) {
		this(period);
		for (Bar b : bars) {
			this.dates.add(b.close_ts);
			this.bars.add(b);
		}
	}

	public BarTimeSeries(long period) {
		this.period = period;
	}

	public int size() {
		return bars.size();
	}

	public Bar floor(long millis) {
		int index = Collections.binarySearch(dates, millis);
		index = (index < 0) ? -index - 2 : index;
		if (index < 0)
			return null;
		else
			return bars.get(index);
	}

	public Bar getLag(int lag) {
		assert lag >= 0;
		assert bars.size() > 0;

		if (lag >= bars.size()) {
			return null;
		}
		else {
			return bars.get(bars.size() - 1 - lag);
		}
	}

	protected Bar getFirstValidBar() {
		final int n = bars.size();

		for (int i = 0; i < n; i++) {
			Bar bb = bars.get(i);
			if (bb != null && bb.isValid()) {
				return bb;
			}
		}
		return null;
	}

	public double getLogrel() {
		if (bars == null || bars.size() == 0)
			return Double.NaN;
		Bar bar1 = getFirstValidBar();
		Bar bar2 = bars.lastElement();

		return TimeSeriesUtil.c2cLogrel(bar2, bar1);
	}

	public double getLogrel(int lag, int step) {
		Bar bar2 = getLag(lag);
		Bar bar1 = getLag(lag + step);
		return TimeSeriesUtil.c2cLogrel(bar2, bar1);
	}

	public Bar add(Bar b) {
		assert b != null;
		return this.add(b, b.close_ts);
	}

	public Bar add(Bar b, long millis) {
		// Get the last non-null bar
		Bar previousBar = null;
		final int n = bars.size();
		for (int i = n - 1; i >= 0; i--) {
			previousBar = bars.get(i);
			if (previousBar != null)
				break;
		}
		dates.add(millis);
		bars.add(b);
		return previousBar;
	}

	public Bar getLastBar() {
		if (bars.size() > 0) {
			return bars.lastElement();
		}
		return null;
	}

	public double[] getLogrelArray(int step, int lag) {
		int size = (int) Math.floor(bars.size() / step) - lag;
		double[] logrels = new double[size];
		for (int ii = bars.size() - 1 - lag; ii - step >= 0; ii -= step) {
			Bar dailyBar2 = bars.get(ii);
			Bar dailyBar1 = bars.get(ii - step);
			logrels[--size] = TimeSeriesUtil.c2cLogrel(dailyBar2, dailyBar1);
		}
		return logrels;
	}

	public double[] getLogrelArray(int step, int lag, int max) {
		int size = Math.min((int) Math.floor(bars.size() / step) - lag, max);
		double[] logrels = new double[size];
		for (int ii = bars.size() - 1 - lag; ii - step >= 0 && size > 0; ii -= step) {
			Bar dailyBar2 = bars.get(ii);
			Bar dailyBar1 = bars.get(ii - step);
			logrels[--size] = TimeSeriesUtil.c2cLogrel(dailyBar2, dailyBar1);
		}
		return logrels;
	}

	public double getAverageVolPrice(int days, int lag) {
		// returns NaN if there is a NaN in any day of the range
		final int end = bars.size() - lag;
		final int start = Math.max(0, end - days);
		double tot = 0;
		int cnt = 0;
		for (int ii = start; ii < end; ii++) {
			Bar b = bars.get(ii);
			if (b != null) {
				tot += b.close * b.volume;
				cnt++;
			}
		}
		if (cnt > 0) {
			return tot / cnt;
		}
		return Double.NaN;
	}

	// Deprecated so whoever wants to use it, revisits it
	@Deprecated
	public double[] closeArray() {
		double[] arr = new double[bars.size()];
		for (int i = 0; i < bars.size(); i++) {
			Bar b = bars.get(i);
			arr[i] = b == null ? null : b.close;
		}
		return arr;
	}

	// Deprecated so whoever wants to use it, revisits it
	@Deprecated
	public double[] close_tsArray() {
		double[] arr = new double[bars.size()];
		for (int i = 0; i < bars.size(); i++) {
			Bar b = bars.get(i);
			arr[i] = b == null ? null : bars.get(i).close_ts;
		}
		return arr;
	}

	public Bar aggregate() {
		return TimeSeriesUtil.aggregateBars(bars);
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
			str += df.format(dates.get(ii)) + "|" + (bars.get(ii) == null ? "NA" : bars.get(ii).toString()) + "\n";
		}
		return str;
	}

	public Vector<Bar> toVector() {
		return (Vector<Bar>) bars.clone();
	}

	public ListIterator<Bar> getBars() {
		return bars.listIterator();
	}

	private static void tests() throws ParseException {
		Exchange.Type exch = Type.NYSE;
		Security sec = new Security(5334);
		long date = df.parseShort("20110404").getTime();
		BarTimeSeries ts = new BarTimeSeries(0);
		Bar bar1 = new Bar(sec, Exchange.openTime(date, exch), Exchange.closeTime(date, exch), 2, 3, 1, 2, 100);
		Bar bar2 = new Bar(sec, Exchange.openTime(date + Time.MILLIS_PER_DAY, exch), Exchange.closeTime(date + Time.MILLIS_PER_DAY, exch), 5, 4, 7, 6, 200);
		Bar bar3 = null;

		System.out.println(ts.floor(Exchange.closeTime(date, exch)) + " Expected null");
		ts.add(bar1);
		System.out.println(ts.floor(Exchange.closeTime(date, exch)) + " Expected " + bar1);
		System.out.println(ts.floor(Exchange.closeTime(date, exch) + 1) + " Expected " + bar1);
		System.out.println(ts.floor(Exchange.closeTime(date, exch) - 1) + " Expected null");
		System.out.println(ts.getLogrel() + " Expected 0.0");
		ts.add(bar2);
		System.out.println(ts.floor(Exchange.closeTime(date + Time.MILLIS_PER_DAY, exch)) + " Expected " + bar2);
		System.out.println(ts.floor(Exchange.closeTime(date + Time.MILLIS_PER_DAY, exch) + 1) + " Expected " + bar2);
		System.out.println(ts.floor(Exchange.closeTime(date + Time.MILLIS_PER_DAY, exch) - 1) + " Expected " + bar1);
		System.out.println(ts.floor(Exchange.closeTime(date, exch)) + " Expected " + bar1);
		System.out.println(ts.floor(Exchange.closeTime(date, exch) - 1) + " Expected null");
		System.out.println("Logrel array: " + Arrays.toString(ts.getLogrelArray(1, 0)));
		System.out.println(ts.getLag(0) + " Expected " + bar2);
		System.out.println(ts.getLag(1) + " Expected " + bar1);
		System.out.println(ts.getLag(2) + " Expected null");
		System.out.println(ts.getLogrel() + " Expected " + Math.log(bar2.close / bar1.close));
		System.out.println(ts.getAverageVolPrice(1, 0) + " Expected " + bar2.notional());
		System.out.println(ts.getAverageVolPrice(2, 0) + " Expected " + (bar1.notional() + bar2.notional()) / 2);
		System.out.println(ts.getAverageVolPrice(1, 1) + " Expected " + bar1.notional());
		System.out.println(ts.getAverageVolPrice(500, 1) + " Expected " + bar1.notional());
		ts.add(bar3, Exchange.closeTime(Exchange.addTradingDays(date, 2, exch), exch));
		System.out.println(ts.getAverageVolPrice(3, 0) + " Expected " + (bar1.notional() + bar2.notional()) / 2);
		System.out.println("Logrel array: " + Arrays.toString(ts.getLogrelArray(1, 0)));
	}

	public static void main(String[] args) throws ParseException {
		tests();
	}
}
