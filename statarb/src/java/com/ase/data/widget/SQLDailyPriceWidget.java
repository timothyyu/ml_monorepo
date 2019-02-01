package ase.data.widget;

import gnu.trove.TIntObjectHashMap;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.Vector;

import ase.data.Country;
import ase.data.Currency;
import ase.data.Exchange;
import ase.data.Exchange.Type;
import ase.data.Security;
import ase.timeseries.DailyBar;
import ase.util.CollectionUtils;
import ase.util.Pair;
import ase.util.PerformanceTimer;
import ase.util.Time;
import ase.util.Triplet;

public class SQLDailyPriceWidget extends SQLWidget {

	private static SQLDailyPriceWidget instance;

	synchronized public static SQLDailyPriceWidget instance() {
		if (instance == null) {
			instance = new SQLDailyPriceWidget();
		}
		return instance;
	}

	// //////////// CACHING STRUCTURES /////////////////////////
	// The information that we keep around for each secid
	private static class BarCacheElement {
		long fromDate;
		long toDate;
		Vector<DailyBar> list = null;

		public BarCacheElement(long fromDate, long toDate, Vector<DailyBar> list) {
			this.fromDate = fromDate;
			this.toDate = toDate;
			this.list = list;
		}

		// assumes that list of bars given and stored is sorted by date
		public void update(long fromDate, long toDate, Vector<DailyBar> list) {
			// no overlap with existing data, straight substitute
			// if the series is getting too long, straight substitute
			if (toDate < this.fromDate || fromDate > this.toDate) {
				this.fromDate = fromDate;
				this.toDate = toDate;
				this.list = list;

				return;
			}
			// prepend bars
			// If we need to prepend bars, use a new arraylist for efficiency
			if (fromDate < this.fromDate) {
				Vector<DailyBar> newlist = new Vector<DailyBar>();
				for (DailyBar bar : list) {
					if (Time.midnight(bar.close_ts) < this.fromDate) {
						newlist.add(bar);
					}
				}

				newlist.addAll(this.list);
				this.list = newlist;
			}
			// append bars
			if (toDate > this.toDate) {
				for (DailyBar bar : list) {
					if (Time.midnight(bar.close_ts) >= this.toDate) { // Note that we test for
						// equality since data
						this.list.add(bar); // in cache is
											// [this.fromDate,this.toDate)
					}
				}
			}

			this.fromDate = Math.min(this.fromDate, fromDate);
			this.toDate = Math.max(this.toDate, toDate);
		}
	}

	private TIntObjectHashMap<BarCacheElement> barCache = new TIntObjectHashMap<SQLDailyPriceWidget.BarCacheElement>();
	private HashMap<Pair<Integer, Integer>, Triplet<Double, Double, Double>> adjCache = new HashMap<Pair<Integer, Integer>, Triplet<Double, Double, Double>>();
	private static boolean USE_CACHING = true;
	private static int MAX_CACHE_LENGTH_PER_SECURITY = 1000;
	private static Comparator<DailyBar> dbComp = DailyBar.getDayBasedComparator();

	// /////////// REMAINING CODE ////////////

	// XXX need to check cond code here
	@Deprecated
	String query_range = "SELECT p.secid, p.date, " + "IFNULL(p.open, 'NaN'), IFNULL(p.high, 'NaN'), IFNULL(low, 'NaN'), IFNULL(p.close, 'NaN'), "
			+ "IFNULL(p.volume, 'NaN'), p.currency, IFNULL(p.adj, 'NaN'), IFNULL(p.adrrc, 'NaN'), " + "IFNULL(d.dividend, 0), IFNULL(sp.rate, 1) "
			+ "FROM securitytmp s " + "JOIN price_full p ON s.secid = p.secid " + "LEFT JOIN dividend d ON p.secid = d.secid AND p.date = d.date "
			+ "LEFT JOIN split sp ON p.secid = sp.secid AND p.date = sp.date "
			+ "WHERE p.cond = 3 AND p.date >= ? AND p.date <= ? AND p.died IS NULL and d.died IS NULL and sp.died IS NULL "
			+ "ORDER BY p.secid ASC, p.date ASC";

