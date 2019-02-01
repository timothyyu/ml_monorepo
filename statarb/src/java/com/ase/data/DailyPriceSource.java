package ase.data;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.widget.SQLDailyPriceWidget;
import ase.timeseries.DailyBar;
import ase.timeseries.DailyBarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class DailyPriceSource {
	private static final Logger log = LoggerFactory.getLogger(DailyPriceSource.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public final SQLDailyPriceWidget pw = SQLDailyPriceWidget.instance();

	public DailyPriceSource() {
	}

	/**
	 * If asof<MarketClose for day, do not include asof day in search. Else, include.
	 * 
	 */
	public double getLatestPrice(Security sec, long asof) throws Exception {
		return getLatestPrice(sec, asof, sec.primaryExchange);
	}

	public double getLatestPrice(Security sec, long asof, Exchange.Type exch) throws Exception {
		DailyBar db=getBarAsOf(CollectionUtils.toSet(sec), asof, sec.primaryExchange).get(sec);
		if (db == null) return Double.NaN;
		return db.close;
	}
	
	public Pair<Double,Long> getLatestPriceAndTs(Security sec, long asof) throws Exception {
		DailyBar db=getBarAsOf(CollectionUtils.toSet(sec), asof, sec.primaryExchange).get(sec);
		if (db == null) return new Pair<Double, Long>(Double.NaN, 0L);
		return new Pair<Double, Long>(db.close, db.close_ts);
	}

	/**
	 * If asof<MarketClose for day, do not include asof day in search. Else, include.
	 * 
	 */
	public Map<Security, DailyBar> getBarAsOf(Set<Security> secs, long asof, Exchange.Type exch) throws Exception {
		//this is required to include the asof day when asof=closetime
		long date = (!Exchange.isTradingDay(asof, exch) || asof < Exchange.closeTime(asof, exch))? Exchange.prevTradingDay(asof, exch) : Time.today(asof); 
		
		Map<Security, DailyBar> res = pw.getLatestPrices(secs, date, Time.addDays(date, -5), exch);
		if (res.size() != secs.size()) {
			log.warning("Retrieved " + res.size() + " out of " + secs.size());
		}
		return res;
	}

	/**
	 * Get bar time series in range [date1,date2]
	 */
	public Map<Security, DailyBarTimeSeries> getTimeSeries(Set<Security> secs, long date1, long date2, Exchange.Type exch) throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);

		Map<Security, Vector<DailyBar>> bars = pw.getPrices(secs, date1, date2 + Time.MILLIS_PER_DAY);
		Map<Security, DailyBarTimeSeries> res = new HashMap<Security, DailyBarTimeSeries>(bars.size());

		for (Map.Entry<Security, Vector<DailyBar>> ent : bars.entrySet()) {
			res.put(ent.getKey(), new DailyBarTimeSeries(ent.getValue(), date1, date2, exch));
		}
		return res;
	}

	public static void main(String[] args) throws Exception {
		try {
			Security sec = new Security(Integer.parseInt(args[0]));
			long date = df.parseShort(args[1]).getTime();
			Exchange.Type exch = Exchange.Type.valueOf(args[2]);

			DailyPriceSource dpSource = new DailyPriceSource();
			System.out.println(dpSource.getLatestPrice(sec, date, exch));
		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}
}
