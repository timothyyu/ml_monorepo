package ase.data.widget;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.Vector;

import ase.data.Country;
import ase.data.Currency;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.Stock;
import ase.data.XRef;
import ase.util.CollectionUtils;
import ase.util.Time;
import ase.util.Triplet;

public class SQLSecurityWidget extends SQLWidget {

	// ////////// CACHING ///////////////////

	private static boolean USE_CACHING = true;
	private static Map<Triplet<Integer, XRef, Security>, String> sec2xrefCache = new HashMap<Triplet<Integer, XRef, Security>, String>();
	private static Map<Triplet<Integer, XRef, String>, Security> xref2secCache = new HashMap<Triplet<Integer, XRef, String>, Security>();
	// /////////////////////////////////////

	private static SQLSecurityWidget instance = null;

	private SQLSecurityWidget() {
		super();
	}

	public static SQLSecurityWidget instance() {
		if (instance == null) {
			instance = new SQLSecurityWidget();
		}
		return instance;
	}

	protected void uponReconnect() {
	}

	//XXX WARNING: Hardcoded to have alive = true and exchange = NYSE
	public Set<Security> getStocksAsOf(Country country, Currency currency, double hp, double lp, double minadvp, long asOf, int adv_days) throws SQLException {
		assert lp < hp;
		String query = "SELECT s.secid, s.coid, s.issueid, avg(p.close * p.volume) AS advp, avg(p.close) AS price "
				+ "FROM stock s JOIN price_full p ON s.secid = p.secid "
				+ "WHERE p.died IS NULL AND p.date < ? AND p.date >= date_sub(?, INTERVAL ? DAY) AND s.country = ? AND s.currency = ? " + "GROUP BY p.secid "
				+ "HAVING advp > ? AND price > ? AND price < ?";

		stm = prepare(query);
		int i = 1;
		stm.setInt(i++, new Integer(df.formatShort(asOf)));
		stm.setInt(i++, new Integer(df.formatShort(asOf)));
		stm.setInt(i++, adv_days);
		stm.setInt(i++, country.ordinal());
		stm.setInt(i++, currency.ordinal());
		stm.setDouble(i++, minadvp);
		stm.setDouble(i++, lp);
		stm.setDouble(i++, hp);

		ResultSet rs = stm.executeQuery();
		Set<Security> res = new HashSet<Security>();
		while (rs.next()) {
			res.add(new Stock(rs.getInt(1), rs.getInt(2), rs.getString(3), Exchange.Type.NYSE, country, currency, true));
		}
		rs.close();
		stm.close();
		log.info("Loaded " + res.size() + " securities");
		return res;
	}

	@Deprecated
	//XXX WARNING: Hardcoded to have alive = true and exchange = NYSE
	public Vector<Security> getStock(int coid, String issueid, long asOf) throws SQLException {
		String query = "SELECT secid, coid, issueid, country, currency FROM stock WHERE coid = ? AND issueid = ? and born > ? AND (died IS NULL OR died < ?)";
		stm = prepare(query);
		int i = 1;
		stm.setInt(i++, new Integer(coid));
		stm.setString(i++, issueid);
		stm.setLong(i++, new Long(asOf));
		stm.setLong(i++, new Long(asOf));

		ResultSet rs = stm.executeQuery();
		Vector<Security> res = new Vector<Security>();
		while (rs.next()) {
			res.add(new Stock(rs.getInt(1), rs.getInt(2), rs.getString(3), Exchange.Type.NYSE, Country.valueOf(rs.getString(4)), Currency.valueOf(rs.getString(5)), true));
		}
		rs.close();
		stm.close();
		log.info("Loaded " + res.size() + " securities");
		return res;
	}

	public Map<Security, String> getXrefMap(Set<Security> secs, long asof, XRef xref) throws SQLException {
		Map<Security, String> res = new HashMap<Security, String>(secs.size());

		String command;
		switch (xref) {
		case CUSIP:
			command = "SELECT value FROM xref WHERE secid=? AND xref_type=1 AND source=2 AND born<=? AND (died IS NULL OR died>?)";
			break;
		case TIC:
			command = "SELECT value FROM xref WHERE secid=? AND xref_type=2 AND source=2 AND born<=? AND (died IS NULL OR died>?)";
			break;
		case SEDOL:
			command = "SELECT value FROM xref WHERE secid=? AND xref_type=3 AND (source=2 OR source=12) AND born<=? AND (died IS NULL OR died>?)";
			break;
		case ISIN:
			command = "SELECT value FROM xref WHERE secid=? AND xref_type=4 AND (source=12 OR source=3) AND born<=? AND (died IS NULL OR died>?)";
			break;
		default:
			throw new RuntimeException("getXrefMap does no yet support " + xref.toString());
		}

		PreparedStatement pst = prepare(command);
		pst.setLong(2, asof);
		pst.setLong(3, asof);
		for (Security sec : secs) {
			String value = null;
			if (USE_CACHING)
				value = sec2xrefCache.get(new Triplet<Integer, XRef, Security>(Time.toYYYYMMDD(asof), xref, sec));

			if (value == null) {
				pst.setInt(1, sec.getSecId());
				ResultSet rs = pst.executeQuery();
				if (rs.next())
					value = rs.getString(1);
				rs.close();

				if (USE_CACHING)
					sec2xrefCache.put(new Triplet<Integer, XRef, Security>(Time.toYYYYMMDD(asof), xref, sec), value);
			}

			res.put(sec, value);
		}

		pst.close();
		return res;
	}