	String query_asOf = "SELECT p.date, " + "IFNULL(p.open, 'NaN'), IFNULL(p.high, 'NaN'), IFNULL(low, 'NaN'), "
			+ "IFNULL(close, 'NaN'), IFNULL(volume, 'NaN'), currency, IFNULL(adj, 'NaN'), IFNULL(adrrc, 'NaN') "
			+ "FROM price_full p WHERE p.secid = ? AND p.cond = 3 AND p.died IS NULL AND p.date<=? AND p.date>=? ORDER BY p.date DESC LIMIT 1";

	String query_single_range = "SELECT p.secid, p.date, " + "IFNULL(p.open, 'NaN'), IFNULL(p.high, 'NaN'), IFNULL(low, 'NaN'), IFNULL(p.close, 'NaN'), "
			+ "IFNULL(p.volume, 'NaN'), p.currency, IFNULL(p.adj, 'NaN'), IFNULL(p.adrrc, 'NaN'), "
			+ "IFNULL(d.dividend, 0), IFNULL(d.casheq,0), IFNULL(sp.rate, 1) " + "FROM price_full p "
			+ "LEFT JOIN dividend d ON p.secid = d.secid AND p.date = d.date AND d.died IS NULL " + "LEFT JOIN split sp ON p.secid = sp.secid AND p.date = sp.date AND sp.died IS NULL "
			+ "WHERE p.secid=? AND p.cond = 3 AND p.date >= ? AND p.date < ? AND p.died IS NULL "
			+ "ORDER BY p.secid ASC, p.date ASC";

	// Revisit this, but it is devilishly tricky to get both splits/dividends
	// with a single sql query,
	// since WHERE conditions are applied *after* the outer joins and not at the
	// base tables before the join is made.
	String query_dividend = "SELECT dividend, casheq FROM dividend WHERE secid=? AND date=? AND died IS NULL";
	String query_split = "SELECT rate FROM split WHERE secid=? AND date=? AND died IS NULL";
	String query_future_split = "SELECT rate FROM future_split WHERE secid=? AND date=? AND died IS NULL";

	private SQLDailyPriceWidget() {
		super();
	}

	protected void uponReconnect() {
	}

