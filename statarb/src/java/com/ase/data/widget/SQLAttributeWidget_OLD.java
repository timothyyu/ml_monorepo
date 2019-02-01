package ase.data.widget;

import java.io.FileReader;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.TreeMap;

import ase.data.Attribute;
import ase.data.Currency;
import ase.data.DateAttribute;
import ase.data.DbAttrType;
import ase.data.NumericAttribute;
import ase.data.Security;
import ase.data.StringAttribute;
import ase.data.Universe;
import ase.util.CollectionUtils;
import ase.util.PerformanceTimer;
import ase.util.Time;

public class SQLAttributeWidget_OLD extends SQLWidget {
	private static SQLAttributeWidget_OLD instance = null;

	public static final SQLAttributeWidget_OLD instance() {
		if (instance == null) {
			instance = new SQLAttributeWidget_OLD();
		}
		return instance;
	}

	// COMPANY TABLES
	// CO_ATTR_*
	private static final String co_attr = "SELECT a.date, a.value, a.born " + "FROM stock as s, %s as a "
			+ "WHERE s.secid=? AND s.coid=a.coid AND a.type=? AND a.date>=? AND a.date<? AND a.born<=? AND (a.died IS NULL OR a.died>?) "
			+ "ORDER BY a.date DESC, a.born DESC";
	private static final String upcoming_co_attr = "SELECT a.date, a.value, a.born " + "FROM stock as s, %s as a "
			+ "WHERE s.secid=? AND s.coid=a.coid AND a.type=? AND a.date>=? AND a.born<=? AND (a.died IS NULL OR a.died>?) " + "ORDER BY a.date ASC LIMIT 1";
	private static final String range_co_attr_n = String.format(co_attr, "co_attr_n");
	private static final String single_co_attr_n = range_co_attr_n + " LIMIT 1";
	private static final String upcoming_co_attr_n = String.format(upcoming_co_attr, "co_attr_n");

	private static final String range_co_attr_s = String.format(co_attr, "co_attr_s");
	private static final String single_co_attr_s = range_co_attr_s + " LIMIT 1";
	private static final String upcoming_co_attr_s = String.format(upcoming_co_attr, "co_attr_s");

	private static final String range_co_attr_d = String.format(co_attr, "co_attr_d");
	private static final String single_co_attr_d = range_co_attr_d + " LIMIT 1";
	private static final String upcoming_co_attr_d = String.format(upcoming_co_attr, "co_attr_d");

	// CO_ACTUALS_*
	private static final String actuals = "SELECT a.date, a.value, a.currency, a.born "
			+ "FROM cs2reuters as ref, %s as a "
			+ "WHERE ref.secid=? AND ref.born<=? AND (ref.died IS NULL OR ref.died>?) AND ref.rkd=a.rkd AND a.type=? AND a.date>=? AND a.date<? AND a.born<=? AND (a.died IS NULL OR a.died>?) "
			+ "ORDER BY a.date DESC, a.born DESC";
	private static final String range_co_actuals_n = String.format(actuals, "co_actuals_n");
	private static final String single_co_actuals_n = range_co_actuals_n + " LIMIT 1";

	private static final String range_co_actuals_d = String.format(actuals, "co_actuals_d");
	private static final String single_co_actuals_d = range_co_actuals_d + " LIMIT 1";

	// BARRA_*
	private static final String barra = "SELECT data.date, data.value, data.born "
			+ "FROM %s as data,cs2barra as ref "
			+ "WHERE ref.secid=? AND ref.barraid=data.barraid AND data.type=? AND data.date>=ref.born AND data.date<IFNULL(ref.died,9223372036854775807) AND data.date>=? AND data.date<? AND data.born<=? AND (data.died IS NULL OR data.died>?) "
			+ "ORDER BY data.date DESC, data.born DESC";
	private static final String range_barra_n = String.format(barra, "barra_n");
	private static final String single_barra_n = range_barra_n + " LIMIT 1";

	private static final String range_barra_s = String.format(barra, "barra_s");
	private static final String single_barra_s = range_barra_s + " LIMIT 1";

	// NEWSCOPE
	private static final String newsscope = "SELECT data.date, data.value, data.born "
			+ "FROM cs2rics as ref STRAIGHT_JOIN newsscope_attr AS data ON (ref.value = data.ric AND data.date >= ref.born AND data.date < IFNULL(ref.died,9223372036854775807))"
			+ "WHERE ref.secid=? AND data.type=? AND data.date>=? AND data.date<? AND data.born<=? AND (data.died IS NULL OR data.died>?) "
			+ "ORDER BY data.date DESC, data.born DESC";
	private static final String range_newsscope = newsscope;
	private static final String single_newsscope = newsscope + " LIMIT 1";

