package ase.timeseries;

import java.text.ParseException;
import java.util.Arrays;
import java.util.Vector;

import ase.data.Exchange;
import ase.data.Exchange.Type;
import ase.data.Security;
import ase.util.Time;

public class DailyBarTimeSeries extends BarTimeSeries {

	public DailyBarTimeSeries() {
		super(Time.MILLIS_PER_DAY);
	}
	
	public DailyBarTimeSeries(Vector<DailyBar> dailyBars, long date1, long date2, Exchange.Type exch) {
	    super(Time.MILLIS_PER_DAY);
	 
	    Time.assertDay(date1);
	    Time.assertDay(date2);
	    
	    //handles cases where date1,date2 fall in non trade days
	    long firstClose = Exchange.nextClose(date1, exch);
	    long lastClose = Exchange.prevClose(date2+Time.MILLIS_PER_DAY, exch);
	    int ii = 0;
	    for ( long tt = firstClose; tt <= lastClose; tt = Exchange.nextClose(tt, exch) ) {
	        while (ii < dailyBars.size() && dailyBars.get(ii).close_ts < tt) {
	            ii++;
	        }
	        if (ii < dailyBars.size() && dailyBars.get(ii).close_ts == tt) {
	        	dates.add(tt);
	        	bars.add(dailyBars.get(ii));
	        }
	        else {
	        	dates.add(tt);
	        	bars.add(null);
	        }
	    }	    
	    adjustAll();
	}

	public DailyBar getLastBar() {
		return (DailyBar) super.getLastBar();
	}

	public Long getLastBarDate() {
		return dates.lastElement();
	}

	public DailyBar getLag(int lag) {
		return (DailyBar) super.getLag(lag);
	}

	protected void adjustAll() {
		DailyBar previousBar = null;
		for (Bar b : bars) {
			DailyBar currentBar = (DailyBar) b;
			if (currentBar == null) {
				continue;
			}
			adjust(currentBar, previousBar);
			previousBar = currentBar;
		}
	}

	public void add(DailyBar bar, long millis) {
		DailyBar previousBar = (DailyBar) super.add(bar, millis);
		if (bar != null) adjust(bar, previousBar);
	}

	public void add(DailyBar bar) {
		assert bar != null;
		this.add(bar, bar.close_ts);
	}

	// TODO Verify what happens on cases where we have both a split and a
	// dividend. Is the dividend given as a fraction of the split shares?
	// I assume that this is the case now.
	protected void adjust(DailyBar currentBar, DailyBar previousBar) {
		double previousAdjFactor = (previousBar == null) ? 1 : previousBar.adjFactor;
		double previousAccDividends = (previousBar == null) ? 0 : previousBar.accDividends;

		currentBar.adjFactor = currentBar.split * previousAdjFactor;
		currentBar.accDividends = currentBar.div * currentBar.adjFactor + previousAccDividends;
	}
	
	private static void tests() throws ParseException {
		Exchange.Type exch = Type.NYSE;
		Security sec = new Security(5334);
		long date = df.parseShort("20110404").getTime();
		DailyBarTimeSeries ts = new DailyBarTimeSeries();
		DailyBar bar1 = new DailyBar(new Bar(sec, Exchange.openTime(date, exch), Exchange.closeTime(date, exch), 2, 3, 1, 2, 100),0.2,0.5);
		DailyBar bar2 = new DailyBar(new Bar(sec, Exchange.openTime(date + Time.MILLIS_PER_DAY, exch), Exchange.closeTime(date + Time.MILLIS_PER_DAY, exch), 5, 4, 7, 6, 200),0.1,3);
		DailyBar bar3 = null;
		ts.add(bar1);
		ts.add(bar2);
		ts.add(bar3, bar2.close_ts+Time.MILLIS_PER_DAY);
		System.out.println(ts.getAverageVolPrice(3, 0)+" Expected "+(bar1.notional()+bar2.notional())/2);
		System.out.println("Logrel array "+Arrays.toString(ts.getLogrelArray(1, 0))+" Expected in the middle "+TimeSeriesUtil.c2cLogrel(bar2, bar1));
	}

	public static void main(String argv[]) {
		try {
			tests();
//			int secid = 1914;
//			long asof = Time.now();
//			Exchange.Type exch = Type.NYSE;
//
//			Security sec = new Security(secid);
//			UnifiedDataSource uSource = new UnifiedDataSource(true);
//			DailyBarTimeSeries ts = uSource.dailySource.getTimeSeries(CollectionUtils.toSet(sec), Exchange.subtractTradingDays(asof, 20, exch), asof, exch)
//					.get(sec);
//
//			System.out.println(ts.toString());
//
//			System.out.println(ts.getLogrel(3, 10));
		}
		catch (Exception e) {
			System.out.println(e);
		}
	}
}
