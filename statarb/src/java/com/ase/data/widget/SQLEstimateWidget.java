package ase.data.widget;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.FileReader;
import java.io.IOException;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.MessageFormat;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.NavigableSet;
import java.util.Properties;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.Vector;

import ase.data.Attribute;
import ase.data.Currency;
import ase.data.DbAttrType;
import ase.data.DistributionSummary;
import ase.data.Estimate;
import ase.data.Estimate.FlagType;
import ase.data.EstimateSeries;
import ase.data.ReutersAnnDate;
import ase.data.Security;
import ase.data.Universe;
import ase.util.CollectionUtils;
import ase.util.Pair;
import ase.util.PerformanceTimer;
import ase.util.Time;

public class SQLEstimateWidget extends SQLWidget {
	// ////////////////////////////

	public enum DateType {
		PAST, // date of estimate < "date"
		PRESENT, // date of estimate == "date"
		FUTURE; // date of estimate is > "date"
	}

	// ////////////////////////////

	private static SQLEstimateWidget instance = null;

	public static final SQLEstimateWidget instance() {
		if (instance == null) {
			instance = new SQLEstimateWidget();
		}
		return instance;
	}

	@Override
	protected void uponReconnect() {
		// TODO Auto-generated method stub
	}

	// {0} attr type, {1} limit, {2} ts, {3} backfill
	private static String periodQuery = "SELECT x.perioddate,x.advdate,x.announced,x.status,x.phase,x.born\n"
			+ "FROM cs2reuters AS m STRAIGHT_JOIN reuters_period AS x on(m.rkd=x.rkd)\n"
			+ "WHERE m.secid=? AND x.type={0} AND x.announced=%s AND m.born<={2} AND (m.died IS NULL OR m.died>{2}) AND (x.born+x.backfill*{3})<={2} AND (x.died IS NULL OR (x.died+x.backfill*{3})>{2})\n"
			+ "ORDER BY x.perioddate %s LIMIT {1}";
	private static String futurePeriodQuery = String.format(periodQuery, "0", "ASC");
	private static String pastPeriodQuery = String.format(periodQuery, "1", "DESC");
	private static String calendarQuery = "SELECT x.perioddate\n"
			+ "FROM cs2reuters AS m STRAIGHT_JOIN reuters_period AS x on(m.rkd=x.rkd)\n"
			+ "WHERE m.secid=? AND x.type={0} AND m.born<={2} AND (m.died IS NULL OR m.died>{2}) AND (x.born+x.backfill*{3})<={2} AND (x.died IS NULL OR (x.died+x.backfill*{3})>{2})\n"
			+ "ORDER BY x.perioddate ASC";

	private static String brokerQuery = "SELECT name FROM brokers WHERE brokerid=? AND source=17 AND born<=? AND (died IS NULL OR died>?)";

	// think if you want to constrain time series with [m.born, m.died) for extra safety
	// also whether you want to make f.orig2 fall within the query range.
	// {0} table, {1} attribute type, {2} brokerid, {3} orig lower range, {4} orig upper range, {5} asof, {6} backfill offset
	private static String estimates_sb_exp = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born\n"
			+ "FROM cs2reuters AS m\n"
			+ "STRAIGHT_JOIN {0} AS e ON (m.rkd=e.rkd)\n"
			+ "LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig AND (f.born+f.backfill*{6})<={5} AND (f.died IS NULL or (f.died+f.backfill*{6})>{5}))\n"
			+ "WHERE m.secid=? AND m.born<={5} AND (m.died IS NULL OR m.died>{5}) AND e.date=? AND e.type={1} AND e.brokerid={2} AND (e.born+e.backfill*{6})<={5} AND (e.died IS NULL OR (e.died+e.backfill*{6})>{5}) AND e.orig<{4} AND e.orig>={3}\n"
			+ "ORDER BY e.orig ASC,f.orig2 ASC";

	private static String estimates_ab_exp = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born,e.brokerid\n"
			+ "FROM cs2reuters AS m\n"
			+ "STRAIGHT_JOIN {0} AS e ON (m.rkd=e.rkd)\n"
			+ "LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig AND (f.born+f.backfill*{6})<={5} AND (f.died IS NULL or (f.died+f.backfill*{6})>{5}))\n"
			+ "WHERE m.secid=? AND m.born<={5} AND (m.died IS NULL OR m.died>{5}) AND e.date=? AND e.type={1} AND (e.born+e.backfill*{6})<={5} AND (e.died IS NULL OR (e.died+e.backfill*{6})>{5}) AND e.orig<{4} AND e.orig>={3}\n"
			+ "ORDER BY e.brokerid ASC,e.orig ASC,f.orig2 ASC";

