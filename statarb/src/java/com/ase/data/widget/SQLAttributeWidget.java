package ase.data.widget;

import java.io.FileReader;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.text.MessageFormat;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Properties;
import java.util.Set;
import java.util.TreeMap;

import ase.calculator.BarraCalculator;
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

public class SQLAttributeWidget extends SQLWidget {
	private static SQLAttributeWidget instance = null;

	public static final SQLAttributeWidget instance() {
		if (instance == null) {
			instance = new SQLAttributeWidget();
		}
		return instance;
	}

	//CONVENTIONS: {0} table, {1} attr type, {2} date >=, {3} date <, {4} asof, {5} backfill offset
	
	// COMPANY TABLES
	// CO_ATTR_*
	private static final String range_co_attr = "SELECT a.date, a.value, a.born\n"
			+ "FROM stock as s STRAIGHT_JOIN {0} as a ON (s.coid=a.coid)\n"
			+ "WHERE s.secid=? AND a.type={1} AND a.date>={2} AND a.date<{3} AND (a.born+a.backfill*{5})<={4} AND (a.died IS NULL OR (a.died+a.backfill*{5})>{4})\n"
			+ "ORDER BY a.date DESC, a.born DESC";
	private static final String upcoming_co_attr = "SELECT a.date, a.value, a.born+a.backfill*{5}\n"
			+ "FROM stock as s STRAIGHT_JOIN {0} as a ON (s.coid=a.coid)\n"
			+ "WHERE s.secid=? AND a.type={1} AND a.date>={2} AND (a.born+a.backfill*{5})<={4} AND (a.died IS NULL OR (a.died+a.backfill*{5})>{4})\n"
			+ "ORDER BY a.date ASC LIMIT 1";
	private static final String single_co_attr = range_co_attr + "\nLIMIT 1";

	// CO_ACTUALS_*
	private static final String range_co_actuals = "SELECT a.date, a.value, a.currency, a.born\n"
			+ "FROM cs2reuters as ref STRAIGHT_JOIN {0} as a ON (ref.rkd=a.rkd)\n"
			+ "WHERE ref.secid=? AND ref.born<={4} AND (ref.died IS NULL OR ref.died>{4}) AND a.type={1} AND a.date>={2} AND a.date<{3} AND (a.born+a.backfill*{5})<={4} AND (a.died IS NULL OR (a.died+a.backfill*{5})>{4})\n"
			+ "ORDER BY a.date DESC, a.born DESC";
	private static final String single_co_actuals = range_co_actuals + "\nLIMIT 1";

	// BARRA_*
	private static final String range_barra = "SELECT data.date, data.value, data.born\n"
			+ "FROM cs2barra as ref STRAIGHT_JOIN {0} as data ON (ref.barraid=data.barraid AND data.date>=ref.born AND data.date<IFNULL(ref.died,9223372036854775807))\n"
			+ "WHERE ref.secid=? AND data.type={1} AND data.date>={2} AND data.date<{3} AND (data.born+data.backfill*{5})<={4} AND (data.died IS NULL OR (data.died+data.backfill*{5})>{4})\n"
			+ "ORDER BY data.date DESC, data.born DESC";
	private static final String single_barra = range_barra + "\nLIMIT 1";

	// NEWSCOPE
	private static final String range_newsscope = "SELECT data.date, data.value, data.born\n"
			+ "FROM cs2rics as ref STRAIGHT_JOIN {0} AS data ON (ref.value = data.ric AND data.date >= ref.born AND data.date < IFNULL(ref.died,9223372036854775807))\n"
			+ "WHERE ref.secid=? AND data.type={1} AND data.date>={2} AND data.date<{3} AND (data.born+data.backfill*{5})<={4} AND (data.died IS NULL OR (data.died+data.backfill*{5})>{4})\n"
			+ "ORDER BY data.date DESC, data.born DESC";
	private static final String single_newsscope = range_newsscope + "\nLIMIT 1";

	// MUS
	private static final String range_mus = "SELECT date, value, date\n" + "FROM {0}\n" + "WHERE secid=? AND type={1} AND date>={2} AND date<{3}\n"
			+ "ORDER by date DESC";
	private static final String single_mus = range_mus + "\nLIMIT 1";

	// SECURITY TABLES
	private static final String range_sec_attr = "SELECT a.date, a.value, a.born\n"
			+ "FROM {0} as a\n"
			+ "WHERE a.secid=? AND a.type={1} AND a.date>={2} AND a.date<{3} AND (a.born+a.backfill*{5})<={4} AND (a.died IS NULL OR (a.died+a.backfill*{5})>{4})\n"
			+ "ORDER BY a.date DESC, a.born DESC";
	private static final String single_sec_attr = range_sec_attr + "\nLIMIT 1";
	private static final String upcoming_sec_attr = "SELECT a.date, a.value, a.born+a.backfill*{5}\n" + "FROM {0} as a\n"
			+ "WHERE a.secid=? AND a.type={1} AND a.date>={2} AND (a.born+a.backfill*{5})<={4} AND (a.died IS NULL OR (a.died+a.backfill*{5})>{4})\n"
			+ "ORDER BY a.date ASC LIMIT 1";

