package ase.data.widget;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;

import ase.data.Currency;
import ase.data.Estimate;
import ase.data.Security;
import ase.util.Pair;
import ase.util.Time;

public class SQLCurrencyWidget extends SQLWidget {

	// /// SINGLETON////
	private static SQLCurrencyWidget instance;

	public static SQLCurrencyWidget instance() {
		if (instance == null) {
			instance = new SQLCurrencyWidget();
		}
		return instance;
	}

	protected static String query_asof = "SELECT x2.rate/x1.rate, x1.date " + "FROM exrate x1, exrate x2 "
			+ "WHERE x1.currency=%s AND x2.currency=%s AND x1.date=x2.date AND x1.date<=%s AND x1.date>=%s AND x1.died IS NULL AND x2.died IS NULL "
			+ "ORDER BY x1.date DESC LIMIT 1";

	// ////// CACHING ///////////
	protected static boolean USE_CACHING = true;
	protected HashMap<Currency, NavigableMap<Long, Double>> cache = new HashMap<Currency, NavigableMap<Long, Double>>();

	// //////////////////////////

	public SQLCurrencyWidget() {
		if (USE_CACHING) {
			for (Currency currency : Currency.values()) {
				if (currency != Currency.NA)
					try {
						preload(currency);
					}
					catch (SQLException e) {
						log.severe(e.getMessage());
						log.severe("Disabling caching");
						USE_CACHING = false;
					}
			}
		}
	}

	protected void preload(Currency currency) throws SQLException {
		Statement st = c.createStatement();
		ResultSet rs = st.executeQuery("SELECT date, rate FROM exrate WHERE currency=" + currency.getCode());
		NavigableMap<Long, Double> series = new TreeMap<Long, Double>();
		while (rs.next()) {
			int date = rs.getInt(1);
			double rate = rs.getDouble(2);
			series.put(Time.fromYYYYMMDD(date), rate);
		}
		cache.put(currency, series);
	}

	public Pair<Long, Double> convert(Currency from, Currency to, long date, long oldest) throws SQLException {
		if (USE_CACHING && cache.containsKey(from) && cache.containsKey(to))
			return cacheConvert(from, to, date, oldest);
		else
			return dbConvert(from, to, date, oldest);
	}

	public Double convert(Currency from, Currency to, long date) throws SQLException {
		if (USE_CACHING && cache.containsKey(from) && cache.containsKey(to)) {
			Pair<Long, Double> p = cacheConvert(from, to, date, date - 7 * Time.MILLIS_PER_DAY);
			return p != null ? p.second : null;
		}
		else {
			Pair<Long, Double> p = dbConvert(from, to, date, date - 7 * Time.MILLIS_PER_DAY);
			return p != null ? p.second : null;
		}
	}

	protected Pair<Long, Double> cacheConvert(Currency from, Currency to, long date, long oldest) {
		NavigableMap<Long, Double> fromSeries = cache.get(from);
		if (fromSeries == null) {
			log.severe("Currency " + from + " not present in cache");
			return null;
		}

		NavigableMap<Long, Double> toSeries = cache.get(to);
		if (to == null) {
			log.severe("Currency " + to + " not present in cache");
			return null;
		}

		// Easy case, get floor for both maps
		Map.Entry<Long, Double> fe = fromSeries.floorEntry(date);
		Map.Entry<Long, Double> te = toSeries.floorEntry(date);

		if (fe.getKey() < oldest || te.getKey() < oldest)
			return null;
		if (fe.getKey().equals(te.getKey()))
			return new Pair<Long, Double>(fe.getKey(), te.getValue() / fe.getValue());

		// hard case, find a matching date
		// lazy for now return null;
		log.severe("Some lazy bastard should go ahead and implement this. You know who you are.");
		return null;
	}

	protected Pair<Long, Double> dbConvert(Currency from, Currency to, long date, long oldest) throws SQLException {
		Statement st = c.createStatement();
		ResultSet rs = st.executeQuery(String.format(query_asof, from.getCode(), to.getCode(), Time.toYYYYMMDD(date), Time.toYYYYMMDD(date)));
		Pair<Long, Double> p = null;
		if (rs.next())
			p = new Pair<Long, Double>(Time.fromYYYYMMDD(rs.getInt(2)), rs.getDouble(1));
		rs.close();
		st.close();
		return p;
	}

	public Double estimateToUSD(Security sec, Estimate<?> est, boolean convert) throws SQLException {
		if (est.currency == Currency.USD)
			return 1.0;
		if (est.currency == null) {
			log.warning("Null currency for secid=" + sec.getSecId() + " and estimate=" + est.toString());
			return null;
		}
		if (est.currency == Currency.NA) {
			log.warning("NA currency for secid=" + sec.getSecId() + " and estimate=" + est.toString());
			return null;
		}
		if (!convert && est.currency != Currency.USD) {
			log.warning("Not convert currency " + est.currency + " for secid=" + sec.getSecId() + " and estimate=" + est.toString());
			return null;
		}

		log.info("Converting currency " + est.currency + " for secid=" + sec.getSecId() + " and estimate=" + est.toString());
		long date = Time.today(est.orig) - Time.MILLIS_PER_DAY;
		Pair<Long, Double> ex = convert(est.currency, Currency.USD, date, date - 7 * Time.MILLIS_PER_DAY);
		if (ex == null) {
			log.warning("Failed to translate currency!");
			return null;
		}
		log.info("AdjRate=" + ex.second);
		return ex.second;
	}

	@Override
	protected void uponReconnect() {
	}

	public static void main(String[] args) throws SQLException {
		SQLCurrencyWidget widget = instance();
		long date = Time.today(Time.now());
		Double p = widget.convert(Currency.USD, Currency.EUR, date);
		System.out.println(p);
		Currency c = Currency.CAD;
		System.out.println(c == Currency.CAD);
		System.out.println(null == c);
	}
}