	// MUS
	// XXX a bit hackishly introduce two extra params to compensate for the fact that there is no born and died
	private static final String range_mus = "SELECT date, value, date FROM mus WHERE secid=? AND type=? AND date>=? AND date<? AND date<? AND date<? ORDER by date DESC";
	private static final String single_mus = range_mus + " LIMIT 1";

	// SECURITY TABLES
	private static final String sec_attr = "SELECT a.date, a.value, a.born " + "FROM %s as a "
			+ "WHERE a.secid=? AND a.type=? AND a.date>=? AND a.date<? AND a.born<=? AND (a.died IS NULL OR a.died>?) " + "ORDER BY a.date DESC, a.born DESC";
	private static final String upcoming_sec_attr = "SELECT a.date, a.value, a.born " + "FROM %s as a"
			+ "WHERE a.secid=? AND a.type=? AND a.date>=? AND a.born<=? AND (a.died IS NULL OR a.died>?) " + "ORDER BY a.date ASC LIMIT 1";
	private static final String range_sec_attr_n = String.format(sec_attr, "sec_attr_n");
	private static final String single_sec_attr_n = range_sec_attr_n + " LIMIT 1";
	private static final String upcoming_sec_attr_n = String.format(upcoming_sec_attr, "sec_attr_n");

	private static final String range_sec_attr_s = String.format(sec_attr, "sec_attr_s");
	private static final String single_sec_attr_s = range_sec_attr_s + " LIMIT 1";
	private static final String upcoming_sec_attr_s = String.format(upcoming_sec_attr, "sec_attr_s");

	private static final String range_sec_attr_d = String.format(sec_attr, "sec_attr_d");
	private static final String single_sec_attr_d = range_sec_attr_d + " LIMIT 1";
	private static final String upcoming_sec_attr_d = String.format(upcoming_sec_attr, "sec_attr_d");

	private static Map<String, String[]> queries = new HashMap<String, String[]>() {
		{
			put("co_attr_n", new String[] { single_co_attr_n, range_co_attr_n, upcoming_co_attr_n });
			put("co_attr_d", new String[] { single_co_attr_d, range_co_attr_d, upcoming_co_attr_d });
			put("co_attr_s", new String[] { single_co_attr_s, range_co_attr_s, upcoming_co_attr_s });

			put("sec_attr_n", new String[] { single_sec_attr_n, range_sec_attr_n, upcoming_sec_attr_n });
			put("sec_attr_d", new String[] { single_sec_attr_d, range_sec_attr_d, upcoming_sec_attr_d });
			put("sec_attr_s", new String[] { single_sec_attr_s, range_sec_attr_s, upcoming_sec_attr_s });

			put("co_actuals_n", new String[] { single_co_actuals_n, range_co_actuals_n });
			put("co_actuals_d", new String[] { single_co_actuals_d, range_co_actuals_d });
			put("barra_n", new String[] { single_barra_n, range_barra_n });
			put("barra_s", new String[] { single_barra_s, range_barra_s });
			put("newsscope_attr", new String[] { single_newsscope, range_newsscope });
			put("mus", new String[] { single_mus, range_mus });
		}
	};

	// //////////FIELDS//////////////

	private SQLAttributeWidget_OLD() {
		super();
	}

	protected void uponReconnect() {
	}

