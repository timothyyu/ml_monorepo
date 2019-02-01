package ase.data;

import gnu.trove.TIntObjectHashMap;

import java.util.Arrays;
import java.util.Calendar;
import java.util.EnumSet;
import java.util.TimeZone;
import java.util.Vector;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

//This class is heavily used and may benefit from some caching

public class Exchange {
	public static enum Type {
		DUMMY(-1), NONE(0), NYSE(11), AMEX(12), OTCBB(13), NASD(14), NASDOMS(15), CHI(16), ARCA(17), PHLX(18), OTC(19), BX(20), BATS(-2);

		private static TIntObjectHashMap<Exchange.Type> lookup = new TIntObjectHashMap<Exchange.Type>();
		static {
			for (Exchange.Type c : EnumSet.allOf(Exchange.Type.class))
				lookup.put(c.getCode(), c);
		}
		public static Exchange.Type getExchangeType(int code) {
			return lookup.get(code);
		}
		
		public final int code;
		Type(int code) {
			this.code = code;
		}
		public int getCode() {
			return this.code;
		}
	};

	private static final Logger log = LoggerFactory.getLogger(Exchange.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	
	public static final long REGULAR_TRADING_MILLIS = 65 * Time.MILLIS_PER_HOUR / 10;

	public static final int[] NYSE_HOLIDAYS = { 20010101, 20010115, 20010219, 20010413, 20010528, 20010704, 20010903, 20010911, 20010912, 20010913, 20010914,
			20011122, 20011225, 20020101, 20020121, 20020218, 20020329, 20020527, 20020704, 20020902, 20021128, 20021225, 20030101, 20030120, 20030217,
			20030418, 20030526, 20030704, 20030901, 20031127, 20031225, 20040101, 20040119, 20040216, 20040409, 20040531, 20040611, 20040705, 20040906,
			20041125, 20041224, 20050117, 20050221, 20050325, 20050530, 20050704, 20050905, 20051124, 20051226, 20060102, 20060116, 20060220, 20060414,
			20060529, 20060704, 20060904, 20061123, 20061225, 20070101, 20070102, 20070115, 20070219, 20070406, 20070528, 20070704, 20070903, 20071122,
			20071225, 20080101, 20080121, 20080218, 20080321, 20080526, 20080704, 20080901, 20081127, 20081225, 20090101, 20090119, 20090216, 20090410,
			20090525, 20090703, 20090907, 20091126, 20091225, 20100101, 20100118, 20100215, 20100402, 20100531, 20100705, 20100906, 20101125, 20101224,
			20110117, 20110221, 20110422, 20110530, 20110704, 20110905, 20111124, 20111226 };

	public static final int[] NYSE_EARLY_CLOSE = { 20051125, 20060703, 20061124, 20070703, 20071123, 20071224, 20080703, 20081128, 20081224, 20091127,
			20091224, 20101126, 20111125 };

	public static long tradingDayMillis(Exchange.Type exch) {
	    //XXX need to switch on exchange!!!
	    return REGULAR_TRADING_MILLIS;
	}
	
	public static double fractionOfDayPassed(Exchange.Type exch, long asof) {
	    return (asof - Exchange.openTime(asof, exch))/(1.0*Exchange.tradingDayMillis(exch));
	}
	
	public static int[] holidays(Exchange.Type exch) {
		switch (exch) {
		case NYSE:
		case AMEX:
		case OTCBB:
		case NASD:
		case NASDOMS:
		case CHI:
		case ARCA:
		case PHLX:
		case OTC:
		case BATS:
		case BX:
			return NYSE_HOLIDAYS;
		case DUMMY:
		case NONE:
			return NYSE_HOLIDAYS;
		default:
			throw new RuntimeException("Exchange.holidays called with invalid exchange " + exch);
		}
	}

	public static int[] early_close(Exchange.Type exch) {
		switch (exch) {
		case NYSE:
		case AMEX:
		case OTCBB:
		case NASD:
		case NASDOMS:
		case CHI:
		case ARCA:
		case PHLX:
		case OTC:
		case BATS:
		case BX:
			return NYSE_EARLY_CLOSE;
		case DUMMY:
		case NONE:
			return NYSE_EARLY_CLOSE;
		default:
			throw new RuntimeException("Exchange.early_close called with invalid exchange " + exch);
		}
	}

	public static boolean isHoliday(long date, Exchange.Type exch) {
		int yyyymmdd = Time.toYYYYMMDD(Time.midnight(date));
		int res = Arrays.binarySearch(holidays(exch), yyyymmdd);
		if (res >= 0)
			return true;
		else
			return false;
	}

	public static boolean isEarlyClose(long date, Exchange.Type exch) {
		int yyyymmdd = Time.toYYYYMMDD(Time.midnight(date));
		int res = Arrays.binarySearch(early_close(exch), yyyymmdd);
		if (res >= 0)
			return true;
		else
			return false;
	}

	// this function can be passed a date with time. it's a holiday/weekend all
	// day!
	public static boolean isTradingDay(long date, Exchange.Type exch) {
		if (isHoliday(date, exch) || Time.isWeekend(date))
			return false;
		else
			return true;
	}

	// ignores time of day in its logic
	public static long prevTradingDay(long millis, Exchange.Type exch) {
		millis -= Time.fromDays(1);
		while (!isTradingDay(millis, exch)) {
			millis -= Time.fromDays(1);
		}
		return Time.midnight(millis);
	}

	// ignores time of day in its logic
	public static long nextTradingDay(long millis, Exchange.Type exch) {
		millis += Time.fromDays(1);
		while (!isTradingDay(millis, exch)) {
			millis += Time.fromDays(1);
		}
		return Time.midnight(millis);
	}

	// doesn't ignore time of day in its logic
	// / XXX TODO: maybe we want different functionalities here for half days --
	// same time delta from open? delta to close? interpolated?
	public static long prevTradingDateTime(long date, Exchange.Type exch) {
		long timeofday = date - openTime(date, exch);
		long yesterday = prevTradingDay(date, exch);
		long yesterdayTime = openTime(yesterday, exch) + timeofday;
		
		//XXX Compensate for daylight savings that could throw yesterdayTime in a day different than yesterday. We pull yesterdayTime to at least the proper date
		if (Time.today(yesterdayTime) == yesterday)
			return yesterdayTime;
		else if (Time.today(yesterdayTime) < yesterday)
			return yesterday;
		else 
			return yesterday + Time.fromDays(1) -1;
	}

	// doesn't ignore time of day in its logic
	public static long nextTradingDateTime(long date, Exchange.Type exch) {
		long timeofday = date - openTime(date, exch);
		long tomorrow = nextTradingDay(date, exch);
		
		//XXX Compensate for daylight savings that could throw tomorrowTime in a day different than tomorrow. We try to pull tommorowTime at least on the proper date
		long tomorrowTime = openTime(tomorrow, exch) + timeofday;
		if (Time.today(tomorrowTime) == tomorrow)
			return tomorrowTime;
		else if (Time.today(tomorrowTime) < tomorrow)
			return tomorrow;
		else 
			return tomorrow + Time.fromDays(1) -1;
	}

	public static long addTradingDays(long millis, int ndays, Exchange.Type exch) {
		while (ndays > 0) {
			millis = nextTradingDateTime(millis, exch);
			ndays--;
		}
		return millis;
	}

	public static long subtractTradingDays(long date, int ndays, Exchange.Type exch) {
		while (ndays > 0) {
			date = prevTradingDateTime(date, exch);
			ndays--;
		}
		return date;
	}

	public static Long[] tradingDaysBetween(long date1, long date2, Exchange.Type exch) {
	    Time.assertDay(date1);
	    Time.assertDay(date2);
	    
		Vector<Long> res = new Vector<Long>();
		///XXX note the less or equals in the loop below. This way we return all days [t1,t2] even
		///if t2=midnight(t2)
		for (long date = date1; date <= date2; date = Exchange.nextTradingDay(date, exch)) {
			res.add(date);
		}
		return res.toArray(new Long[0]);
	}

	// given a date/time of an event, will return the date and time of the first
	// closing price into which this event might possibly be incorporated
	public static long nextClose(long millis, Exchange.Type exch) {
		if (isTradingDay(millis, exch) && millis < closeTime(millis, exch))
			return closeTime(millis, exch);
		else
			return closeTime(nextTradingDay(millis, exch), exch);
	}

	// given a date/time of an event, will return the most recent date/time
	// that exch closed prior to this event
	public static long prevClose(long millis, Exchange.Type exch) {
		if (isTradingDay(millis, exch) && millis > closeTime(millis, exch))
			return closeTime(millis, exch);
		else
			return closeTime(prevTradingDay(millis, exch), exch);
	}

	// takes 2 dates and says whether events at each time
	// affect the same day's trading on exchange exch
	public static boolean affectsSameDay(long millis1, long millis2, Exchange.Type exch) {
		millis1 = nextClose(millis1, exch);
		millis2 = nextClose(millis2, exch);
		if (millis1 == millis2)
			return true;
		else
			return false;
	}

	public static long getTZOffset(long date, Exchange.Type exch) {
		return Time.getNYCOffset(date);
	}

	// this function will claim that the exchange opens every day, so
	// make sure you know whether you're asking on a weekend or holiday
	public static long openTime(long date, Exchange.Type exch) {
		return Time.midnight(date) + Time.fromMinutes(9 * 60 + 30) - getTZOffset(date, exch);
	}

	// this function will claim that the exchange opens every day, so
	// make sure you know whether you're asking on a weekend or holiday
	public static long closeTime(long millis, Exchange.Type exch) {
		if (isEarlyClose(millis, exch))
			return Time.midnight(millis) + Time.fromMinutes(13 * 60) - getTZOffset(millis, exch);
		else
			return Time.midnight(millis) + Time.fromMinutes(16 * 60) - getTZOffset(millis, exch);
	}

	public static boolean isOpen(long millis, Exchange.Type exch) {
		if (isTradingDay(millis, exch) && millis >= openTime(millis, exch) && millis <= closeTime(millis, exch))
			return true;
		else
			return false;
	}

	public static long tradingTimeBetween(long date1, long date2, Exchange.Type exch) {
		if (date1 > date2) {
			throw new RuntimeException("tradingTimeBetween called with date1 > date2");
		}
		long date = date1;
		long result = 0;
		while (true) {
			long nextdate = nextTradingDateTime(date, exch);
			if (nextdate >= date2) {
				if (Time.midnight(date) == Time.midnight(date2)) {
					result += date2 - date;
				}
				else if (Time.midnight(nextdate) == Time.midnight(date2)) {
					result += Time.fromDays(1);
					result += date2 - nextdate;
				}
				else {
					result += Time.fromDays(1);
				}
				break;
			}
			else {
				result += Time.fromDays(1);
				date = nextdate;
			}
		}
		return result;
	}

	// returns the time difference between half days and regular days, 0 if it
	// is a reg day
	public static long earlyCloseDiff(long date, Exchange.Type exch) {
		if (isEarlyClose(date, exch)) {
			return Time.fromMinutes(3 * 60);
		}
		return 0;
	}

	// WEEK IS SUNDAY-SATURDAY
	public static long startOfTradingWeek(long currentDate, Exchange.Type exch) {
		Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
		cal.setFirstDayOfWeek(Calendar.SUNDAY);
		cal.setTimeInMillis(currentDate);
		cal.set(Calendar.DAY_OF_WEEK, cal.getFirstDayOfWeek());
		return Exchange.nextTradingDay(cal.getTimeInMillis(), exch);
	}

	public static long endOfTradingWeek(long currentDate, Exchange.Type exch) {
		Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
		cal.setFirstDayOfWeek(Calendar.SUNDAY);
		cal.setTimeInMillis(currentDate);
		cal.set(Calendar.DAY_OF_WEEK, cal.getActualMaximum(Calendar.DAY_OF_WEEK));
		return Exchange.prevTradingDay(cal.getTimeInMillis(), exch);
	}

	// [F0,U0,S1,M1,T1,W1,R1,F1,U1,S2].
	// if you ask on S1 to U1 you get F0
	// if you ask on S2 onward you get F1
	public static long endOfPreviousTradingWeek(long currentDate, Exchange.Type exch) {
		return Exchange.prevTradingDay(startOfTradingWeek(currentDate, exch), exch);
	}

	public static long startOfTradingMonth(long currentDate, Exchange.Type exch) {
		Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
		cal.setTimeInMillis(currentDate);
		cal.set(Calendar.DAY_OF_MONTH, cal.getActualMinimum(Calendar.DAY_OF_MONTH));
		long date = cal.getTimeInMillis();
		if (Exchange.isTradingDay(date, exch)) {
			return date;
		}
		else {
			return Exchange.nextTradingDay(date, exch);
		}
	}

	public static long endOfPreviousTradingMonth(long currentDate, Exchange.Type exch) {
		return Exchange.prevTradingDay(startOfTradingMonth(currentDate, exch), exch);
	}

	public static void main(String[] argv) throws Exception {
		long date = 0;
		Exchange.Type exch = null;

		String mode = argv[0];
		if ("oc".equals(mode)) {
			exch = Exchange.Type.valueOf(argv[1]);
			date = df.parse(argv[2]);
			long opentime, closetime;
			if (isTradingDay(date, exch)) {
				opentime = openTime(date, exch);
				// Note that the closeTime() function takes care of half days
				closetime = closeTime(date, exch);
			}
			else {
				opentime = 0;
				closetime = 0;
			}
			System.out.println(opentime + "|" + closetime);
		}
		else if ("tda".equals(mode)) {
			exch = Exchange.Type.valueOf(argv[1]);
			date = df.parse(argv[2]);
			int offset = Integer.parseInt(argv[3]);
			long newdate = date;
			if (offset > 0) {
				newdate = addTradingDays(date, offset, exch);
			}
			else if (offset < 0) {
				int daysToGoBack = Math.abs(offset);
				newdate = subtractTradingDays(date, daysToGoBack, exch);
			}
			System.out.println(df.formatShort(newdate));
		}
		else if ("sow".equals(mode)) {
			exch = Exchange.Type.valueOf(argv[1]);
			date = df.parseShort(argv[2]).getTime();
			System.out.println(df.formatShort(startOfTradingWeek(date, exch)));
		}
		else if ("eow".equals(mode)) {
			exch = Exchange.Type.valueOf(argv[1]);
			date = df.parseShort(argv[2]).getTime();
			System.out.println(df.formatShort(endOfTradingWeek(date, exch)));
		}
		else {
			System.out.println("Invalid Model!!!");
		}
	}
}