	// XXX misses some...
	// We need a resolver in case of multiple secids. Now, prefer US and lower issueids
	public Map<String, Security> getStocksFromXref(Set<String> xrefs, XRef xref, long asof) throws SQLException {
		assert asof > 0; // asof=0 is an indication that something was not initialized...
		Map<String, Security> res = new HashMap<String, Security>();
		String command;
		switch (xref) {
		case CUSIP:
			command = "SELECT x.secid FROM xref AS x STRAIGHT_JOIN stock AS s ON(x.secid=s.secid) WHERE x.value=? AND x.xref_type=1 AND x.source=2 AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY IF(s.country=0,s.country,1000),s.issueid LIMIT 1";
			break;
		case TIC:
			command = "SELECT x.secid FROM xref AS x STRAIGHT_JOIN stock AS s ON(x.secid=s.secid) WHERE x.value=? AND x.xref_type=2 AND x.source=2 AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY IF(s.country=0,s.country,1000),s.issueid LIMIT 1";
			break;
		case SEDOL:
			command = "SELECT x.secid FROM xref AS x STRAIGHT_JOIN stock AS s ON(x.secid=s.secid) WHERE x.value=? AND x.xref_type=3 AND (x.source=2 OR x.source=12) AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY IF(s.country=0,s.country,1000),s.issueid LIMIT 1";
			break;
		case ISIN:
			command = "SELECT x.secid FROM xref AS x STRAIGHT_JOIN stock AS s ON(x.secid=s.secid) WHERE x.value=? AND x.xref_type=4 AND (x.source=3 OR x.source=12) AND x.born<=? AND (x.died IS NULL OR x.died>?) ORDER BY IF(s.country=0,s.country,1000),s.issueid LIMIT 1";
			break;
		default:
			throw new RuntimeException("getXrefMap does no yet support " + xref.toString());
		}

		PreparedStatement pst = prepare(command);
		pst.setLong(2, asof);
		pst.setLong(3, asof);
		for (String x : xrefs) {
			Security sec = null;
			if (USE_CACHING)
				sec = xref2secCache.get(new Triplet<Integer, XRef, String>(Time.toYYYYMMDD(asof), xref, x));

			if (sec == null) {
				pst.setString(1, x);
				ResultSet rs = pst.executeQuery();
				if (rs.next())
					sec = new Security(rs.getInt(1));
				rs.close();

				if (USE_CACHING)
					xref2secCache.put(new Triplet<Integer, XRef, String>(Time.toYYYYMMDD(asof), xref, x), sec);
			}
			res.put(x, sec);
		}

		pst.close();
		return res;
	}

	public Security getStockFromXref(String xref, XRef type, long asof) throws SQLException {
		return getStocksFromXref(CollectionUtils.toSet(xref), type, asof).get(xref);
	}

	public Set<Stock> loadStocks(Set<Security> secs, long asof) throws Exception {
		Set<Stock> stocks = new HashSet<Stock>();

		// /XXX put limit there as an optimization
		PreparedStatement pst = prepare("SELECT s.coid, s.issueid, s.country, s.currency, IFNULL(a.value, 'A'), IFNULL(b.value, -1) " + "FROM stock AS s "
				+ "LEFT JOIN sec_attr_s AS a ON (s.secid=a.secid AND a.born<=? AND (a.died IS NULL OR a.died>?) AND a.type=45 AND a.date=0) "
				+ "LEFT JOIN sec_attr_n AS b ON (s.secid=b.secid AND b.born<=? AND (b.died IS NULL or b.died>?) AND b.type=43 AND b.date=0) "
				+ "WHERE s.secid=? AND s.born<=? AND (s.died IS NULL OR s.died>?) LIMIT 1");

		pst.setLong(1, asof);
		pst.setLong(2, asof);
		pst.setLong(3, asof);
		pst.setLong(4, asof);
		pst.setLong(6, asof);
		pst.setLong(7, asof);


		int cnt = 0;
		for (Security sec : secs) {
			pst.setInt(5, sec.getSecId());
			ResultSet rs = pst.executeQuery();
			if (rs.next()) {
				String active = rs.getString(5);
				int exchCode = rs.getInt(6);
				Exchange.Type exch = (Exchange.Type.getExchangeType(exchCode) != null) ? Exchange.Type.getExchangeType(exchCode) : Exchange.Type.DUMMY;
				stocks.add(new Stock(sec.getSecId(), rs.getInt(1), rs.getString(2), exch, Country.getCountry(rs.getInt(3)), Currency.getCurrency(rs.getInt(4)),
						active.equals("A") ? true : false));
				cnt++;
			}
			else {
				log.warning("No stock found for secid " + sec.getSecId() + " asof " + df.debugFormat(asof));
			}
			rs.close();
		}
		pst.close();
		log.info("Retrieved " + cnt + " / " + secs.size() + " stocks");

		return stocks;
	}

	public static void main(String[] argv) {
		try {
			SQLSecurityWidget w = new SQLSecurityWidget();
			Set<Security> secs = w.getStocksAsOf(Country.US, Currency.USD, 500, 1, 100000, Time.now(), 20);
			System.out.println(secs.size());
		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}

}
