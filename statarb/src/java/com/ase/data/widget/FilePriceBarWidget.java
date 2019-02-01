package ase.data.widget;

import gnu.trove.TIntObjectHashMap;

import java.io.BufferedReader;
import java.io.File;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.ListIterator;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.Vector;
import java.util.logging.Logger;
import java.util.regex.Pattern;

import org.apache.commons.collections15.map.LRUMap;

import ase.data.BarSource;
import ase.data.Exchange;
import ase.data.Imbalance;
import ase.data.Exchange.Type;
import ase.data.Security;
import ase.timeseries.Bar;
import ase.timeseries.BarV2;
import ase.timeseries.TimeSeries;
import ase.timeseries.TimestampedDatum;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class FilePriceBarWidget {

	protected enum BarType {
		INTRA, DAY, IMB
	};

	// //////////// STUFF FOR PERFORMING BINARY SEARCH ON TIMESTAMPED DATA VECTORS////////
	protected static class TimestampedDatumComparator implements Comparator<TimestampedDatum> {
		public int compare(TimestampedDatum o1, TimestampedDatum o2) {
			return (int) Math.signum(o1.getTs() - o2.getTs());
		}
	}

	protected static class EnhancedLong implements TimestampedDatum {
		protected long d;

		public EnhancedLong(long d) {
			this.d = d;
		}

		public long getTs() {
			return d;
		}
	}

	// /////////// CACHING //////////////////
	// Synonym for Pair<Integer,Integer>
	protected static class SecDay extends Pair<Security, Integer> {
		public SecDay(Security sec, int day) {
			super(sec, day);
		}
	}

	protected static boolean USE_CACHING = true;
	protected static final int INTRA_CACHE_SIZE_IN_SEC_DAYS = 2000 * 2;
	protected static final int DAY_CACHE_SIZE_IN_SEC_DAYS = 2000 * 21;
	protected static final int IMB_CACHE_SIZE_IN_SEC_DAYS = 2000 * 2;
	protected Map<SecDay, Vector<TimestampedDatum>> intraCache = new LRUMap<FilePriceBarWidget.SecDay, Vector<TimestampedDatum>>(INTRA_CACHE_SIZE_IN_SEC_DAYS);
	protected Map<SecDay, Vector<TimestampedDatum>> dayCache = new LRUMap<FilePriceBarWidget.SecDay, Vector<TimestampedDatum>>(DAY_CACHE_SIZE_IN_SEC_DAYS);
	protected Map<SecDay, Vector<TimestampedDatum>> imbCache = new LRUMap<FilePriceBarWidget.SecDay, Vector<TimestampedDatum>>(IMB_CACHE_SIZE_IN_SEC_DAYS);
	// ///////////////////////////////////////

	// /////// FIELDS //////////////
	protected static final ASEFormatter df = ASEFormatter.getInstance();
	protected static final Logger log = LoggerFactory.getLogger(FilePriceBarWidget.class.getName());
	protected static final String BAR_DIR = System.getenv("DATA_DIR") + "/bars";
	protected static final TimestampedDatumComparator comparator = new TimestampedDatumComparator();
	private static FilePriceBarWidget instance;

	// ////// METHODS //////////////

	synchronized public static final FilePriceBarWidget instance() {
		if (instance == null) {
			instance = new FilePriceBarWidget();
		}
		return instance;
	}

	protected FilePriceBarWidget() {
	}

	// ////////////////// INTERNALS ///////////////////

	synchronized protected void addToCache(Set<Security> secs, Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> bars, int day, BarType type,
			boolean cacheLive) {
		Map<SecDay, Vector<TimestampedDatum>> cache = null;
		switch (type) {
		case INTRA:
			cache = intraCache;
			break;
		case DAY:
			cache = dayCache;
			break;
		case IMB:
			cache = imbCache;
			break;
		}
		// If no files are found (bars==null), do not cache anything.
		// The reason is that we are not sure if this is a live or a historical
		// day we were trying to retrieve
		// If it was a live day, it would be wrong to cache the absence of data.
		if (bars != null && (!bars.first || cacheLive)) {
			for (Security sec : secs) {
				cache.put(new SecDay(sec, day), bars.second.get(sec));
			}
			log.info("Cache for " + type + " now contains " + cache.size() + " secdays");
		}
	}

	synchronized protected Map<Security, Vector<TimestampedDatum>> getBarsForDay(Set<Security> securities, int day, BarType type) throws Exception {
		Map<SecDay, Vector<TimestampedDatum>> cache = null;
		switch (type) {
		case INTRA:
			cache = intraCache;
			break;
		case DAY:
			cache = dayCache;
			break;
		case IMB:
			cache = imbCache;
			break;
		}

		if (!USE_CACHING) {
			Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> allBars = readFile(securities, day, type);
			if (allBars == null)
				return null;
			else
				return allBars.second;
		}
		else {
			boolean readFile = false;
			for (Security sec : securities) {
				if (!cache.containsKey(new SecDay(sec, day))) {
					readFile = true;
					break;
				}
			}

			if (readFile) {
				Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> allBars = readFile(securities, day, type);
				addToCache(securities, allBars, day, type, false);
				if (allBars == null)
					return null;
				else
					return allBars.second;
			}
			else {
				Map<Security, Vector<TimestampedDatum>> result = new HashMap<Security, Vector<TimestampedDatum>>();
				for (Security sec : securities)
					result.put(sec, cache.get(new SecDay(sec, day)));

				return result;
			}
		}
	}

	// //////// FILE READING //////////////

	// [0]=File
	// [1]=Version
	// [2]=Live
	// [3]=Zipped
	protected Object[] getFile(int day, BarType type) {
		File dir = new File(BAR_DIR + "/" + day);
		if (!dir.exists())
			return null;

		TreeSet<String> files = new TreeSet<String>();
		for (File file : dir.listFiles())
			files.add(file.getName());

		if (type == BarType.INTRA) {
			if (files.contains("bars_v2.txt.live")) {
				return new Object[] { new File(dir, "bars_v2.txt.live"), 2, true, false };
			}
			else if (files.contains("bars_v2.txt.gz")) {
				return new Object[] { new File(dir, "bars_v2.txt.gz"), 2, false, true };
			}
			else if (files.contains("bars_v1.txt.live")) {
				return new Object[] { new File(dir, "bars_v1.txt.live"), 1, true, false };
			}
			else if (files.contains("bars_v1.txt.gz")) {
				return new Object[] { new File(dir, "bars_v1.txt.gz"), 1, false, true };
			}
			else if (files.contains("all.txt.live")) {
				return new Object[] { new File(dir, "all.txt.live"), 1, true, false };
			}
			else if (files.contains("all.txt.gz")) {
				return new Object[] { new File(dir, "all.txt.gz"), 1, false, true };
			}
		}
		else if (type == BarType.DAY) {
			if (files.contains("daily_v1.txt.live")) {
				return new Object[] { new File(dir, "daily_v1.txt.live"), 1, true, false };
			}
			else if (files.contains("daily_v1.txt.gz")) {
				return new Object[] { new File(dir, "daily_v1.txt.gz"), 1, false, true };
			}
		}
		else if (type == BarType.IMB) {
			if (files.contains("imb_v1.txt.live")) {
				return new Object[] { new File(dir, "imb_v1.txt.live"), 1, true, false };
			}
			else if (files.contains("imb_v1.txt.gz")) {
				return new Object[] { new File(dir, "imb_v1.txt.gz"), 1, false, true };
			}
		}

		return null;
	}

	protected Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> readFile(Set<Security> securities, int day, BarType type) throws Exception {
		switch (type) {
		case INTRA:
			return readIntraFile(securities, day);
		case DAY:
			return readDayFile(securities, day);
		case IMB:
			return readImbFile(securities, day);
		}
		throw new RuntimeException("We should not have reached this spot");
	}

	// /XXX ONLY VALID BARS ARE RETURNED FROM FILE. WE MIGHT WANT TO REVISIT
	// THIS
	protected Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> readIntraFile(Set<Security> securities, int day) throws Exception {
		Object[] fileInfo = getFile(day, BarType.INTRA);
		if (fileInfo == null) {
			log.warning("Cannot find bar file for day " + day);
			return null;
		}

		File file = (File) fileInfo[0];
		Integer version = (Integer) fileInfo[1];
		Boolean live = (Boolean) fileInfo[2];
		Boolean zipped = (Boolean) fileInfo[3];

		log.info("Reading bar file: " + file.getCanonicalPath());

		// create a map from secids to securities
		TIntObjectHashMap<Security> secidMap = new TIntObjectHashMap<Security>();
		// initialize sec2bars with empty vectors, so that even securities with
		// no data get at lease
		// an empty vector
		Map<Security, Vector<TimestampedDatum>> sec2bars = new HashMap<Security, Vector<TimestampedDatum>>();
		for (Security sec : securities) {
			secidMap.put(sec.getSecId(), sec);
			sec2bars.put(sec, new Vector<TimestampedDatum>(7 * 60 / ((int) (BarSource.BAR_SPAN / Time.MILLIS_PER_MINUTE))));
		}

		BufferedReader reader = null;
		if (zipped) {
			reader = FileUtils.openZipReader(file);
		}
		else {
			reader = FileUtils.openFileReader(file);
		}

		String line;
		Pattern separator = Pattern.compile("\\|");
		while ((line = reader.readLine()) != null) {
			Bar bar = null;
			String[] tokens = separator.split(line);
			int secid = Integer.valueOf(tokens[0]);
			Security sec = secidMap.get(secid);
			if (sec == null) {
				continue;
			}
			long open_ts = Long.valueOf(tokens[1]);
			long close_ts = Long.valueOf(tokens[2]);
			double open = Double.valueOf(tokens[3]);
			double high = Double.valueOf(tokens[5]);
			double low = Double.valueOf(tokens[6]);
			double close = Double.valueOf(tokens[7]);
			double volume = Double.valueOf(tokens[8]);

			if (version == 1) {
				bar = new Bar(sec, open_ts, close_ts, open, high, low, close, volume);
			}
			else if (version == 2) {
				int ii = 9;
				double meanSpread = Double.valueOf(tokens[ii++]);
				double meanEffectiveSpread = Double.valueOf(tokens[ii++]);
				double meanBidSize = Double.valueOf(tokens[ii++]);
				double meanAskSize = Double.valueOf(tokens[ii++]);
				int trades = Integer.valueOf(tokens[ii++]);
				int bidTrades = Integer.valueOf(tokens[ii++]);
				int midTrades = Integer.valueOf(tokens[ii++]);
				int askTrades = Integer.valueOf(tokens[ii++]);
				int effectiveBidTrades = Integer.valueOf(tokens[ii++]);
				int effectiveMidTrades = Integer.valueOf(tokens[ii++]);
				int effectiveAskTrades = Integer.valueOf(tokens[ii++]);
				double bidTradeAmount = Double.valueOf(tokens[ii++]);
				double midTradeAmount = Double.valueOf(tokens[ii++]);
				double askTradeAmount = Double.valueOf(tokens[ii++]);
				double effectiveBidTradeAmount = Double.valueOf(tokens[ii++]);
				double effectiveMidTradeAmount = Double.valueOf(tokens[ii++]);
				double effectiveAskTradeAmount = Double.valueOf(tokens[ii++]);

				bar = new BarV2(sec, open_ts, close_ts, open, high, low, close, volume, meanSpread, meanEffectiveSpread, meanBidSize, meanAskSize, trades,
						bidTrades, midTrades, askTrades, effectiveBidTrades, effectiveMidTrades, effectiveAskTrades, bidTradeAmount, midTradeAmount,
						askTradeAmount, effectiveBidTradeAmount, effectiveMidTradeAmount, effectiveAskTradeAmount);
			}

			// /XXX ONLY EXTRACT FROM FILE VALID BARS
			if (!bar.isValid()) {
				continue;
			}

			sec2bars.get(sec).add(bar);
		}
		reader.close();

		// compact
		for (Vector<TimestampedDatum> v : sec2bars.values())
			v.trimToSize();

		return new Pair<Boolean, Map<Security, Vector<TimestampedDatum>>>(live, sec2bars);
	}

	// /XXX ONLY VALID BARS ARE RETURNED FROM FILE. WE MIGHT WANT TO REVISIT
	// THIS
	protected Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> readDayFile(Set<Security> securities, int day) throws Exception {
		Object[] fileInfo = getFile(day, BarType.DAY);
		if (fileInfo == null) {
			log.warning("Cannot find daily bar file for day " + day);
			return null;
		}

		File file = (File) fileInfo[0];
		Integer version = (Integer) fileInfo[1];
		Boolean live = (Boolean) fileInfo[2];
		Boolean zipped = (Boolean) fileInfo[3];

		log.info("Reading daily file: " + file.getCanonicalPath());

		// create a map from secids to securities
		TIntObjectHashMap<Security> secidMap = new TIntObjectHashMap<Security>();
		// initialize sec2bars with empty vectors, so that even securities with
		// no data get at lease
		// an empty vector
		Map<Security, Vector<TimestampedDatum>> sec2bars = new HashMap<Security, Vector<TimestampedDatum>>();
		for (Security sec : securities) {
			secidMap.put(sec.getSecId(), sec);
			sec2bars.put(sec, new Vector<TimestampedDatum>(7 * 60 / ((int) (BarSource.BAR_SPAN / Time.MILLIS_PER_MINUTE))));
		}

		BufferedReader reader = null;
		if (zipped) {
			reader = FileUtils.openZipReader(file);
		}
		else {
			reader = FileUtils.openFileReader(file);
		}

		String line;
		Pattern separator = Pattern.compile("\\|");
		while ((line = reader.readLine()) != null) {
			Bar bar = null;
			String[] tokens = separator.split(line);
			int secid = Integer.valueOf(tokens[0]);
			Security sec = secidMap.get(secid);
			if (sec == null) {
				continue;
			}
			long close_ts = Long.valueOf(tokens[1]);
			long open_ts = Exchange.openTime(Time.fromYYYYMMDD(day), sec.primaryExchange);
			double open = Double.valueOf(tokens[2]);
			double high = Double.valueOf(tokens[3]);
			double low = Double.valueOf(tokens[4]);
			double close = Double.valueOf(tokens[5]);
			double volume = Double.valueOf(tokens[9]);

			double qhigh = Double.valueOf(tokens[6]);
			double qlow = Double.valueOf(tokens[7]);
			double vwap = Double.valueOf(tokens[8]);
			double trades = Double.valueOf(tokens[10]);

			if (version == 1) {
				bar = new Bar(sec, open_ts, close_ts, open, high, low, close, volume);
				Double[] extras = new Double[] { qhigh, qlow, vwap, trades };
				bar.setExtras(extras);
			}

			// /XXX ONLY EXTRACT FROM FILE VALID BARS
			if (!bar.isValid()) {
				continue;
			}

			sec2bars.get(sec).add(bar);
		}
		reader.close();

		// compact
		for (Vector<TimestampedDatum> v : sec2bars.values())
			v.trimToSize();

		return new Pair<Boolean, Map<Security, Vector<TimestampedDatum>>>(live, sec2bars);
	}

	// /XXX ONLY VALID BARS ARE RETURNED FROM FILE. WE MIGHT WANT TO REVISIT
	// THIS
	protected Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> readImbFile(Set<Security> securities, int day) throws Exception {
		Object[] fileInfo = getFile(day, BarType.IMB);
		if (fileInfo == null) {
			log.warning("Cannot find imbalance file for day " + day);
			return null;
		}

		File file = (File) fileInfo[0];
		Integer version = (Integer) fileInfo[1];
		Boolean live = (Boolean) fileInfo[2];
		Boolean zipped = (Boolean) fileInfo[3];

		log.info("Reading imbalance file: " + file.getCanonicalPath());

		// create a map from secids to securities
		TIntObjectHashMap<Security> secidMap = new TIntObjectHashMap<Security>();
		// initialize sec2bars with empty vectors, so that even securities with
		// no data get at lease
		// an empty vector
		Map<Security, Vector<TimestampedDatum>> sec2bars = new HashMap<Security, Vector<TimestampedDatum>>();
		for (Security sec : securities) {
			secidMap.put(sec.getSecId(), sec);
			sec2bars.put(sec, new Vector<TimestampedDatum>(1000));
		}

		BufferedReader reader = null;
		if (zipped) {
			reader = FileUtils.openZipReader(file);
		}
		else {
			reader = FileUtils.openFileReader(file);
		}

		String line;
		Pattern separator = Pattern.compile("\\|");
		while ((line = reader.readLine()) != null) {
			Imbalance imb = null;
			String[] tokens = separator.split(line);
			int secid = Integer.valueOf(tokens[0]);
			Security sec = secidMap.get(secid);
			if (sec == null) {
				continue;
			}
			long ts = Long.valueOf(tokens[1]);
			int matchedQty = Integer.valueOf(tokens[2]);
			int imbalance = Integer.valueOf(tokens[3]);
			double refPrice = Double.valueOf(tokens[4]);
			double nearPrice = Double.valueOf(tokens[5]);
			double farPrice = Double.valueOf(tokens[6]);
			double lastTick = Double.valueOf(tokens[7]);
			double bid = Double.valueOf(tokens[8]);
			double ask = Double.valueOf(tokens[9]);

			imb = new Imbalance(sec, ts, matchedQty, imbalance, refPrice, nearPrice, farPrice, lastTick, bid, ask);

			sec2bars.get(sec).add(imb);
		}
		reader.close();

		// compact
		for (Vector<TimestampedDatum> v : sec2bars.values())
			v.trimToSize();

		return new Pair<Boolean, Map<Security, Vector<TimestampedDatum>>>(live, sec2bars);
	}

	// //////////////////INTERFACE ///////////////////

	// /XXX: WARNING will force caching of live data. It is the caller's responsibility to re-preload data
	synchronized public void preload(Set<Security> secs, long date1, long date2) throws Exception {
		Time.assertDay(date1);
		Time.assertDay(date2);
		if (!USE_CACHING)
			return;
		log.info("Preloading bars in days [" + df.formatShort(date1) + ", " + df.formatShort(date2) + "]");

		// /XXX: new zealand baby
		// int startDay = Time.toYYYYMMDD(millis1 - 24L * 60L * 60L * 1000L);
		int startDay = Time.toYYYYMMDD(date1);
		int endDay = Time.incrementDate(Time.toYYYYMMDD(date2));
		log.info("Preloading days [" + startDay + ", " + endDay + ")");

		for (int day = startDay; day < endDay; day = Time.incrementDate(day)) {
			Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> intraBars = readFile(secs, day, BarType.INTRA);
			addToCache(secs, intraBars, day, BarType.INTRA, true);
			Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> dailyBars = readFile(secs, day, BarType.DAY);
			addToCache(secs, dailyBars, day, BarType.DAY, true);
			Pair<Boolean, Map<Security, Vector<TimestampedDatum>>> imbBars = readFile(secs, day, BarType.IMB);
			addToCache(secs, dailyBars, day, BarType.IMB, true);
		}
	}

	public Vector<Bar> getPrices(Security sec, long millis1, long millis2, Exchange.Type exch) throws Exception {
		return getPrices(CollectionUtils.toSet(sec), millis1, millis2, exch).get(sec);
	}

	/**
	 * Gets all bars, across days with millis1<=close_ts<=millis2
	 * 
	 */
	public Map<Security, Vector<Bar>> getPrices(Set<Security> secs, long millis1, long millis2, Exchange.Type exch) throws Exception {
		log.info("Loading bars with close_ts between [" + df.format(millis1) + ", " + df.format(millis2) + "]");
		// convert the dates
		// /XXX If we ever trade new zealand, where trading day spans utc,
		// uncomment this:
		// protect ourselves against the freak case of a trading day spanning
		// UTC by additionally searching the previous day
		// do this by subtracting one day from millis1
		// int startDay = Time.toYYYYMMDD(millis1 - 24L * 60L * 60L * 1000L);
		int startDay = Time.toYYYYMMDD(millis1);
		int endDay = Time.incrementDate(Time.toYYYYMMDD(millis2));

		log.info("Searching in days to [" + startDay + ", " + endDay + ")");

		HashMap<Security, Vector<Bar>> result = new HashMap<Security, Vector<Bar>>();
		// initialize result
		for (Security sec : secs) {
			result.put(sec, new Vector<Bar>());
		}

		int counter = 0;
		for (int day = startDay; day < endDay; day = Time.incrementDate(day)) {
			if (!Exchange.isTradingDay(df.fromYYYYMMDD(Integer.toString(day)), exch))
				continue;

			Map<Security, Vector<TimestampedDatum>> allSecDayBars = getBarsForDay(secs, day, BarType.INTRA);
			if (allSecDayBars == null)
				continue;

			for (Security sec : secs) {
				Vector<Bar> secBars = result.get(sec);
				Vector<TimestampedDatum> secDayBars = allSecDayBars.get(sec);

				if (secDayBars == null || secDayBars.isEmpty() || secDayBars.lastElement().getTs() < millis1)
					continue;

				// binary search for our bars
				// get range through binary search
				int start = Collections.binarySearch(secDayBars, new EnhancedLong(millis1), comparator);
				int end = Collections.binarySearch(secDayBars, new EnhancedLong(millis2), comparator);
				start = (start < 0) ? -start - 1 : start;
				end = (end < 0) ? -end - 1 : end + 1; // Note the end+1. if
														// millis2=close_ts we
														// keep it

				if (start != end) {
					for (TimestampedDatum d : secDayBars.subList(start, end))
						secBars.add((Bar) d);
					counter += end - start;
				}
			}
		}
		log.info("Loaded " + counter + " bars.");
		return result;
	}

	/**
	 * Gets most recent bar with oldest<=close_ts<=asof
	 * 
	 */
	public Bar getPricesAsOf(Security sec, long asOf, long oldest, Exchange.Type exch) throws Exception {
		return getPricesAsOf(CollectionUtils.toSet(sec), asOf, oldest, exch).get(sec);
	}

	public Map<Security, Bar> getPricesAsOf(Set<Security> secs, long asOf, long oldest, Exchange.Type exch) throws Exception {
		log.info("Loading oldest bars with close_ts between [" + df.format(oldest) + ", " + df.format(asOf) + "]");
		// convert the dates
		// /XXX If we ever trade new zealand, where trading day spans utc,
		// uncomment this:
		// protect ourselves against the freak case of a trading day spanning
		// UTC by additionally searching the previous day
		// do this by subtracting one day from millis1
		// int startDay = Time.toYYYYMMDD(oldest - 24L * 60L * 60L * 1000L);
		int startDay = Time.toYYYYMMDD(oldest);
		int endDay = Time.toYYYYMMDD(asOf);

		log.info("Searching in days to [" + startDay + ", " + endDay + "]");

		HashMap<Security, Bar> result = new HashMap<Security, Bar>();
		// initialize result
		for (Security sec : secs) {
			result.put(sec, null);
		}

		int counter = 0;
		for (int day = endDay; day >= startDay; day = Time.decrementDate(day)) {
			if (!Exchange.isTradingDay(df.fromYYYYMMDD(Integer.toString(day)), exch))
				continue;

			// got bars for all securities
			if (counter == result.size())
				break;

			Map<Security, Vector<TimestampedDatum>> allSecDayBars = getBarsForDay(secs, day, BarType.INTRA);
			if (allSecDayBars == null)
				continue;

			for (Security sec : secs) {
				Bar mostRecent = result.get(sec);
				if (mostRecent != null)// already got bar for this security
					continue;

				Vector<TimestampedDatum> secDayBars = allSecDayBars.get(sec);
				if (secDayBars == null || secDayBars.isEmpty())
					continue;

				// //////////////
				ListIterator<TimestampedDatum> it = secDayBars.listIterator(secDayBars.size());
				while (it.hasPrevious()) {
					Bar bar = (Bar) it.previous();
					if (bar.isValid() && bar.close_ts <= asOf) {
						mostRecent = bar;
						result.put(sec, mostRecent);
						counter++;
						break;
					}
					else if (bar.close_ts < oldest) {
						break;
					}
				}
			}
		}
		log.info("Loaded " + counter + " bars.");
		return result;
	}

	public Map<Security, Bar> getDayBars(Set<Security> secs, long date1, long millisIntoDay, Exchange.Type exch) throws Exception {
		Time.assertDay(date1);
		assert millisIntoDay < 7 * Time.MILLIS_PER_HOUR && millisIntoDay >= 0;
		assert Exchange.isTradingDay(date1, exch);
		log.info("Loading half bars between on " + df.formatShort(date1) + ". Hours used=" + 1.0 * millisIntoDay / 60 / 60 / Time.MILLIS_PER_SECOND);

		HashMap<Security, Bar> result = new HashMap<Security, Bar>();
		Map<Security, Vector<TimestampedDatum>> allSecDayBars = getBarsForDay(secs, Time.toYYYYMMDD(date1), BarType.DAY);
		if (allSecDayBars == null) {
			log.info("Loaded " + result.size() + " / " + secs.size() + " day bars.");
			return result;
		}

		long millis = Exchange.openTime(date1, exch) + millisIntoDay;
		for (Security sec : secs) {
			Vector<TimestampedDatum> secBars = allSecDayBars.get(sec);
			if (secBars == null)
				continue;
			// perform a binary search to find the bar
			int pos = Collections.binarySearch(secBars, new EnhancedLong(millis), comparator);
			pos = (pos < 0) ? -pos - 2 : pos;
			if (pos < 0)
				continue;
			result.put(sec, (Bar) secBars.get(pos));
		}

		log.info("Loaded " + result.size() + " / " + secs.size() + " day bars.");
		return result;
	}

	public boolean hasDayBars(long date) {
		Time.assertDay(date);
		Object[] o = getFile(Time.toYYYYMMDD(date), BarType.DAY);
		return o != null;
	}

	private static void tests() throws Exception {
		Exchange.Type exch = Type.NYSE;
		Set<Security> secs = CollectionUtils.toSet(new Security(5334));
		FilePriceBarWidget widget = new FilePriceBarWidget();

		long millis1;
		long millis2;
		// intra day on a full day
		System.out.println("TEST1, INTRADAY WITH DATA");
		millis1 = df.parseMins("20100104_1432").getTime();
		millis2 = df.parseMins("20100104_1537").getTime();
		Map<Security, Vector<Bar>> res = widget.getPrices(secs, millis1, millis2, exch);
		for (Bar bar : res.get(new Security(5334))) {
			System.out.println(bar.toHRString());
		}

		// intra day on a emmpty
		System.out.println("TEST2, INTRADAY DAY WITHOUT DATA");
		millis1 = df.parseMins("20100102_1432").getTime();
		millis2 = df.parseMins("20100102_1537").getTime();
		res = widget.getPrices(secs, millis1, millis2, exch);
		for (Bar bar : res.get(new Security(5334))) {
			System.out.println(bar.toHRString());
		}

		// multiple days
		System.out.println("TEST3, MULTIPLE DAYS DATA");
		millis1 = df.parseMins("20100102_1432").getTime();
		millis2 = df.parseMins("20100107_1537").getTime();
		res = widget.getPrices(secs, millis1, millis2, exch);
		for (Bar bar : res.get(new Security(5334))) {
			System.out.println(bar.toHRString());
		}

		// multiple days
		System.out.println("TEST4, INTRADAY WITHOUT DATA");
		millis1 = df.parseMins("20100105_0032").getTime();
		millis2 = df.parseMins("20100105_0337").getTime();
		res = widget.getPrices(secs, millis1, millis2, exch);
		for (Bar bar : res.get(new Security(5334))) {
			System.out.println(bar.toHRString());
		}

		// as of
		System.out.println("TEST5, ASOF NOTHING TO RETURN");
		long asOf = df.parseMins("20070105_1632").getTime();
		long oldest = df.parseMins("20070101_0000").getTime();
		Map<Security, Bar> as = widget.getPricesAsOf(secs, asOf, oldest, exch);
		System.out.println(as.get(new Security(5334)));

		// as of
		System.out.println("TEST6, ASOF SOMETHING TO RETURN");
		asOf = df.parseMins("20100101_0000").getTime();
		oldest = df.parseMins("20091201_0000").getTime();
		as = widget.getPricesAsOf(secs, asOf, oldest, exch);
		System.out.println(as.get(new Security(5334)).toHRString());

		System.out.println("TEST7, MULTIPLE DAYS TEST CACHING");
		millis1 = df.parseMins("20100102_1432").getTime();
		millis2 = df.parseMins("20100107_1537").getTime();
		widget.preload(CollectionUtils.toSet(new Security(5334)), millis1, millis2);
		Vector<Bar> res1 = widget.getPrices(new Security(5334), millis1 + Time.MILLIS_PER_DAY, millis2 - Time.MILLIS_PER_DAY, exch);
		for (Bar bar : res1) {
			System.out.println(bar.toHRString());
		}

		System.out.println("TEST8, MULTIPLE DAYS ASOF CACHING");
		millis1 = df.parseMins("20100102_1432").getTime();
		millis2 = df.parseMins("20100107_1537").getTime();
		// widget.preload(CollectionUtilities.toSet(new Security(5334)),
		// millis1, millis2);
		Bar as1 = widget.getPricesAsOf(new Security(5334), millis2 - Time.MILLIS_PER_DAY, millis1 + Time.MILLIS_PER_DAY, exch);
		System.out.println(as1.toHRString());
	}

	public static void main(String[] args) throws Exception {
		// Security sec = new Security(5334);
		// FilePriceBarWidget widget = new FilePriceBarWidget();
		// System.out.println(widget.getPricesAsOf(sec, Time.now(), 0, Exchange.Type.NYSE));
		tests();
		// Properties config = new Properties();
		// String configFile = System.getenv("CONFIG_DIR") + "/" + "calc.cfg";
		// config.load(new FileReader(configFile));
		// Universe uni = new Universe(config);
		//
		// FilePriceBarWidget widget = new FilePriceBarWidget();
		//
		// long millis1 = df.dfMins.parse("20100104_1430").getTime();
		// long millis2 = df.dfMins.parse("20100104_1530").getTime();
		// Map<Security, Vector<Bar>> res = widget.getPrices(uni.secs, millis1,
		// millis2);
		//
		// for (Entry<Security, Vector<Bar>> e : res.entrySet()) {
		// for (Bar bar : e.getValue()) {
		// System.out.println(bar.toHRString());
		// }
		// }
	}
}