	// / CACHING OF SPLITS ////
	private HashMap<Integer, NavigableMap<Long, Double>> splitCache = new HashMap<Integer, NavigableMap<Long, Double>>();
	private long splitCacheTs = Long.MIN_VALUE;

	private static Map<String, String[]> queries = new HashMap<String, String[]>() {
		{
			put("co_estimates_n", new String[] { estimates_sb_exp, estimates_ab_exp });
			put("co_estimates_b", new String[] { estimates_ab_exp, estimates_ab_exp });
		}
	};

	public EstimateSeries<Double> parseNumResultSet(Security sec, DbAttrType attr, int brokerid, long asOf, ResultSet rs) throws SQLException {
		EstimateSeries<Double> series = null;
		Estimate<Double> oldInstance = null;
		while (rs.next()) {
			if (series == null)
				series = new EstimateSeries<Double>(sec, attr, Time.fromYYYYMMDD(rs.getInt(1)), brokerid);

			// get info from tuple
			long orig1 = rs.getLong(4);

			Estimate<Double> instance;
			if (oldInstance == null || oldInstance.orig != orig1) {
				double value = rs.getDouble(2);
				Currency currency = Currency.getCurrency(rs.getShort(3));
				long born1 = rs.getLong(5);

				instance = series.addEstimate(value, currency, orig1, born1);
				oldInstance = instance;
			}
			else {
				instance = oldInstance;
			}

			long orig2 = rs.getLong(6);
			String flag = rs.getString(7);
			long born2 = rs.getLong(8);

			if (flag == null) // XXX this is needed due to the left join
				;
			else if (flag.equals("T"))
				instance.addFlag(FlagType.T, orig2, born2);
			else if (flag.equals("C"))
				instance.addFlag(FlagType.C, orig2, born2);
			else if (flag.equals("S"))
				instance.addFlag(FlagType.S, orig2, born2);
			else if (flag.equals("U"))
				instance.addFlag(FlagType.U, orig2, born2);
			else if (flag.equals("N"))
				instance.addFlag(FlagType.N, orig2, born2);
		}

		return series;
	}

	public EstimateSeries<DistributionSummary> parseDistResultSet(Security sec, DbAttrType attr, int brokerid, long asOf, ResultSet rs) throws SQLException,
			IOException {
		EstimateSeries<DistributionSummary> series = null;
		Estimate<DistributionSummary> oldInstance = null;

		while (rs.next()) {
			if (series == null) {
				series = new EstimateSeries<DistributionSummary>(sec, attr, Time.fromYYYYMMDD(rs.getInt(1)), brokerid);
			}

			long orig1 = rs.getLong(4);

			Estimate<DistributionSummary> instance;
			if (oldInstance == null || oldInstance.orig != orig1) {
				DataInputStream rawData = new DataInputStream(new ByteArrayInputStream(rs.getBytes(2)));
				float high = rawData.readFloat();
				float low = rawData.readFloat();
				float mean = rawData.readFloat();
				float stddev = rawData.readFloat();
				float median = rawData.readFloat();
				int ests = rawData.readInt();

				Currency currency = Currency.getCurrency(rs.getShort(3));
				long born1 = rs.getLong(5);

				instance = series.addEstimate(new DistributionSummary(mean, stddev, low, median, high, ests), currency, orig1, born1);
				oldInstance = instance;
			}
			else {
				instance = oldInstance;
			}

			long orig2 = rs.getLong(6);
			String flag = rs.getString(7);
			long born2 = rs.getLong(8);

			if (flag == null) // XXX this is needed due to the left join
				;
			else if (flag.equals("T"))
				instance.addFlag(FlagType.T, orig2, born2);
			else if (flag.equals("C"))
				instance.addFlag(FlagType.C, orig2, born2);
			else if (flag.equals("S"))
				instance.addFlag(FlagType.S, orig2, born2);
			else if (flag.equals("U"))
				instance.addFlag(FlagType.U, orig2, born2);
			else if (flag.equals("N"))
				instance.addFlag(FlagType.N, orig2, born2);

		}
		return series;
	}

