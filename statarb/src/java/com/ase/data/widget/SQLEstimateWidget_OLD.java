package ase.data.widget;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.FileReader;
import java.io.IOException;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
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

public class SQLEstimateWidget_OLD extends SQLWidget {
	// ////////////////////////////

	public enum DateType {
		PAST, // date of estimate < "date"
		PRESENT, // date of estimate == "date"
		FUTURE; // date of estimate is > "date"
	}

	// ///////////////////////////

	private enum QueryType {
		CONSENSUS, DETAILED;
	}

	// ////////////////////////////

	private static SQLEstimateWidget_OLD instance = null;

	public static final SQLEstimateWidget_OLD instance() {
		if (instance == null) {
			instance = new SQLEstimateWidget_OLD();
		}
		return instance;
	}

	@Override
	protected void uponReconnect() {
		// TODO Auto-generated method stub
	}

	// /XXX Right now date subquery gets quarter dates simply chronologically.
	// In the future we might want to update this so it points to the next
	// UNANNOUNCED quarter after date or previous ANNOUNCED
	// /XXX Now it points to the next/prev date for which we have EPS_Q_CE data
	private static String single_date_subquery = "(SELECT x.rkd,x.date,x.type,x.brokerid FROM cs2reuters AS m STRAIGHT_JOIN %s AS x on(m.rkd=x.rkd) WHERE m.secid=? AND m.born<=? AND (m.died IS NULL OR m.died>?) AND x.date%s? AND x.orig<=? AND x.born<=? AND (x.died IS NULL OR x.died>?) AND x.type=? AND x.brokerid=? ORDER BY x.date %s LIMIT 1)";
	private static String neq_single_query = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born,IFNULL(f.died,9223372036854775807) FROM %s AS d STRAIGHT_JOIN %s AS e ON (d.rkd=e.rkd AND d.date=e.date AND d.type=e.type AND d.brokerid=e.brokerid) LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig) WHERE e.born<=? AND (e.died IS NULL OR e.died>?) AND e.orig<=? AND e.orig>? ORDER BY e.orig ASC,f.orig2 ASC,f.born ASC";
	private static String eq_single_query = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born,IFNULL(f.died,9223372036854775807) FROM cs2reuters AS m STRAIGHT_JOIN %s AS e ON (m.rkd=e.rkd) LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig) WHERE m.secid=? AND m.born<=? AND (m.died IS NULL OR m.died>?) AND e.date=? AND e.type=? AND e.brokerid=? AND e.born<=? AND (e.died IS NULL OR e.died>?) AND e.orig<=? AND e.orig>? ORDER BY e.orig ASC,f.orig2 ASC,f.born ASC";
	private static String all_date_subquery = "(SELECT x.rkd,x.date,x.type FROM cs2reuters AS m STRAIGHT_JOIN %s as x on(m.rkd=x.rkd) WHERE m.secid=? AND m.born<=? AND (m.died IS NULL OR m.died>?) AND x.date%s? AND x.orig<=? AND x.born<=? AND (x.died IS NULL OR x.died>?) AND x.type=? ORDER BY x.date %s LIMIT 1)";
	private static String neq_all_query = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born,IFNULL(f.died,9223372036854775807),e.brokerid FROM %s AS d STRAIGHT_JOIN %s AS e ON (d.rkd=e.rkd AND d.date=e.date AND d.type=e.type) LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig) WHERE e.born<=? AND (e.died IS NULL OR e.died>?) AND e.orig<=? AND e.orig>? ORDER BY e.brokerid ASC,e.orig ASC,f.orig2 ASC,f.born ASC";
	private static String eq_all_query = "SELECT e.date,e.value,e.currency,e.orig,e.born,f.orig2,f.flag,f.born,IFNULL(f.died,9223372036854775807),e.brokerid FROM cs2reuters AS m STRAIGHT_JOIN %s AS e ON (m.rkd=e.rkd) LEFT JOIN co_estimate_flags as f ON(e.rkd=f.rkd AND e.type=f.type AND e.brokerid=f.brokerid AND e.date=f.date AND e.orig=f.orig) WHERE m.secid=? AND m.born<=? AND (m.died IS NULL OR m.died>?) AND e.date=? AND e.type=? AND e.born<=? AND (e.died IS NULL OR e.died>?) AND e.orig<=? AND e.orig>? ORDER BY e.brokerid ASC,e.orig ASC,f.orig2 ASC,f.born ASC";

	private static String co_estimates_n_geq = String.format(neq_single_query, String.format(single_date_subquery, "co_estimates_n", ">=", "ASC"),
			"co_estimates_n");
	private static String co_estimates_n_leq = String.format(neq_single_query, String.format(single_date_subquery, "co_estimates_n", "<=", "DESC"),
			"co_estimates_n");
	private static String co_estimates_n_eq = String.format(eq_single_query, "co_estimates_n");
	private static String co_estimates_b_geq = String.format(neq_single_query, String.format(single_date_subquery, "co_estimates_b", ">=", "ASC"),
			"co_estimates_b");
	private static String co_estimates_b_leq = String.format(neq_single_query, String.format(single_date_subquery, "co_estimates_b", "<=", "DESC"),
			"co_estimates_b");
	private static String co_estimates_b_eq = String.format(eq_single_query, "co_estimates_b");
	private static String co_estimates_n_geq_det = String.format(neq_all_query, String.format(all_date_subquery, "co_estimates_n", ">=", "ASC"),
			"co_estimates_n");
	private static String co_estimates_n_leq_det = String.format(neq_all_query, String.format(all_date_subquery, "co_estimates_n", "<=", "DESC"),
			"co_estimates_n");
	private static String co_estimates_n_eq_det = String.format(eq_all_query, "co_estimates_n");

	private static String periodQuery = "SELECT x.perioddate,x.advdate,x.announced,x.status,x.phase,x.born FROM cs2reuters AS m STRAIGHT_JOIN reuters_period AS x on(m.rkd=x.rkd) WHERE m.secid=? AND x.type=? AND x.announced=%s AND m.born<=? AND (m.died IS NULL OR m.died>?) AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY x.perioddate %s LIMIT ?";
	private static String futurePeriodQuery = String.format(periodQuery, "0", "ASC");
	private static String pastPeriodQuery = String.format(periodQuery, "1", "DESC");
	private static String calendarQuery = "SELECT x.perioddate FROM cs2reuters AS m STRAIGHT_JOIN reuters_period AS x on(m.rkd=x.rkd) WHERE m.secid=? AND x.type=? AND m.born<=? AND (m.died IS NULL OR m.died>?) AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY x.perioddate ASC";

	private static String brokerQuery = "SELECT name FROM brokers WHERE brokerid=? AND source=17 AND born<=? AND (died IS NULL OR died>?)";

	private static String splitQuery = "SELECT x.rate,x.date  FROM cs2reuters AS m STRAIGHT_JOIN reuters_split AS x on(m.rkd=x.rkd) WHERE m.secid=%s AND m.born<=%s AND (m.died IS NULL OR m.died>%s) AND x.date<=%s AND x.date>%s AND x.born<=%s AND (x.died IS NULL OR x.died>%s)";
	
	/// CACHING OF SPLITS ////
	private HashMap<Integer, NavigableMap<Long, Double>> splitCache = new HashMap<Integer, NavigableMap<Long,Double>>();
	private long splitCacheTs = Long.MIN_VALUE;
	
	private static Map<String, String[][]> queries = new HashMap<String, String[][]>() {
		{
			put("co_estimates_n", new String[][] { { co_estimates_n_leq, co_estimates_n_eq, co_estimates_n_geq },
					{ co_estimates_n_leq_det, co_estimates_n_eq_det, co_estimates_n_geq_det } });
			put("co_estimates_b", new String[][] { { co_estimates_b_leq, co_estimates_b_eq, co_estimates_b_geq }, { null, null, null } });
			put("reuters_period", new String[][] { { pastPeriodQuery, null, futurePeriodQuery }, { null, null, null } });
		}
	};

	private static void setupQuery(PreparedStatement ps, QueryType queryType, DateType type, DbAttrType attr, long date, long asOf, long oldest)
			throws SQLException {
		String dbname = attr.dbname;
		int attrCode = SQLResolutionWidget.instance().getAttributeCode(dbname);

		int day;
		if (date == Long.MIN_VALUE)
			day = 0;
		else
			day = Time.toYYYYMMDD(date);

		if (type == DateType.PRESENT) {
			int i = 2;
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setInt(i++, day);
			ps.setInt(i++, attrCode);
			if (queryType == QueryType.CONSENSUS)
				ps.setInt(i++, 1);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setLong(i++, oldest);
		}
		else {
			int i = 2;
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setInt(i++, day);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setInt(i++, attrCode);
			if (queryType == QueryType.CONSENSUS)
				ps.setInt(i++, 1);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setLong(i++, asOf);
			ps.setLong(i++, oldest);
		}
	}

	public EstimateSeries<Double> parseNumResultSet(Security sec, DbAttrType attr, int brokerid, long asOf, ResultSet rs) throws SQLException {
		EstimateSeries<Double> series = null;
		Estimate<Double> oldInstance = null;
		while (rs.next()) {
			// ////// WARNING!!!!!!!!!!! decide if date will be long or double
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
			long died2 = rs.getLong(9);

			if (flag == null || !(born2 <= asOf && died2 > asOf))
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
			long died2 = rs.getLong(9);

			if (flag == null || !(born2 <= asOf && died2 > asOf))
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

			int brokerid = rs.getInt(10);
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
			long died2 = rs.getLong(9);

			if (flag == null || !(born2 <= asOf && died2 > asOf))
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

	// date,asOf,oldest are in millis. However, mysql stores dates as ints
	// (20110201). Using Time.toYYYYMMDD
	// to do the conversion
	public Map<Security, EstimateSeries<?>> get(Set<Security> secs, DbAttrType attr, DateType type, long date, long asOf, long oldest) throws Exception {
		assert attr.dbname.endsWith("_CE");
		if (date != Long.MIN_VALUE)
			Time.assertDay(date);
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		PreparedStatement ps = prepare(queries.get(attr.tableref)[QueryType.CONSENSUS.ordinal()][type.ordinal()]);
		setupQuery(ps, QueryType.CONSENSUS, type, attr, date, asOf, oldest);

		Map<Security, EstimateSeries<?>> result = new HashMap<Security, EstimateSeries<?>>();

		for (Security sec : secs) {
			ps.setInt(1, sec.getSecId());
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

	// date,asOf,oldest are in millis. However, mysql stores dates as ints
	// (20110201). Using Time.toYYYYMMDD
	// to do the conversion
	public Map<Security, EstimateSeries<?>> get(Map<Security, Attribute> secAndDate, DbAttrType attr, long asOf, long oldest) throws Exception {
		assert attr.dbname.endsWith("_CE");
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		PreparedStatement ps = prepare(queries.get(attr.tableref)[QueryType.CONSENSUS.ordinal()][DateType.PRESENT.ordinal()]);
		setupQuery(ps, QueryType.CONSENSUS, DateType.PRESENT, attr, 0, asOf, oldest);

		Map<Security, EstimateSeries<?>> result = new HashMap<Security, EstimateSeries<?>>();

		for (Map.Entry<Security, Attribute> sd : secAndDate.entrySet()) {
			Time.assertDay(sd.getValue().asDate());
			Security sec = sd.getKey();
			ps.setInt(1, sec.getSecId());
			ps.setInt(4, Time.toYYYYMMDD(sd.getValue().asDate()));
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

	public Map<Security, Map<Integer, EstimateSeries<Double>>> getDetailed(Map<Security, Attribute> secAndDate, DbAttrType attr, long asOf, long oldest,
			boolean returnSuppressed) throws Exception {
		assert attr.dbname.endsWith("_DE");
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		PreparedStatement ps = prepare(queries.get(attr.tableref)[QueryType.DETAILED.ordinal()][DateType.PRESENT.ordinal()]);
		setupQuery(ps, QueryType.DETAILED, DateType.PRESENT, attr, 0, asOf, oldest);

		Map<Security, Map<Integer, EstimateSeries<Double>>> result = new HashMap<Security, Map<Integer, EstimateSeries<Double>>>();
		for (Map.Entry<Security, Attribute> sd : secAndDate.entrySet()) {
			Time.assertDay(sd.getValue().asDate());
			Security sec = sd.getKey();
			ps.setInt(1, sec.getSecId());
			ps.setInt(4, Time.toYYYYMMDD(sd.getValue().asDate()));
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

	public Map<Security, Map<Integer, EstimateSeries<Double>>> getDetailed(Set<Security> secs, DbAttrType attr, DateType type, long date, long asOf,
			long oldest, boolean returnSuppressed) throws Exception {
		assert attr.dbname.endsWith("_DE");
		if (date != Long.MIN_VALUE)
			Time.assertDay(date);
		// Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();

		PreparedStatement ps = prepare(queries.get(attr.tableref)[QueryType.DETAILED.ordinal()][type.ordinal()]);
		setupQuery(ps, QueryType.DETAILED, type, attr, date, asOf, oldest);

		Map<Security, Map<Integer, EstimateSeries<Double>>> result = new HashMap<Security, Map<Integer, EstimateSeries<Double>>>();
		for (Security sec : secs) {
			ps.setInt(1, sec.getSecId());
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
		checkConnection();

		PreparedStatement ps = prepare(queries.get(attr.tableref)[0][type.ordinal()]);
		int i = 2;
		ps.setInt(i++, attr.code);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);
		ps.setInt(i++, number);

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

		PreparedStatement ps = prepare(calendarQuery);
		int i = 2;
		ps.setInt(i++, attr.code);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);
		ps.setLong(i++, asOf);

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

	public static void benchmark() throws Exception {
		Properties config = new Properties();
		String configFile = System.getenv("CONFIG_DIR") + "/" + "calc.cfg";
		config.load(new FileReader(configFile));
		Universe uni = new Universe(config, System.getenv("RUN_DIR"), Time.now());

		SQLEstimateWidget_OLD w = SQLEstimateWidget_OLD.instance();
		PerformanceTimer timer = new PerformanceTimer();
		timer.start();
		// w.get(uni.secs, new DbAttrType("EPS_Q_DE"), DateType.FUTURE,
		// df.parse("20100101"), df.parse("20100101"), df.parse("20090601"),
		// true);
		w.getDetailed(CollectionUtils.toSet(new Security(5334)), new DbAttrType("EPS_Q_DE"), DateType.FUTURE, df.parse("20100101"), df.parse("20100101"),
				df.parse("20090601"), true);
		timer.end();
		System.out.println(timer.avgTimeInMillis());
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
		log.info("Populating reuters split cache asof="+df.debugFormat(asof));
		
		String query = "SELECT m.secid,x.rate,x.date  FROM cs2reuters AS m STRAIGHT_JOIN reuters_split AS x on(m.rkd=x.rkd) WHERE m.born<=%s AND (m.died IS NULL OR m.died>%s) AND x.born<=%s AND (x.died IS NULL OR x.died>%s)";
		Statement st=c.createStatement();
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

			SQLEstimateWidget_OLD estWidget = instance();

			if (attrType.name.endsWith("_DE")) {
				Map<Security, Map<Integer, EstimateSeries<Double>>> secPastMap = estWidget.getDetailed(CollectionUtils.toSet(sec), attrType,
						SQLEstimateWidget_OLD.DateType.PRESENT, date, Time.now(), Time.now() - 3 * 365 * Time.MILLIS_PER_DAY, true);
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
				Map<Security, EstimateSeries<?>> secMap = estWidget.get(CollectionUtils.toSet(sec), attrType, SQLEstimateWidget_OLD.DateType.PRESENT, date,
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