	// /XXX: Note how the dividend that we assign to a bar is dividend+casheq
	private Vector<DailyBar> getPricesInternal(Security sec, long date1, long date2) throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);

		Vector<DailyBar> bars = new Vector<DailyBar>();

		// Assumes that statement has been prepared
		stm.setInt(1, sec.getSecId());
		stm.setInt(2, Time.toYYYYMMDD(date1));
		stm.setInt(3, Time.toYYYYMMDD(date2));
		// log.finest("Querying in range [" + df.dfShort.format(date1) + "," + df.dfShort.format(date2) + ")");

		ResultSet rs = stm.executeQuery();
		while (rs.next()) {
			long bardate = Time.fromYYYYMMDD(rs.getInt(2));
			bars.add(new DailyBar(sec, bardate, rs.getDouble(3), rs.getDouble(4), rs.getDouble(5), rs.getDouble(6), rs.getDouble(7), rs.getDouble(11)
					+ rs.getDouble(12), rs.getDouble(13), sec.primaryExchange));
		}
		rs.close();
		return bars;
	}

	// Get me all the prices in the range [date1,date2)
	// The dates are provided as timestamps, while daily prices are recorded at
	// the granularity of a day.
	// We use the following convention. Let day(date1) be the day in which the
	// date falls in. Example:
	// day(20110113 00:00:00)=20110113
	// day(20110113 14:50:00)=20110113
	// day(20110113 23:59:59)=20110113
	// When you request range [date1,date2), we return you
	// [day(date1),day(date2))
	synchronized public Map<Security, Vector<DailyBar>> getPrices(Set<Security> secs, long date1, long date2) throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);

		log.info("Loading prices between [" + df.format(date1) + ", " + df.format(date2) + ")");
		log.info("Converting to [" + df.formatShort(date1) + ", " + df.formatShort(date2) + ")");
		Map<Security, Vector<DailyBar>> res = new HashMap<Security, Vector<DailyBar>>();
		stm = c.prepareStatement(query_single_range);

		long cnt1 = 0;
		long cnt2 = 0;
		for (Security sec : secs) {
			// the modified query ranges (up to two, part before the existing
			// range, and part after
			Pair<Long, Long>[] queryRanges = (Pair<Long, Long>[]) (new Pair[2]);
			Arrays.fill(queryRanges, null);

			// check cache to constraint query interval if possible
			BarCacheElement cachedData = barCache.get(sec.getSecId());

			// if no data or already to much data
			if (!USE_CACHING || cachedData == null || (cachedData.toDate - cachedData.fromDate) / Time.MILLIS_PER_DAY > MAX_CACHE_LENGTH_PER_SECURITY) {
				queryRanges[0] = new Pair<Long, Long>(date1, date2);
				cachedData = null;
			}
			else {
				// get the prefix part
				if (date1 < cachedData.fromDate) {
					queryRanges[0] = new Pair<Long, Long>(date1, Math.min(date2, cachedData.fromDate));
				}
				// get the suffix part
				if (date2 > cachedData.toDate) {
					queryRanges[1] = new Pair<Long, Long>(Math.max(cachedData.toDate, date1), date2);
				}
			}

			// do the actual queries
			for (Pair<Long, Long> range : queryRanges) {
				if (range == null)
					continue;

				Vector<DailyBar> bars = getPricesInternal(sec, range.first, range.second);
				cnt1 += bars.size();

				// update cache (this will provide the final time series
				if (cachedData == null) {
					cachedData = new BarCacheElement(range.first, range.second, bars);
					if (USE_CACHING) {
						barCache.put(sec.getSecId(), cachedData);
					}
				}
				else {
					cachedData.update(range.first, range.second, bars);
				}
			}

			// final time series
			Vector<DailyBar> prices = new Vector<DailyBar>();

			// get range through binary search
			int start = Collections.binarySearch(cachedData.list, new DailyBar(null, date1, 0, 0, 0, 0, 0, 0, 0, sec.primaryExchange), dbComp);
			int end = Collections.binarySearch(cachedData.list, new DailyBar(null, date2, 0, 0, 0, 0, 0, 0, 0, sec.primaryExchange), dbComp);
			start = (start < 0) ? -start - 1 : start;
			end = (end < 0) ? -end - 1 : end;

			prices.addAll(cachedData.list.subList(start, end));

			cnt2 += prices.size();
			res.put(sec, prices);
		}
		stm.close();
		log.info("Loaded " + cnt2 + " prices, " + cnt1 + " of them new.");
		return res;
	}

	/**
	 * Return most recent bar in range [oldest,date]
	 */
	synchronized public Map<Security, DailyBar> getLatestPrices(Set<Security> secs, long date, long oldest, Exchange.Type exch) throws Exception {
		Time.assertDay(date);
		Time.assertDay(oldest);
		// log.finest("Loading prices as of (<=) " + df.format(date));

		stm = null;
		Map<Security, DailyBar> res = new HashMap<Security, DailyBar>();
		int cnt = 0;
		int newcnt = 0;
		for (Security sec : secs) {
			// See if we can get it from the cache
			if (USE_CACHING) {
				BarCacheElement ce = barCache.get(sec.getSecId());
				if (ce != null && date < ce.toDate && oldest >= ce.fromDate) {
					// get range through binary search
					DailyBar bar = null;
					int upperBound = Collections.binarySearch(ce.list, new DailyBar(null, date, 0, 0, 0, 0, 0, 0, 0, sec.primaryExchange), dbComp);
					for (int ii = upperBound; ii >= 0; ii--) {
						long barDate = Time.today(ce.list.get(ii).close_ts);
						if (barDate < oldest) {
							break;
						}
						else if (barDate <= date) {
							bar = ce.list.get(ii);
							break;
						}
					}

					if (bar != null) {
						res.put(sec, bar);
						cnt++;
					}
					continue; // next security
				}
			}

			// lazy preparation
			if (stm == null) {
				stm = c.prepareStatement(query_asOf);
				stm.setInt(2, Time.toYYYYMMDD(date));
				stm.setInt(3, Time.toYYYYMMDD(oldest));
			}

			// res.put(sec, getPricesAsOf(sec, asOf, oldest, exch));
			stm.setInt(1, sec.getSecId());
			ResultSet rs = stm.executeQuery();
			if (rs.next()) {
				res.put(sec,
						new DailyBar(sec, Time.fromYYYYMMDD(rs.getInt(1)), rs.getDouble(2), rs.getDouble(3), rs.getDouble(4), rs.getDouble(5), rs.getDouble(6),
								0, 1, exch));
				cnt++;
				newcnt++;
			}
			rs.close();
		}
		if (stm != null) {
			stm.close();
		}
		// log.finest("Loaded " + cnt + " prices, " + newcnt + " of them new.");
		return res;
	}

	@Deprecated
	private Vector<DailyBar> loadBars(Security sec, Exchange.Type exch) throws Exception {
		Vector<DailyBar> v = new Vector<DailyBar>();
		ResultSet rs = stm.executeQuery();
		while (rs.next()) {
			long bardate = df.parseShort(rs.getString(1)).getTime();
			// XXX creating with dummy splits/dividens
			v.add(new DailyBar(sec, bardate, rs.getDouble(2), rs.getDouble(3), rs.getDouble(4), rs.getDouble(5), rs.getDouble(6), 0, 1, exch));
		}
		rs.close();

		return v;
	}

	// returns <DIV,CASHEQ,SPLIT>
	synchronized public Map<Security, Triplet<Double, Double, Double>> getAdjustments(Set<Security> secs, long date) throws Exception {
		Time.assertDay(date);
		// Determine if we are live. If the date translates to the same YYYYMMDD
		// as Time.now(), we are probably operating live. It seems that for
		// splits that happened on date X,
		// we learn the at about X+1, 3:30am UTC
		if (Time.today(date) == Time.today(Time.now())) {
			return getAdjustments(secs, date, true);
		}
		else {
			return getAdjustments(secs, date, false);
		}
	}

	// Get the splits and dividends that happen on the date YYYYMMDD contained
	// by timestamp date
	synchronized public Map<Security, Triplet<Double, Double, Double>> getAdjustments(Set<Security> secs, long date, boolean live) throws Exception {
		Time.assertDay(date);
		Integer intDate = Integer.parseInt(df.formatShort(date));
		log.info("Loading live=" + live + " div/cacheq/split for " + df.format(date));
		log.info("Converting to " + intDate.toString());

		PreparedStatement dividendSt = null;
		PreparedStatement splitSt = null;
		Map<Security, Triplet<Double, Double, Double>> result = new HashMap<Security, Triplet<Double, Double, Double>>();
		for (Security sec : secs) {
			if (USE_CACHING && !live) {
				Triplet<Double, Double, Double> adj = adjCache.get(new Pair<Integer, Integer>(sec.getSecId(), intDate));
				if (adj != null) {
					result.put(sec, adj);
					continue;
				}
			}

			// /XXX preparing statments lazily.
			if ((dividendSt == null || splitSt == null) && live) {
				dividendSt = prepare(query_dividend);
				dividendSt.setInt(2, intDate);

				splitSt = prepare(query_future_split);
				splitSt.setInt(2, intDate);
			}
			else if ((dividendSt == null || splitSt == null) && !live) {
				dividendSt = prepare(query_dividend);
				dividendSt.setInt(2, intDate);

				splitSt = prepare(query_split);
				splitSt.setInt(2, intDate);
			}

			double div = 0;
			double casheq = 0;
			double sp = 1;

			dividendSt.setInt(1, sec.getSecId());
			ResultSet rs1 = dividendSt.executeQuery();
			if (rs1.next()) { // There should be at most one
				div = rs1.getDouble(1);
				casheq = rs1.getDouble(2);
			}
			rs1.close();

			splitSt.setInt(1, sec.getSecId());
			ResultSet rs2 = splitSt.executeQuery();
			if (rs2.next()) { // There should be at most one
				sp = rs2.getDouble(1);
			}
			rs2.close();

			Triplet<Double, Double, Double> adj = new Triplet<Double, Double, Double>(div, casheq, sp);
			if (USE_CACHING && !live) {
				adjCache.put(new Pair<Integer, Integer>(sec.getSecId(), intDate), adj);
			}
			result.put(sec, adj);
		}

		if (splitSt != null) {
			splitSt.close();
		}
		if (dividendSt != null) {
			dividendSt.close();
		}

		return result;
	}

	// public Map<Security,Double> getAdvpsAsOf(Set<Security> secs, long date,
	// int lookback) throws Exception {
	// Map<Security, Double> res = new HashMap<Security,Double>();
	// for (Security sec : secs) {
	// res.put(sec, getAdvpAsOf( sec, date));
	// }
	// return res;
	// }

	// public Double getAdvpAsOf(Security sec, long date, int lookback) throws
	// Exception {
	// stm = c.prepareStatement(query_adv)
	// }

	synchronized public void clearCache() {
		this.barCache.clear();
	}

	// ///////////// TESTS ///////////////////
	private static String compareResults(Map<Security, Vector<DailyBar>> secToBars1, Map<Security, Vector<DailyBar>> secToBars2) {
		if (!secToBars1.keySet().containsAll(secToBars2.keySet()) || !secToBars2.keySet().containsAll(secToBars1.keySet())) {
			return "Uneven sets of securities";
		}

		for (Entry<Security, Vector<DailyBar>> e : secToBars1.entrySet()) {
			Vector<DailyBar> list1 = e.getValue();
			Vector<DailyBar> list2 = secToBars2.get(e.getKey());

			for (int i = 0; i < list1.size(); i++) {
				DailyBar bar1 = list1.get(i);
				DailyBar bar2 = list2.get(i);

				if (!(bar1.close_ts == bar2.close_ts && bar1.close == bar2.close)) {
					return "Uneven data for security " + e.getKey().getSecId() + "\n" + bar1.toString() + " " + bar2.toString();
				}
			}
		}

		return "Hey-okey!";
	}

	private static void tests() throws Exception {
		Set<Security> secs = CollectionUtils.toSet(new Security[] { new Security(5334), new Security(309) });
		Exchange.Type exch = Type.NYSE;
		SQLDailyPriceWidget widget = new SQLDailyPriceWidget();

		// check cached data correctness
		Map<Security, Vector<DailyBar>> secToBars1 = widget.getPrices(secs, df.parse("20010101"), df.parse("20020101"));
		Map<Security, Vector<DailyBar>> secToBars2 = widget.getPrices(secs, df.parse("20010601"), df.parse("20020601"));
		Map<Security, Vector<DailyBar>> secToBars3 = widget.getPrices(secs, df.parse("19990101"), df.parse("20030101"));
		Map<Security, Vector<DailyBar>> secToBars4 = widget.getPrices(secs, df.parse("19980101"), df.parse("20020101"));
		Map<Security, Vector<DailyBar>> secToBars5 = widget.getPrices(secs, df.parse("19970101"), df.parse("19980101"));
		widget.clearCache();
		Map<Security, Vector<DailyBar>> secToBars6 = widget.getPrices(secs, df.parse("19970101"), df.parse("20010101"));
		System.out.println(compareResults(secToBars5, secToBars6));

		widget.clearCache();
		Security sec = new Security(309);
		long date = Time.fromYYYYMMDD(20110406);
		System.out.println("Cache empty");
		DailyBar db = widget.getLatestPrices(secs, date, Exchange.subtractTradingDays(date, 5, exch), exch).get(sec);
		System.out.println(db.toHRString());

		System.out.println("Cache end right before date");
		widget.getPrices(secs, Exchange.subtractTradingDays(date, 5, exch), date);
		db = widget.getLatestPrices(secs, date, Exchange.subtractTradingDays(date, 5, exch), exch).get(sec);
		System.out.println(db.toHRString());

		System.out.println("Cache end right on date");
		widget.getPrices(secs, Exchange.subtractTradingDays(date, 5, exch), date + Time.MILLIS_PER_DAY);
		db = widget.getLatestPrices(secs, date, Exchange.subtractTradingDays(date, 5, exch), exch).get(sec);
		System.out.println(db.toHRString());

		System.out.println("Cache end right after date");
		widget.getPrices(secs, Exchange.subtractTradingDays(date, 5, exch), date + 2 * Time.MILLIS_PER_DAY);
		db = widget.getLatestPrices(secs, date, Exchange.subtractTradingDays(date, 5, exch), exch).get(sec);
		System.out.println(db.toHRString());

		widget.clearCache();
		System.out.println("Cache start right after oldest");
		widget.getPrices(secs, Exchange.subtractTradingDays(date + Time.MILLIS_PER_DAY, 5, exch), date + 2 * Time.MILLIS_PER_DAY);
		db = widget.getLatestPrices(secs, date, Exchange.subtractTradingDays(date, 5, exch), exch).get(sec);
		System.out.println(db.toHRString());
	}

	private static void adjustmentTests() throws Exception {
		SQLDailyPriceWidget widget = new SQLDailyPriceWidget();
		// no split/dividend
		Security sec = new Security(130);
		Map<Security, Triplet<Double, Double, Double>> res1 = widget.getAdjustments(CollectionUtils.toSet(sec), df.parseMins("20110110_1530").getTime(),
				true);
		System.out.println(res1.get(sec));
	}

	private static void benchmark() throws Exception {
		SQLSecurityWidget secWidget = SQLSecurityWidget.instance();
		Set<Security> secs = secWidget.getStocksAsOf(Country.US, Currency.USD, 250.0, 1.0, 100000.0, df.parse("20060101"), 20);

		SQLDailyPriceWidget widget = new SQLDailyPriceWidget();
		PerformanceTimer timer = new PerformanceTimer();

		timer.start();
		// widget.getPricesDeprecated(secs, df.parse("20010101"),
		// df.parse("20020101"));
		widget.getPrices(secs, df.parse("20010101"), df.parse("20020101"));
		timer.end();

		System.out.println(timer.avgTimeInMillis());
	}

	public static void main(String[] argv) {
		try {
			tests();
			// // Sample code for getting range data
			// // Get widget
			// SQLDailyPriceWidget widget = new SQLDailyPriceWidget();
			//
			// // Define set of securities
			// Set<Security> secs = CollectionUtils.toSet(new Security[] { new Security(2), new Security(5) });
			// // Get prices between [date1,date2] (both sides closed,dates in
			// // milliseconds)
			// Map<Security, Vector<DailyBar>> secToBars = widget.getPrices(secs, df.parse("19980101"), df.parse("20030101"));
			//
			// // Sample code for getting as-of data
			// // Get widget
			// widget = new SQLDailyPriceWidget();
			// // Define set of securities
			// secs = CollectionUtils.toSet(new Security[] { new Security(2), new Security(5) });
			// // Get prices as of date (both sides closed,dates in
			// // milliseconds)
			// Map<Security, DailyBar> secToBars2 = widget.getPricesAsOf(secs, df.parse("19980101"), df.parse("19700101"), Exchange.Type.DUMMY);
		}
		catch (Exception e) {
			System.out.println(e);
		}
	}
}
