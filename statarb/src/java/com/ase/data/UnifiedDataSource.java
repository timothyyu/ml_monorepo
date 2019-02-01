package ase.data;

import java.io.File;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.widget.FilePriceBarWidget;
import ase.data.widget.LiveQuoteWidget;
import ase.data.widget.SQLCurrencyWidget;
import ase.data.widget.SQLEstimateWidget;
import ase.data.widget.SQLSecurityWidget;
import ase.portfolio.CapAdjustment;
import ase.portfolio.CapAdjustment.Type;
import ase.portfolio.Portfolio;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.DailyBar;
import ase.timeseries.DailyBarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Time;
import ase.util.Triplet;

public class UnifiedDataSource {
	private static final Logger log = LoggerFactory.getLogger(UnifiedDataSource.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	private final boolean live;

	public final DailyPriceSource dailySource = new DailyPriceSource();
	public final AttributeSource attrSource = new AttributeSource();
	public final BarSource barSource = new BarSource(FilePriceBarWidget.instance());

	public final SQLEstimateWidget estWidget = SQLEstimateWidget.instance();
	public final LiveQuoteWidget lqWidget = LiveQuoteWidget.instance();
	public final SQLSecurityWidget secWidget = SQLSecurityWidget.instance();
	public final SQLCurrencyWidget exWidget = SQLCurrencyWidget.instance();

	private final Map<Security, Triplet<Double, Double, Double>> cachedLiveAdjustments = new HashMap<Security, Triplet<Double, Double, Double>>();
	private long lastModTime = 0;

	public UnifiedDataSource(boolean live) {
		this.live = live;
	}

	@Deprecated
	public Map<Security, Price> getPrices(Set<Security> secs, long asof, Exchange.Type exch) throws Exception {
		return getPrices(secs, asof, exch, this.live);
	}

	/**
	 * MIDNIGHT------ 1 -----OPEN------- 2 ------CLOSE--------- 3 -----MIDNIGHT parse code keeping this division of the current day in mind
	 */
	public Map<Security, Price> getPrices(Set<Security> secs, long asof, Exchange.Type exch, boolean live) throws Exception {
		Map<Security, Quote> quotes = null;
		Map<Security, Bar> bars = null;
		Map<Security, DailyBar> dailyBars = null;

		if (live && Time.today(Time.now()) == Time.today(asof) && Exchange.isOpen(asof, exch)) {
			quotes = lqWidget.getPrices(secs);
			bars = barSource.getBarAsOf(secs, asof, exch);
		}
		else if (Exchange.isTradingDay(asof, exch) && asof < Exchange.closeTime(asof, exch)) {
			bars = barSource.getBarAsOf(secs, asof, exch);
			dailyBars = dailySource.getBarAsOf(secs, asof, exch);
		}
		else {
			bars = barSource.getBarAsOf(secs, asof, exch);
			dailyBars = dailySource.getBarAsOf(secs, asof, exch);
		}

		Map<Security, Price> finalPrices = new HashMap<Security, Price>();
		for (Security sec : secs) {
			Price finalPrice = null;
			Price tmpPrice = null;

			// apply in descending order of priority
			tmpPrice = dailyBars != null ? dailyBars.get(sec) : null;
			if (tmpPrice != null && (finalPrice == null || (tmpPrice.getTs() > finalPrice.getTs()))) {
				finalPrice = tmpPrice;
			}

			tmpPrice = bars != null ? bars.get(sec) : null;
			if (tmpPrice != null && (finalPrice == null || (tmpPrice.getTs() > finalPrice.getTs()))) {
				finalPrice = tmpPrice;
			}

			tmpPrice = quotes != null ? quotes.get(sec) : null;
			if (tmpPrice != null && (finalPrice == null || (tmpPrice.getTs() > finalPrice.getTs()))) {
				finalPrice = tmpPrice;
			}

			if (finalPrice != null) {
				finalPrices.put(sec, finalPrice);
			}
		}

		return finalPrices;
	}

	public Map<Security, DailyBarTimeSeries> getDailyBarTimeSeries(Set<Security> secs, long date1, long t2, Exchange.Type exch) throws Exception {
		Time.assertDay(date1);
		long trading_day_before_t2 = Exchange.prevTradingDay(t2, exch);
		log.info("Getting daily prices between [" + df.formatShort(date1) + ", " + df.formatShort(trading_day_before_t2) + "]");
		Map<Security, DailyBarTimeSeries> dailyPrices = dailySource.getTimeSeries(secs, date1, trading_day_before_t2, exch);

		if (!Exchange.isTradingDay(t2, exch)) {
			log.severe(df.debugFormat(t2)
					+ " doesn't fall on a trading day. The returned time series won't have a bar, null or normal, for the last non-trading date(s). You asked for it...");
			return dailyPrices;
		}

		log.info("Getting intraday prices (if any) between " + df.debugFormat(Exchange.openTime(t2, exch)) + " - " + df.debugFormat(t2));
		Map<Security, Bar> currentBarPrices = null;
		Map<Security, DailyBar> currentDailyBarPrices = null;
		// keep the isTradingDay check for now, just in case we remove the check before
		// before
		if (Exchange.isTradingDay(t2, exch) && t2 <= Exchange.openTime(t2, exch)) {
			currentBarPrices = null;
			currentDailyBarPrices = null;
			// just return daily prices, don't return a null.
			// ignore above, we will return null
			// return dailyPrices;
		}
		else if (Exchange.isTradingDay(t2, exch) && t2 > Exchange.openTime(t2, exch) && t2 < Exchange.closeTime(t2, exch)) {
			currentBarPrices = barSource.getBar(secs, Exchange.openTime(t2, exch), t2, exch);
			currentDailyBarPrices = null;
		}
		// /XXX this condition should hopefully never happen
		else if (Exchange.isTradingDay(t2, exch) && t2 >= Exchange.closeTime(t2, exch) && live && Time.today(t2) == Time.today(Time.now())) {
			log.severe("You are claiming to be live and are asking for prices with asof after today's market... I am using both bars and daily prices");
			currentBarPrices = barSource.getBar(secs, Exchange.openTime(t2, exch), t2, exch);
			// currentDailyBarPrices = dailySource.getBarAsOf(secs, t2, exch);
			currentDailyBarPrices = dailySource.pw.getLatestPrices(secs, Time.today(t2), Time.today(t2), exch);
		}
		else if (Exchange.isTradingDay(t2, exch) && t2 >= Exchange.closeTime(t2, exch)) {
			currentBarPrices = null;
			// currentDailyBarPrices = dailySource.getBarAsOf(secs, t2, exch);
			currentDailyBarPrices = dailySource.pw.getLatestPrices(secs, Time.today(t2), Time.today(t2), exch);
		}
		else {
			currentBarPrices = null;
			currentDailyBarPrices = null;
		}

		// get adjustments
		Map<Security, Triplet<Double, Double, Double>> adjustments = null;
		if (live && Time.today(t2) == Time.today(Time.now()) && (new File(System.getenv("RUN_DIR"), Portfolio.DAY_CAPADJUSTMENTS)).exists()) {
			adjustments = getCapAdjustmentsFromFile();
		}
		else {
			adjustments = dailySource.pw.getAdjustments(secs, Time.today(t2));
		}

		for (Security sec : dailyPrices.keySet()) {
			Bar currentBar = (currentBarPrices != null) ? currentBarPrices.get(sec) : null;
			DailyBar currentDailyBar = (currentDailyBarPrices != null) ? currentDailyBarPrices.get(sec) : null;
			Bar semiFinalBar = null;
			DailyBar finalBar = null;

			// assign to semifinal bar whichever bar is better prioritizing on (a) not null, (b) more recent, (c) more authoritative (compustat>bar file)
			if (currentDailyBar == null && currentBar == null) {
				dailyPrices.get(sec).add(null, t2);
				continue;
			}

			if (currentDailyBar == null)
				semiFinalBar = currentBar;
			else if (currentBar == null)
				semiFinalBar = currentDailyBar;
			else if (currentDailyBar.close_ts >= currentBar.close_ts)
				semiFinalBar = currentDailyBar;
			else if (currentDailyBar.close_ts < currentBar.close_ts)
				semiFinalBar = currentBar;
			else
				throw new RuntimeException("UnifiedDataSource: We should have never reached this condition.");

			double div = 0;
			double casheq = 0;
			double split = 1;
			if (adjustments.containsKey(sec)) {
				Triplet<Double, Double, Double> ds = adjustments.get(sec);
				div = ds.first;
				casheq = ds.second;
				split = ds.third;
			}
			// /XXX Note how we add div+casheq in the bar's dividend component
			finalBar = new DailyBar(semiFinalBar, div + casheq, split);
			dailyPrices.get(sec).add(finalBar, t2);
		}
		return dailyPrices;
	}

	protected Map<Security, Triplet<Double, Double, Double>> getCapAdjustmentsFromFile() throws Exception {
		// Check cache first
		File adjFile = new File(System.getenv("RUN_DIR"), Portfolio.DAY_CAPADJUSTMENTS);
		if (adjFile.lastModified() == lastModTime) {
			return cachedLiveAdjustments;
		}

		this.cachedLiveAdjustments.clear();
		for (CapAdjustment adj : CapAdjustment.loadCapAdjustmentsFile(adjFile)) {
			if (adj.type != Type.DIV && adj.type != Type.SPLIT && adj.type != Type.CASHEQ)
				continue;
			Triplet<Double, Double, Double> ds = cachedLiveAdjustments.get(adj.sec);
			double div = 0;
			double casheq = 0;
			double split = 1;
			if (ds != null) {
				div = ds.first;
				casheq = ds.second;
				split = ds.third;
			}

			if (adj.type == Type.DIV)
				div += adj.adj;
			else if (adj.type == Type.SPLIT)
				split *= adj.adj;
			else if (adj.type == Type.CASHEQ)
				casheq += adj.adj;

			this.cachedLiveAdjustments.put(adj.sec, new Triplet<Double, Double, Double>(div, casheq, split));
		}
		this.lastModTime = adjFile.lastModified();
		return this.cachedLiveAdjustments;
	}

	//
	public Map<Security, Price> getPriceAtTs(Set<Security> secs, long asof, Exchange.Type exch) throws Exception {
		assert asof <= Exchange.closeTime(asof, exch);
		assert asof >= Exchange.openTime(asof, exch);

		Map<Security, Price> result = new HashMap<Security, Price>();

		if (asof == Exchange.closeTime(asof, exch)) {
			for (Map.Entry<Security, DailyBarTimeSeries> e : this.dailySource.getTimeSeries(secs, Time.today(asof), Time.today(asof), exch).entrySet()) {
				Double p = e.getValue().getLastBar() != null ? e.getValue().getLastBar().close : null;
				if (p != null && !Double.isNaN(p)) {
					result.put(e.getKey(), new Quote(p, p, asof));
				}
			}
		}
		else if (asof == Exchange.openTime(asof, exch)) {
			for (Map.Entry<Security, DailyBarTimeSeries> e : this.dailySource.getTimeSeries(secs, Time.today(asof), Time.today(asof), exch).entrySet()) {
				Double p = e.getValue().getLastBar() != null ? e.getValue().getLastBar().open : null;
				if (p != null && !Double.isNaN(p)) {
					result.put(e.getKey(), new Quote(p, p, asof));
				}
			}
		}
		// XXX Would we want to round this up to the closest cent?
		else {
			for (Map.Entry<Security, BarTimeSeries> e : this.barSource.getTimeSeries(secs, Exchange.openTime(asof, exch),  Exchange.closeTime(asof, exch), exch).entrySet()) {
				Security sec = e.getKey();
				BarTimeSeries ts = e.getValue();
				Bar bar = ts.floor(asof + BarSource.BAR_SPAN);
				if (bar !=null && bar.open_ts <= asof && bar.close_ts >= asof) {
					double m = 1.0 * (asof - bar.open_ts) / BarSource.BAR_SPAN;
					double p = m * bar.close + (1 - m) * bar.open;
					result.put(sec, new Quote(p, p, asof));
				}
			}
		}

		return result;
	}

	public static void tests() throws Exception {
		UnifiedDataSource usource = new UnifiedDataSource(false);
		Security sec = new Security(309);
		Set<Security> secs = CollectionUtils.toSet(sec);
		Exchange.Type exch = ase.data.Exchange.Type.NYSE;
		long date1 = Time.fromYYYYMMDD(20110406);
		long date2 = Time.fromYYYYMMDD(20110407);

		DailyBarTimeSeries ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) - 1, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) - 1));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch), exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch)));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) + 1, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) + 1));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) + BarSource.BAR_SPAN, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) + BarSource.BAR_SPAN));
		System.out.println(ts);

		date1 = Time.fromYYYYMMDD(20110407);
		date2 = Time.fromYYYYMMDD(20110407);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) - 1, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) - 1));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch), exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch)));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) + 1, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) + 1));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, Exchange.openTime(date2, exch) + BarSource.BAR_SPAN, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(Exchange.openTime(date2, exch) + BarSource.BAR_SPAN));
		System.out.println(ts);

		ts = usource.getDailyBarTimeSeries(secs, date1, date1 - 1, exch).get(sec);
		System.out.println(df.debugFormat(date1) + " " + df.debugFormat(date1 - 1));
		System.out.println(ts);
	}

	public static void main(String[] args) throws Exception {
		try {
			tests();
			// Security sec = new Security(Integer.parseInt(args[0]));
			// long t1 = df.dfShort.parse(args[1]).getTime();
			// long t2 = df.dfShort.parse(args[2]).getTime();
			// Exchange.Type exch = Exchange.Type.valueOf(args[3]);
			//
			// UnifiedDataSource uSource = new UnifiedDataSource(false);
			// System.out.println(uSource.getDailyBarTimeSeries(CollectionUtils.toSet(sec), t1, t2, exch));
		}
		catch (Exception e) {
			e.printStackTrace();
		}

	}
}
