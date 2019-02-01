package ase.data;

import gnu.trove.TLongArrayList;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.Exchange.Type;
import ase.data.widget.FilePriceBarWidget;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.TimeSeries;
import ase.timeseries.TimeSeriesUtil;
import ase.timeseries.Bar.BarExtraType;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class BarSource {
	private static final Logger log = LoggerFactory.getLogger(BarSource.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final FilePriceBarWidget pbw;
	public final static long BAR_SPAN = Time.fromMinutes(1);

	public BarSource(FilePriceBarWidget pbw) {
		this.pbw = pbw;
	}

	public void preload(Set<Security> secs, long date1, long date2) throws Exception {
		pbw.preload(secs, date1, date2);
	}

	/**
	 * Gets the price of the most recent bar in the asof day with close_ts<=asof
	 */
	public double getPrice(Security sec, long asof, Exchange.Type exch) throws Exception {
		log.info("Loading bars for " + sec + " on " + df.format(asof) + " on " + exch);
		long oldest = Exchange.openTime(asof, exch);
		Bar bb = pbw.getPricesAsOf(sec, asof, oldest, exch);
		if (bb == null) {
			return Double.NaN;
		}
		return bb.close;
	}

	public Map<Security, Bar> getBarAsOf(Set<Security> secs, long asof, Exchange.Type exch) throws Exception {
		long oldest = Exchange.openTime(asof, exch);
		return pbw.getPricesAsOf(secs, asof, oldest, exch);
	}

	/**
	 * Gets a bar created by accumulating all bars within the same day having t1<=close_ts<=t2.
	 */
	public Map<Security, Bar> getBar(Set<Security> secs, long t1, long t2, Exchange.Type exch) throws Exception {
		// does not adjust prices so bar is only aggregated for the same day
		assert Time.midnight(t1) == Time.midnight(t2);

		log.info("Loading default bars between [" + df.format(t1) + ", " + df.format(t2) + "] on " + exch);
		Map<Security, Vector<Bar>> barMap = pbw.getPrices(secs, t1, t2, exch);
		Map<Security, Bar> res = new HashMap<Security, Bar>(barMap.size());

		for (Map.Entry<Security, Vector<Bar>> ent : barMap.entrySet()) {
			if (ent.getValue().size() > 0) {
				res.put(ent.getKey(), TimeSeriesUtil.aggregateBars(ent.getValue()));
			}
		}
		return res;
	}

	/**
	 * Get a bartimeseries for days [date1,date2] comprised of the half bar including bars with open<=close_ts<=open+millisIntoDay. The times associated with
	 * the time series is the closing time of the exchange WARNING: it is not a daily bar series, so prices are unadjusted.
	 */
	public Map<Security, BarTimeSeries> getHalfDayTimeSeries(Set<Security> secs, long date1, long date2, long millisIntoDay, Exchange.Type exch)
			throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);
		assert millisIntoDay < 7 * Time.MILLIS_PER_HOUR && millisIntoDay >= 0;
		log.info("Loading half bars between [" + df.format(date1) + ", " + df.format(date2) + "]. Hours used=" + 1.0 * millisIntoDay / 60 / 60
				/ Time.MILLIS_PER_SECOND);
		Map<Security, BarTimeSeries> result = new HashMap<Security, BarTimeSeries>();
		// create time series objects
		for (Security sec : secs) {
			result.put(sec, new BarTimeSeries(millisIntoDay));
		}

		// get bars for each day
		// long date = date1;
		for (long date = date1; date <= date2; date = Exchange.nextTradingDay(date, exch)) {
			long open = Exchange.openTime(date, exch);
			if (pbw.hasDayBars(date)) {
				Map<Security, Bar> barMap = pbw.getDayBars(secs, date, millisIntoDay, exch);
				for (Security sec : secs) {
					Bar bar = barMap.get(sec);
					assert bar == null || bar.close_ts <= open + millisIntoDay;
					result.get(sec).add(bar, open + millisIntoDay);
				}
			}
			else {
				Map<Security, Vector<Bar>> barMap = pbw.getPrices(secs, open, open + millisIntoDay, exch);
				for (Security sec : secs) {
					Vector<Bar> bars = barMap.get(sec);
					if (bars != null && bars.size() > 0) {
						assert bars.lastElement().close_ts <= open + millisIntoDay;
						result.get(sec).add(TimeSeriesUtil.aggregateBars(bars), open + millisIntoDay);
					}
					else {
						result.get(sec).add(null, open + millisIntoDay);
					}
				}
			}
		}

		return result;
	}

	public Map<Security, Pair<Double, Double>> getQuantileHL(Set<Security> secs, long date, long millisIntoDay, Exchange.Type exch) throws Exception {
		Time.assertDay(date);
		log.info("Loading quantile high/lows for day = " + df.formatShort(date));

		Map<Security, Pair<Double, Double>> result = new HashMap<Security, Pair<Double, Double>>();
		Map<Security, Bar> bars = pbw.getDayBars(secs, date, millisIntoDay, exch);
		long dateAsof = Exchange.openTime(date, exch) + millisIntoDay;
		for (Map.Entry<Security, Bar> e : bars.entrySet()) {
			Security sec = e.getKey();
			Bar bar = e.getValue();
			if (bar == null)
				return null;
			assert bar.close_ts <= dateAsof;
			result.put(sec, new Pair<Double, Double>(bar.getExtra(BarExtraType.QHIGH), bar.getExtra(BarExtraType.QLOW)));
		}
		return result;
	}

	public Map<Security, TimeSeries<Pair<Double, Double>>> getQuantileHL(Set<Security> secs, long date1, long date2, long millisIntoDay, Exchange.Type exch)
			throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);
		log.info("Loading quantile high/lows for days [" + df.formatShort(date1) + ", " + df.formatShort(date2) + "]");

		Map<Security, TimeSeries<Pair<Double, Double>>> result = new HashMap<Security, TimeSeries<Pair<Double, Double>>>();
		for (Security sec : secs)
			result.put(sec, new TimeSeries<Pair<Double, Double>>());
		for (long date = date1; date <= date2; date = Exchange.nextTradingDay(date, exch)) {
			long dateAsof = Exchange.openTime(date, exch) + millisIntoDay;
			Map<Security, Bar> bars = pbw.getDayBars(secs, date, millisIntoDay, exch);
			for (Security sec : secs) {
				Bar bar = bars.get(sec);
				TimeSeries<Pair<Double, Double>> ts = result.get(sec);
				if (bar == null) {
					ts.add(null, dateAsof);
				}
				else {
					assert bar.close_ts <= dateAsof;
					ts.add(new Pair<Double, Double>(bar.getExtra(BarExtraType.QHIGH), bar.getExtra(BarExtraType.QLOW)), dateAsof);
				}
			}
		}

		return result;
	}

	/**
	 * Gets an intraday time series comprised of bars with t1<=close_ts<=t2
	 */
	public Map<Security, BarTimeSeries> getTimeSeries(Set<Security> secs, long t1, long t2, Exchange.Type exch) throws Exception {
		// does not adjust prices so bar is only aggregated for the same day
		assert Time.midnight(t1) == Time.midnight(t2);

		log.info("Loading default bars between " + df.format(t1) + " - " + df.format(t2) + " on " + exch);
		Map<Security, Vector<Bar>> barMap = pbw.getPrices(secs, t1, t2, exch);
		Map<Security, BarTimeSeries> res = new HashMap<Security, BarTimeSeries>(barMap.size());

		long[] close_tss = getBarCloseTimestamps(t1, t2, exch);
		for (Map.Entry<Security, Vector<Bar>> ent : barMap.entrySet()) {
			Vector<Bar> bars = ent.getValue();
			BarTimeSeries ts = new BarTimeSeries(bars, close_tss, BAR_SPAN);
			res.put(ent.getKey(), ts);
		}
		return res;
	}

	public long[] getBarCloseTimestamps(long t1, long t2, Exchange.Type exch) {
		assert Time.midnight(t1) == Time.midnight(t2);

		long open = Exchange.openTime(t1, exch);
		long close = Exchange.closeTime(t1, exch);
		TLongArrayList tss = new TLongArrayList(80);

		for (long date = open + BAR_SPAN; date <= close; date += BAR_SPAN) {
			if (date >= t1 && date <= t2)
				tss.add(date);
		}
		return tss.toNativeArray();
	}

	public static void main(String[] args) throws Exception {
		BarSource bs = new BarSource(FilePriceBarWidget.instance());
		Security sec = new Security(5334);
		Exchange.Type exch = Type.NYSE;
		long date = Time.fromYYYYMMDD(20110603);

		System.out.println(bs.getQuantileHL(CollectionUtils.toSet(sec), date, 0, exch).get(sec));
		System.out.println(bs.getQuantileHL(CollectionUtils.toSet(sec), date, Time.MILLIS_PER_HOUR, exch).get(sec));
		System.out.println(bs.getQuantileHL(CollectionUtils.toSet(sec), date, 2 * Time.MILLIS_PER_HOUR, exch).get(sec));
		System.out.println(bs.getQuantileHL(CollectionUtils.toSet(sec), date, Exchange.REGULAR_TRADING_MILLIS, exch).get(sec));
	}

}
