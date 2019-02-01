package ase.util;

import java.text.ParseException;
import java.util.Calendar;
import java.util.SimpleTimeZone;
import java.util.TimeZone;

import ase.data.Exchange;
import ase.data.Exchange.Type;

public class Time {
	public static TimeZone nyctz = TimeZone.getTimeZone("America/New_York");
	public static final SimpleTimeZone tz = new SimpleTimeZone(0, "GMT");
	public static final Calendar cal = Calendar.getInstance(tz);
	public static final long MILLIS_PER_DAY = 60L * 60L * 24L * 1000L;
	public static final long MILLIS_PER_HOUR = 60L * 60L * 1000L;
	public static final long MILLIS_PER_MINUTE = 60L * 1000L;
	public static final long MILLIS_PER_SECOND = 1000L;
	public static final int BIZ_DAYS_PER_YEAR = 252;
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static void assertDay(long date) {
	    assert date == Time.midnight(date);
	}
	
	public static long yesterday(long millis) {
	    return Time.midnight(millis - MILLIS_PER_DAY);
	}
	
	public static long today(long millis) {
        return Time.midnight(millis);
    }
	
	public static long tomorrow(long millis) {
	    return Time.midnight(millis + MILLIS_PER_DAY);
	}
	
	// takes datetime and returns just the date
	public static long midnight(long millis) {
		return millis - millis % MILLIS_PER_DAY;
	}

	public static long fromMinutes(long minutes) {
		return minutes * 60 * MILLIS_PER_SECOND;
	}

	public static long fromHours(long hours) {
		return hours * 3600 * MILLIS_PER_SECOND;
	}
	
	public static long toMinutes(long millis) {
		return millis / (60 * MILLIS_PER_SECOND);
	}

	public static long fromDays(int days) {
		return MILLIS_PER_DAY * days;
	}

	synchronized public static int toYYYYMMDD(long millis) {
		cal.setTimeInMillis(millis);
		return cal.get(Calendar.YEAR) * 10000 + (cal.get(Calendar.MONTH) + 1) * 100
				+ cal.get(Calendar.DAY_OF_MONTH);
	}
	
	synchronized public static long fromYYYYMMDD(int date) {
		int year=date/10000;
		int month=(date%10000)/100;
		int day=date%100;
		
		cal.clear();
		cal.set(year, month-1, day);
		
		return cal.getTimeInMillis();
	}

	public static int millis2hour(long asof, Exchange.Type exch) {
		long millisIntoTradingDay = asof - Exchange.openTime(asof, exch);
		
		//Outside trading hours
		if (millisIntoTradingDay < 0 || millisIntoTradingDay > Exchange.tradingDayMillis(exch)) 
			return -1;
		
		//take out of the equation the first half hour [9.30am, 10am)
		millisIntoTradingDay -= 30 * Time.MILLIS_PER_MINUTE;
		if (millisIntoTradingDay < 0)
			return 0;
		//compute the hour where we are in: convention [10am, 11am) is hour1, [11am, 12pm) is hour2,..., NOTE: [3pm, 4pm] is hour6
		int hour = (int) (millisIntoTradingDay / Time.MILLIS_PER_HOUR);
		//put exact close to hour6
		return Math.min(hour + 1, 6);
	}
	
	public static long addDays(long millis, int ndays) {
		return millis + ndays * MILLIS_PER_DAY;
	}

	public static int daysBetween(long millis1, long millis2) {
		return (int) ((millis2 - millis1) / MILLIS_PER_DAY);
	}

	public static long fromDate(java.util.Date date) {
		return date.getTime();
	}

	public static java.util.Date toDate(long millis) {
		return new java.util.Date(millis);
	}

	public static java.sql.Date toSqlDate(long millis) {
		return new java.sql.Date(millis);
	}

	synchronized public static boolean isWeekend(long millis) {
		cal.setTimeInMillis(millis);
		int day = cal.get(Calendar.DAY_OF_WEEK);
		if (day == Calendar.SATURDAY || day == Calendar.SUNDAY)
			return true;
		else
			return false;
	}

	// XXX not sure if this is off by one day on DST BUG
	synchronized public static int getNYCOffset(long date) {
		return nyctz.getOffset(date);
	}

	synchronized public static final long now() {
		return Calendar.getInstance().getTimeInMillis();
	}

	@Deprecated ///XXX Nikos: deceiving method name
	public static final long getDate(long date) {
		return date + Time.MILLIS_PER_DAY;
	}

	@Deprecated
	public static final long parseDate(String date) throws ParseException {
		return getDate(df.parseShort(date).getTime());
	}

	public static final int incrementDate(int day) throws ParseException {
		long newMillis = Time.fromYYYYMMDD(day) + Time.MILLIS_PER_DAY;
		return Time.toYYYYMMDD(newMillis);
	}

	public static final String incrementDate(String day) throws Exception {
		long newMillis = df.fromYYYYMMDD(day) + Time.MILLIS_PER_DAY;
		return String.valueOf(Time.toYYYYMMDD(newMillis));
	}
	
	public static final int decrementDate(int day) throws ParseException {
		long newMillis = Time.fromYYYYMMDD(day) - Time.MILLIS_PER_DAY;
		return Time.toYYYYMMDD(newMillis);
	}

	public static final String decrementDate(String day) throws Exception {
		long newMillis = df.fromYYYYMMDD(day) - Time.MILLIS_PER_DAY;
		return String.valueOf(Time.toYYYYMMDD(newMillis));
	}

	public static void tests1() throws ParseException {
		long date;
		System.out.println("Testing toYYYYMMDD  (all should be equal)");
		for (date=1300000000000L; date<1300000000000L+Time.MILLIS_PER_DAY; date+=30*60*1000L) {
			System.out.println(Time.toYYYYMMDD(date)+" "+df.formatShort(date));
		}
		System.out.println("Testing fromYYYYMMDD (all should be equal)");
		for (date=1300000000000L; date<1300000000000L+20*Time.MILLIS_PER_DAY; date+=17*60*60*1000L) {
			Integer intDate=Integer.parseInt(df.formatShort(date));
			System.out.println(Time.fromYYYYMMDD(intDate)+" "+df.parseShort(String.valueOf(intDate)).getTime());
		}
	}
	
	public static void tests2() {
		Exchange.Type exch = Type.NYSE;
		long day = Time.fromYYYYMMDD(20110630);
		long open = Exchange.openTime(day, exch);
		long close = Exchange.closeTime(day, exch);
		
		for (long asof = open; asof <= close; asof += 5 * Time.MILLIS_PER_MINUTE) {
			System.out.println(df.debugFormat(asof - 1)+", Hour = "+millis2hour(asof - 1, exch));
			System.out.println(df.debugFormat(asof)+", Hour = "+millis2hour(asof, exch));
			System.out.println(df.debugFormat(asof + 1)+", Hour = "+millis2hour(asof + 1, exch));
		}
	}
	
	public static void main(String[] argv) throws Exception {
		tests2();
	}
}
