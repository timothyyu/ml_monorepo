package ase.data;

import java.util.Vector;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class EstimateSeries<T> {
	private static final Logger log = LoggerFactory.getLogger(EstimateSeries.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public final Security sec;
	public final AttrType type;
	public final long perioddate;
	public final int brokerid;

	// ascending time series
	private Vector<Estimate<T>> series;

	public EstimateSeries(Security sec, AttrType type, long perioddate, int brokerid) {
		super();
		this.sec = sec;
		this.type = type;
		this.perioddate = perioddate;
		this.brokerid = brokerid;
		this.series = null;
	}

	public int size() {
		if (series == null)
			return 0;
		return series.size();
	}

	public Estimate<T> addEstimate(T value, Currency currency, long orig, long born) {
		if (series == null) {
			series = new Vector<Estimate<T>>();
		}
		Estimate<T> ei = new Estimate<T>(value, currency, orig, born);
		series.add(ei);
		return ei;
	}

	public Estimate<T> addEstimate(Estimate<T> estimate) {
		if (series == null) {
			series = new Vector<Estimate<T>>();
		}
		series.add(estimate);
		return estimate;
	}

	public void removeLatestEstimate() {
		if (series == null || series.isEmpty()) {
			return;
		}
		series.remove(series.size() - 1);
	}

	public Estimate<T> getLatestEstimate() {
		return getLaggedEstimate(0);
	}

	public Estimate<T> getLaggedEstimate(int lag) {
		if (series == null)
			return null;
		if (series.size() <= lag)
			return null;
		return series.get(series.size() - 1 - lag);
	}

	public Estimate<T> getLaggedDailyEstimate(int lag) {
		if (series == null)
			return null;
		if (series.size() <= lag)
			return null;

		long lastdate = Long.MAX_VALUE;
		for (int ii = series.size() - 1; ii > -1; ii--) {
			Estimate<T> est = series.get(ii);
			if (Time.today(est.orig) < Time.today(lastdate)) {
				if (lag-- == 0)
					return est;
				lastdate = est.orig;
			}
		}
		return null;
	}

	public Estimate<T> getFloorEstimate(long date) {
		for (int ii = series.size() - 1; ii >= 0; ii--) {
			Estimate<T> est = series.get(ii);
			if (est.orig <= date)
				return est;
		}
		return null;
	}

	public String toString() {
		return "ESTIMATESERIES|" + sec.getSecId() + "|" + type.name + "|" + df.debugFormat(perioddate) + "|" + brokerid + "|"
				+ (series == null ? 0 : series.size());
	}

	public void printSeries() {
		for (Estimate<T> est : series) {
			System.out.println(est.toString());
		}
	}
}