	private static Map<String, String[]> queries = new HashMap<String, String[]>() {
		{
			put("co_actuals_n", new String[] { single_co_actuals, range_co_actuals });
			put("co_actuals_d", new String[] { single_co_actuals, range_co_actuals });

			put("co_attr_n", new String[] { single_co_attr, range_co_attr, upcoming_co_attr });
			put("co_attr_d", new String[] { single_co_attr, range_co_attr, upcoming_co_attr });
			put("co_attr_s", new String[] { single_co_attr, range_co_attr, upcoming_co_attr });

			put("sec_attr_n", new String[] { single_sec_attr, range_sec_attr, upcoming_sec_attr });
			put("sec_attr_d", new String[] { single_sec_attr, range_sec_attr, upcoming_sec_attr });
			put("sec_attr_s", new String[] { single_sec_attr, range_sec_attr, upcoming_sec_attr });

			put("barra_n", new String[] { single_barra, range_barra });
			put("barra_s", new String[] { single_barra, range_barra });

			put("newsscope_attr", new String[] { single_newsscope, range_newsscope });

			put("mus", new String[] { single_mus, range_mus });
		}
	};

	// //////////FIELDS//////////////

	private SQLAttributeWidget() {
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

		String table = attr.tableref;
		boolean intDate = attr.tableref.startsWith("co_actuals");
		String attrCode = Integer.toString(attr.code);
		String t1 = intDate ? df.toYYYYMMDD(oldest) : Long.toString(oldest);
		String t2 = intDate ? df.toYYYYMMDD(asof) : Long.toString(asof);
		String ts = Long.toString(asof);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(queries.get(table)[0], table, attrCode, t1, t2, ts, offset);
		
		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		int cnt = 0;
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

		log.info("Getting *upcoming* " + attr + " asof " + asof + " (" + df.format(asof) + ") on " + secs.size() + " securities.");

		String table = attr.tableref;
		boolean intDate = false;
		String attrCode = Integer.toString(attr.code);
		String t1 = intDate ? df.toYYYYMMDD(asof) : Long.toString(asof);
		String t2 = null;
		String ts = Long.toString(asof);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(queries.get(table)[2], table, attrCode, t1, t2, ts, offset);
		
		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);
		
		int cnt = 0;
		for (Security sec : secs) {
			ps.setInt(1, sec.getSecId());
			ResultSet rs = ps.executeQuery();
			ResultSetMetaData rsm = rs.getMetaData();
			boolean haveCurrency = (rsm.getColumnCount() == 4);

			// there should be only one. NOTE THE IF
			if (rs.next()) {
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
		
		String table = attr.tableref;
		boolean intDate = attr.tableref.startsWith("co_actuals");
		String attrCode = Integer.toString(attr.code);
		String t1 = intDate ? df.toYYYYMMDD(oldest) : Long.toString(oldest);
		String t2 = intDate ? df.toYYYYMMDD(millis2) : Long.toString(millis2);
		String ts = Long.toString(millis2);
		String offset = Long.toString(attr.backfillOffset);
		String query = MessageFormat.format(queries.get(table)[1], table, attrCode, t1, t2, ts, offset);
		
		log.info("Issuing query:\n" + query);
		PreparedStatement ps = prepare(query);

		// /XXX Some benchmarking may be needed for this. I think it turns out
		// to be a bad idea
		// /as the db rather than directly sending results, creates tmp tables
		// in memory and then sends
		//ps.setFetchSize(250);

		int cnt = 0;
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

		SQLAttributeWidget w = new SQLAttributeWidget();
		PerformanceTimer timer = new PerformanceTimer();

		timer.start();
		Map<Security, NavigableMap<Long, Attribute>> res2 = w.getRange(uni.secs, BarraCalculator.B_BETA, df.parse("20100101"), df.parse("20110101"), 1);
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
//			SQLAttributeWidget_EXP w = new SQLAttributeWidget_EXP();
//
//			Security sec = new Security(5334);
//			// Attribute att1 = w.getUpcoming(CollectionUtils.toSet(sec), new DbAttrType("FUTURE_ANN_DATE", "FUTURE_ANN_DATE", 0, 10), Time.now()).get(sec);
//			// System.out.println(att1);
//
//			Attribute att2 = w.get(CollectionUtils.toSet(sec), new DbAttrType("RNEWS_TOTAL", "RNEWS_TOTAL", 0, 20, Time.fromMinutes(1)), Time.now(), 0)
//					.get(sec);
//			System.out.println(att2);
//
//			// NavigableMap<Long, Attribute> res = w.getRange(CollectionUtils.toSet(sec), new DbAttrType("IBQ"), df.dfShort.parse("20100101").getTime(),
//			// Time.now()).get(sec);
//			// for (Map.Entry<Long, Attribute> e : res.entrySet()) {
//			// System.out.println(df.dfHumanShort.format(e.getKey()) + " " + e.getValue().toString());
//			// }

		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}
}