	public Map<Integer, EstimateSeries<Double>> parseDetNumResultSet(Security sec, DbAttrType attr, long asOf, ResultSet rs, boolean returnSuppressed)
			throws SQLException {
		Map<Integer, EstimateSeries<Double>> allSeries = null;
		EstimateSeries<Double> oldSeries = null;
		Estimate<Double> oldInstance = null;
		while (rs.next()) {
			if (allSeries == null)
				allSeries = new HashMap<Integer, EstimateSeries<Double>>();

			int brokerid = rs.getInt(9);
			EstimateSeries<Double> series;
			if (oldSeries == null || oldSeries.brokerid != brokerid) {
				oldSeries = series = new EstimateSeries<Double>(sec, attr, Time.fromYYYYMMDD(rs.getInt(1)), brokerid);
				allSeries.put(brokerid, series);
			}
			else {
				series = oldSeries;
			}

			long orig1 = rs.getLong(4);
			Estimate<Double> instance;
			if (oldInstance == null || oldInstance.orig != orig1) {
				if (oldInstance != null && (!returnSuppressed && series.getLatestEstimate() != null && series.getLatestEstimate().isSuppressed())) {
					series.removeLatestEstimate();
				}

				double value = rs.getDouble(2);
				Currency currency = Currency.getCurrency(rs.getShort(3));
				long born1 = rs.getLong(5);
				instance = series.addEstimate(value, currency, orig1, born1);
				oldInstance = instance;
			}
			else {
				instance = oldInstance;
			}

			long orig2 = rs.getLong(6);
			String flag = rs.getString(7);
			long born2 = rs.getLong(8);

			if (flag == null) // XXX this is needed due to the left join
				;
			else if (flag.equals("T"))
				instance.addFlag(FlagType.T, orig2, born2);
			else if (flag.equals("C"))
				instance.addFlag(FlagType.C, orig2, born2);
			else if (flag.equals("S"))
				instance.addFlag(FlagType.S, orig2, born2);
			else if (flag.equals("U"))
				instance.addFlag(FlagType.U, orig2, born2);
			else if (flag.equals("N"))
				instance.addFlag(FlagType.N, orig2, born2);
		}

		if (!returnSuppressed && allSeries != null) {
			for (EstimateSeries<Double> est : allSeries.values()) {
				if (est.getLatestEstimate() != null && est.getLatestEstimate().isSuppressed()) {
					est.removeLatestEstimate();
				}
			}
		}

		return allSeries;
	}

	public static Map<Security, Long> associateSecidsWithDates(Set<Security> secs, long date) {
		Map<Security, Long> result = new HashMap<Security, Long>();
		for (Security sec : secs)
			result.put(sec, date);
		return result;
	}

	public static Map<Security, Long> associateSecidsWithDates(Map<Security, Attribute> secAndDate) {
		Map<Security, Long> result = new HashMap<Security, Long>();
		for (Map.Entry<Security, Attribute> e : secAndDate.entrySet())
			result.put(e.getKey(), e.getValue().asDate());
		return result;
	}

	public Map<Security, EstimateSeries<?>> getConsensus(Map<Security, Long> secAndDate, DbAttrType attr, long asOf, long oldest) throws Exception {
		assert attr.dbname.endsWith("_CE");
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		String table = attr.tableref;
		String attrCode = Integer.toString(attr.code);
		String brokerid = "1";
		String t1 = Long.toString(oldest);
		String t2 = Long.toString(asOf);
		String ts = Long.toString(asOf);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(queries.get(table)[0], table, attrCode, brokerid, t1, t2, ts, offset);

		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		Map<Security, EstimateSeries<?>> result = new HashMap<Security, EstimateSeries<?>>();

		for (Map.Entry<Security, Long> sd : secAndDate.entrySet()) {
			long millis = sd.getValue();
			int date;
			if (millis == Long.MIN_VALUE)
				date = 0;
			else {
				Time.assertDay(millis);
				date = Time.toYYYYMMDD(millis);
			}

			Security sec = sd.getKey();
			ps.setInt(1, sec.getSecId());
			ps.setInt(2, date);
			ResultSet rs = ps.executeQuery();
			switch (attr.datatype) {
			case N:
				EstimateSeries<Double> resn = parseNumResultSet(sec, attr, 1, asOf, rs);
				if (resn != null)
					result.put(sec, resn);
				break;
			case P:
				EstimateSeries<DistributionSummary> resd = parseDistResultSet(sec, attr, 1, asOf, rs);
				if (resd != null)
					result.put(sec, resd);
				break;
			default:
				throw new Exception("Unsupported Datatype " + attr.datatype + " in SQLEstimateWidget!");
			}

			rs.close();
		}
		ps.close();
		return result;
	}