	public Map<Security, Attribute> get(Set<Security> secs, DbAttrType attr, long asof, long oldest) throws Exception {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();
		if (attr.tableref == null) {
			log.warning("Could not look up attribute " + attr + " in database!");
			return null;
		}
		// int datatype = attr_type_cache.get(attr.dbname);

		log.info("Getting " + attr + " asof " + asof + " / " + oldest + " (" + df.format(asof) + "/" + df.format(oldest) + ") on " + secs.size()
				+ " securities.");

		PreparedStatement ps = prepare(queries.get(attr.tableref)[0]);
		int i = 2;
		if (attr.tableref.startsWith("co_actuals")) {
			ps.setLong(i++, asof);
			ps.setLong(i++, asof);
			ps.setInt(i++, attr.code);
			// ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(attr.max_age)));
			ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(oldest)));
			ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(asof)));
			ps.setLong(i++, asof);
			ps.setLong(i++, asof);
		}
		else {
			ps.setInt(i++, attr.code);
			// ps.setLong(i++, attr.max_age);
			ps.setLong(i++, oldest);
			ps.setLong(i++, asof);
			ps.setLong(i++, asof);
			ps.setLong(i++, asof);
		}

		int cnt = 0;
		boolean intDate = attr.tableref.startsWith("co_actuals");
		for (Security sec : secs) {
			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			ResultSetMetaData rsm = rs.getMetaData();
			boolean haveCurrency = (rsm.getColumnCount() == 4);

			// there should be only one. NOTE THE IF
			if (rs.next()) {
				long datumDate = intDate ? Time.fromYYYYMMDD(rs.getInt(1)) : rs.getLong(1);
				switch (attr.datatype) {
				case N:
					// if we have currency the layout is
					// date,value,currency,born. else datte,value,bron
					if (haveCurrency) {
						res.put(sec, new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), Currency.getCurrency(rs.getShort(3)), rs.getLong(4)));
					}
					else {
						res.put(sec, new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), rs.getLong(3)));
					}
					break;
				case S:
					res.put(sec, new StringAttribute(attr, sec, datumDate, rs.getString(2), rs.getLong(3)));
					break;
				case D:
					res.put(sec, new DateAttribute(attr, sec, datumDate, rs.getLong(2), rs.getLong(3)));
					break;
				default:
					throw new Exception("Unsupported Datatype " + attr.datatype + "!");
				}
				cnt++;
			}
			rs.close();
		}
		log.info("Returning " + cnt + " of attribute " + attr);
		ps.close();
		return res;
	}

	// /XXX currently implemented for tables sec_attr_* and co_attr_*
	public Map<Security, Attribute> getUpcoming(Set<Security> secs, DbAttrType attr, long asof) throws Exception {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>();
		checkConnection();
		if (attr.tableref == null) {
			log.warning("Could not look up attribute " + attr + " in database!");
			return null;
		}
		// int datatype = attr_type_cache.get(attr.dbname);

		log.info("Getting *upcoming* " + attr + " asof " + asof + " (" + df.format(asof) + ") on " + secs.size() + " securities.");

		PreparedStatement ps = prepare(queries.get(attr.tableref)[2]);
		int i = 2;
		// if (attr.tableref.startsWith("co_actuals")) {
		// ps.setLong(i++, asof);
		// ps.setLong(i++, asof);
		// ps.setInt(i++, attr.code);
		// // ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(attr.max_age)));
		// ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(oldest)));
		// ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(asof)));
		// ps.setLong(i++, asof);
		// ps.setLong(i++, asof);
		// }
		// else {
		ps.setInt(i++, attr.code);
		ps.setLong(i++, asof);
		ps.setLong(i++, asof);
		ps.setLong(i++, asof);
		// }

		int cnt = 0;
		// boolean intDate = attr.tableref.startsWith("co_actuals");
		for (Security sec : secs) {
			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			ResultSetMetaData rsm = rs.getMetaData();
			boolean haveCurrency = (rsm.getColumnCount() == 4);

			// there should be only one. NOTE THE IF
			if (rs.next()) {
				// long datumDate = intDate ? Time.fromYYYYMMDD(rs.getInt(1)) :
				// rs.getLong(1);
				long datumDate = rs.getLong(1);
				switch (attr.datatype) {
				case N:
					// if we have currency the layout is
					// date,value,currency,born. else datte,value,bron
					if (haveCurrency) {
						res.put(sec, new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), Currency.getCurrency(rs.getShort(3)), rs.getLong(4)));
					}
					else {
						res.put(sec, new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), rs.getLong(3)));
					}
					break;
				case S:
					res.put(sec, new StringAttribute(attr, sec, datumDate, rs.getString(2), rs.getLong(3)));
					break;
				case D:
					res.put(sec, new DateAttribute(attr, sec, datumDate, rs.getLong(2), rs.getLong(3)));
					break;
				default:
					throw new Exception("Unsupported Datatype " + attr.datatype + "!");
				}
				cnt++;
			}
			rs.close();
		}
		log.info("Returning " + cnt + " of attribute " + attr);
		ps.close();
		return res;
	}

	public Map<Security, NavigableMap<Long, Attribute>> getRange(Set<Security> secs, DbAttrType attr, long millis1, long millis2, long oldest) throws Exception {
		if (millis1 > millis2) {
			throw new RuntimeException("millis1 > millis2! " + millis1 + " > " + millis2);
		}

		Map<Security, NavigableMap<Long, Attribute>> res = new HashMap<Security, NavigableMap<Long, Attribute>>();
		checkConnection();
		log.info("Getting " + attr + " between [" + df.format(millis1) + "(" + millis1 + "), " + df.format(millis2) + "(" + millis2 + ")) on " + secs.size()
				+ " securities.");

		PreparedStatement ps = prepare(queries.get(attr.tableref)[1]);
		// /XXX Some benchmarking may be needed for this. I think it turns out
		// to be a bad idea
		// /as the db rather than directly sending results, creates tmp tables
		// in memory and then sends
		// ps.setFetchSize(50); // Get 50 rows at a time. normally we shouldn't
		// need many more
		int i = 2;
		if (attr.tableref.startsWith("co_actuals")) {
			ps.setLong(i++, millis2);
			ps.setLong(i++, millis2);
			ps.setInt(i++, attr.code);
			// ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(attr.max_age)));
			ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(oldest)));
			ps.setInt(i++, Integer.parseInt(df.toYYYYMMDD(millis2)));
			ps.setLong(i++, millis2);
			ps.setLong(i++, millis2);
		}
		else {
			ps.setInt(i++, attr.code);
			// ps.setLong(i++, attr.max_age);
			ps.setLong(i++, oldest);
			ps.setLong(i++, millis2);
			ps.setLong(i++, millis2);
			ps.setLong(i++, millis2);
		}

		int cnt = 0;
		boolean intDate = attr.tableref.startsWith("co_actuals");
		for (Security sec : secs) {
			TreeMap<Long, Attribute> atts = new TreeMap<Long, Attribute>();
			res.put(sec, atts);

			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			java.sql.ResultSetMetaData rsm = rs.getMetaData();
			boolean haveCurrency = (rsm.getColumnCount() == 4);

			while (rs.next()) {
				Attribute datum;
				long datumDate = intDate ? Time.fromYYYYMMDD(rs.getInt(1)) : rs.getLong(1);
				switch (attr.datatype) {
				case N:
					// if we have currency the layout is
					// date,value,currency,born. else datte,value,bron
					if (haveCurrency) {
						datum = new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), Currency.getCurrency(rs.getShort(3)), rs.getLong(4));
					}
					else {
						datum = new NumericAttribute(attr, sec, datumDate, rs.getDouble(2), rs.getLong(3));
					}
					break;
				case S:
					datum = new StringAttribute(attr, sec, datumDate, rs.getString(2), rs.getLong(3));
					break;
				case D:
					datum = new DateAttribute(attr, sec, datumDate, rs.getLong(2), rs.getLong(3));
					break;
				default:
					throw new RuntimeException("Unsupported datatype " + attr.datatype + "!");
				}

				atts.put(datumDate, datum);
				cnt++;
				// we get on older than the lower bound
				if (datum.date <= millis1) {
					break;
				}
			}
			rs.close();
		}
		ps.close();
		log.info("Returning " + cnt + " of attribute " + attr);
		return res;
	}

	private static void benchmark() throws Exception {
		Properties config = new Properties();
		String configFile = System.getenv("CONFIG_DIR") + "/" + "calc.prod.cfg";
		config.load(new FileReader(configFile));
		Universe uni = new Universe(config, System.getenv("RUN_DIR"), Time.now());

		SQLAttributeWidget_OLD w = new SQLAttributeWidget_OLD();
		PerformanceTimer timer = new PerformanceTimer();

		timer.start();
		Map<Security, NavigableMap<Long, Attribute>> res2 = w.getRange(uni.secs, new DbAttrType("MIDCAP"), df.parse("20100101"), df.parse("20110101"),
				df.parse("20090101"));
		timer.end();
		System.out.println(timer.avgTimeInMillis());

		timer.reset();
		timer.start();
		Map<Security, Attribute> res1 = w.get(uni.secs, new DbAttrType("MIDCAP"), df.parse("20110101"), df.parse("20100101"));
		timer.end();
		System.out.println(timer.avgTimeInMillis());
	}

	public static void main(String[] argv) {
		try {
			benchmark();
			// SQLAttributeWidget_OLD w = new SQLAttributeWidget_OLD();
			//
			// Security sec = new Security(5334);
			// Attribute att1 = w.getUpcoming(CollectionUtils.toSet(sec), new DbAttrType("FUTURE_ANN_DATE", "FUTURE_ANN_DATE", 0, 10), Time.now()).get(sec);
			// System.out.println(att1);
			//
			// Attribute att2 = w.get(CollectionUtils.toSet(sec), new DbAttrType("FUTURE_ANN_DATE", "FUTURE_ANN_DATE", 0, 10), Time.now(), 0).get(sec);
			// System.out.println(att2);

			// NavigableMap<Long, Attribute> res = w.getRange(CollectionUtils.toSet(sec), new DbAttrType("IBQ"), df.dfShort.parse("20100101").getTime(),
			// Time.now()).get(sec);
			// for (Map.Entry<Long, Attribute> e : res.entrySet()) {
			// System.out.println(df.dfHumanShort.format(e.getKey()) + " " + e.getValue().toString());
			// }

		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}
}
