package ase.timeseries;

import java.util.Arrays;

import ase.data.Price;
import ase.data.Security;
import ase.util.ASEFormatter;

public class Bar implements Comparable<Bar>, Price, TimestampedDatum {
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public enum BarExtraType {
		QHIGH, QLOW, VWAP, TRADES;
	}
	
	public final Security sec;
	public final long open_ts;
	public final long close_ts;

	public final double open;
	public final double high;
	public final double low;
	public final double close;
	public final double volume;

	public int version;
	public Double[] extras;

	public Bar(Security sec, long open_ts, long close_ts, double open, double high, double low, double close, double volume) {
		assert close_ts > open_ts;
		assert !Double.isNaN(volume);

		this.sec = sec;
		this.open_ts = open_ts;
		this.close_ts = close_ts;
		this.open = open;
		this.high = high;
		this.low = low;
		this.close = close;
		this.volume = volume;

		this.version = 1;
		this.extras = null;
	}

	public Bar(Bar b) {
		this(b.sec, b.open_ts, b.close_ts, b.open, b.high, b.low, b.close, b.volume);
	}

	public String toString() {
		return "" + sec + "|" + open_ts + "|" + close_ts + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume;
	}

	public String toHRString() {
		return "" + sec + "|" + df.format(open_ts) + "|" + df.format(close_ts) + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume;
	}
	
	public String extrasToString() {
		return Arrays.toString(extras);
	}

	public void setExtras(Double[] extras) {
		this.extras = extras;
	}
	
	public Double getExtra(BarExtraType etype) {
		if (this.extras == null || etype.ordinal()>=this.extras.length)
			return null;
		else
			return this.extras[etype.ordinal()];
	}
	
	public double notional() {
		return close * volume;
	}

	public double getPrice() {
		return close;
	}

	public long getTs() {
		return close_ts;
	}

	public boolean isValid() {
		return sec != null && open_ts > 0 && close_ts > 0 && open > 0 && high > 0 && low > 0 && close > 0 && volume >= 0 && low <= high;
	}

	public int compareTo(Bar b) {
		if (this.close_ts > b.close_ts)
			return 1;
		else if (this.close_ts < b.close_ts)
			return -1;
		else
			return 0;
	}
}