	public Map<Security, Map<Integer, EstimateSeries<Double>>> getDetailed(Map<Security, Long> secAndDate, DbAttrType attr, long asOf, long oldest,
			boolean returnSuppressed) throws Exception {
		assert attr.dbname.endsWith("_DE");
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		String table = attr.tableref;
		String attrCode = Integer.toString(attr.code);
		String brokerid = null;
		String t1 = Long.toString(oldest);
		String t2 = Long.toString(asOf);
		String ts = Long.toString(asOf);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(queries.get(table)[1], table, attrCode, brokerid, t1, t2, ts, offset);

		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		Map<Security, Map<Integer, EstimateSeries<Double>>> result = new HashMap<Security, Map<Integer, EstimateSeries<Double>>>();
		for (Map.Entry<Security, Long> sd : secAndDate.entrySet()) {
			long millis = sd.getValue();
			int date;
			if (millis == Long.MIN_VALUE)
				date = 0;
			else {
				Time.assertDay(millis);
				date = Time.toYYYYMMDD(millis);
			}

			Security sec = sd.getKey();
			ps.setInt(1, sec.getSecId());
			ps.setInt(2, date);
			ResultSet rs = ps.executeQuery();

			switch (attr.datatype) {
			case N:
				Map<Integer, EstimateSeries<Double>> resn = parseDetNumResultSet(sec, attr, asOf, rs, returnSuppressed);
				if (resn != null) {
					result.put(sec, resn);
				}
				break;
			default:
				throw new Exception("Unsupported Datatype " + attr.datatype + " in SQLEstimateWidget!");
			}
			rs.close();
		}
		ps.close();
		return result;
	}

	public Map<Security, Vector<ReutersAnnDate>> getEstimatePeriods(Set<Security> secs, DbAttrType attr, DateType type, int number, long asOf)
			throws SQLException, IOException {
		assert attr.dbname.startsWith("PERIOD");
		assert type == DateType.FUTURE || type == DateType.PAST;
		checkConnection();

		String attrCode = Integer.toString(attr.code);
		String limit = Integer.toString(number);
		String ts = Long.toString(asOf);
		String offset = Long.toString(attr.backfillOffset);
		String query = null;
		if (type == DateType.FUTURE)
			query = MessageFormat.format(futurePeriodQuery, attrCode, limit, ts, offset);
		else if (type == DateType.PAST)
			query = MessageFormat.format(pastPeriodQuery, attrCode, limit, ts, offset);

		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		Map<Security, Vector<ReutersAnnDate>> result = new HashMap<Security, Vector<ReutersAnnDate>>(secs.size());
		for (Security sec : secs) {
			Vector<ReutersAnnDate> dates = new Vector<ReutersAnnDate>(number);
			result.put(sec, dates);

			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			while (rs.next()) {
				Integer perioddate = rs.getInt(1);
				Long advdate = rs.getLong(2);
				if (rs.wasNull())
					advdate = null;
				Integer announced = rs.getInt(3);
				String status = rs.getString(4);
				Integer phase = rs.getInt(5);
				if (rs.wasNull())
					phase = null;
				Long born = rs.getLong(6);

				dates.add(new ReutersAnnDate(perioddate, announced == 1, advdate, status, phase, born));
			}
			rs.close();

		}
		ps.close();
		return result;
	}

	public Map<Security, NavigableSet<Long>> getCalendarPeriods(Set<Security> secs, DbAttrType attr, long asOf) throws SQLException, IOException {
		assert attr.dbname.startsWith("PERIOD");
		checkConnection();

		String attrCode = Integer.toString(attr.code);
		String limit = null;
		String ts = Long.toString(asOf);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(calendarQuery, attrCode, limit, ts, offset);

		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		Map<Security, NavigableSet<Long>> result = new HashMap<Security, NavigableSet<Long>>(secs.size());
		for (Security sec : secs) {
			NavigableSet<Long> dates = new TreeSet<Long>();
			result.put(sec, dates);
			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			while (rs.next()) {
				dates.add(Time.fromYYYYMMDD(rs.getInt(1)));
			}
			rs.close();

		}
		ps.close();
		return result;
	}

	public String getBrokerName(int brokerid, long asof) throws SQLException {
		PreparedStatement pst = prepare(brokerQuery);
		pst.setInt(1, brokerid);
		pst.setLong(2, asof);
		pst.setLong(3, asof);

		String brokerName = null;
		ResultSet rs = pst.executeQuery();
		if (rs.next())
			brokerName = rs.getString(1);
		rs.close();
		pst.close();
		return brokerName;
	}

	protected void preloadSplits(long asof) throws SQLException {
		log.info("Populating reuters split cache asof=" + df.debugFormat(asof));

		String query = "SELECT m.secid,x.rate,x.date  FROM cs2reuters AS m STRAIGHT_JOIN reuters_split AS x on(m.rkd=x.rkd) WHERE m.born<=%s AND (m.died IS NULL OR m.died>%s) AND x.born<=%s AND (x.died IS NULL OR x.died>%s)";
		Statement st = c.createStatement();
		splitCache.clear();
		splitCacheTs = asof;

		ResultSet rs = st.executeQuery(String.format(query, asof, asof, asof, asof));
		while (rs.next()) {
			int secid = rs.getInt(1);
			double rate = rs.getDouble(2);
			long date = Time.fromYYYYMMDD(rs.getInt(3));

			NavigableMap<Long, Double> splits = splitCache.get(secid);
			if (splits == null)
				splitCache.put(secid, splits = new TreeMap<Long, Double>());
			splits.put(date, rate);
		}
		rs.close();
		st.close();
	}

	public Double getSplitAdjRate(Security sec, long date, long asof) throws SQLException {
		Time.assertDay(date);
		if (asof != splitCacheTs)
			preloadSplits(asof);

		NavigableMap<Long, Double> splits = splitCache.get(sec.getSecId());
		if (splits == null)
			return 1.0;
		splits = splits.subMap(date, false, asof, true);
		Double rate = 1.0;
		for (Double s : splits.values())
			rate *= s;
		return rate;
	}

	public static void main(String[] args) {
		try {
			Security sec = new Security(Integer.parseInt(args[0]));
			DbAttrType attrType = new DbAttrType(args[1]);
			int intDate = Integer.parseInt(args[2]);
			boolean lags = args.length > 3 && args[3].equals("lags");

			long date;

			if (intDate == 0) {
				date = Long.MIN_VALUE;
			}
			else {
				date = Time.fromYYYYMMDD(intDate);
			}

			SQLEstimateWidget estWidget = instance();

			if (attrType.name.endsWith("_DE")) {
				Map<Security, Map<Integer, EstimateSeries<Double>>> secPastMap = estWidget.getDetailed(
						associateSecidsWithDates(CollectionUtils.toSet(sec), date), attrType, Time.now(), Time.now() - 3 * 365 * Time.MILLIS_PER_DAY, true);
				Map<Integer, EstimateSeries<Double>> brokerMap = secPastMap.get(sec);
				for (Integer broker : new TreeSet<Integer>(brokerMap.keySet())) {
					EstimateSeries<Double> series = brokerMap.get(broker);
					System.out.println("Broker: " + estWidget.getBrokerName(broker, Time.now()));
					System.out.println(series.toString());
					series.printSeries();
					if (lags) {
						System.out.println("LAGS");
						for (int lag = 0; lag < series.size(); lag++) {
							System.out.println(series.getLaggedDailyEstimate(lag));
						}
					}
					System.out.println("");
				}
			}
			else if (attrType.name.endsWith("_CE")) {
				Map<Security, EstimateSeries<?>> secMap = estWidget.getConsensus(associateSecidsWithDates(CollectionUtils.toSet(sec), date), attrType,
						Time.now(), Time.now() - 3 * 365 * Time.MILLIS_PER_DAY);
				for (EstimateSeries<?> s : secMap.values()) {
					EstimateSeries<DistributionSummary> series = (EstimateSeries<DistributionSummary>) s;
					System.out.println(series.toString());
					series.printSeries();
					if (lags) {
						System.out.println("LAGS");
						for (int lag = 0; lag < series.size(); lag++) {
							System.out.println(series.getLaggedDailyEstimate(lag));
						}
					}
				}
			}
		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}
}
