package ase.reports;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.TreeSet;
import java.util.Vector;
import java.util.logging.Logger;

import ase.apps.DailyManager.OutputType;
import ase.calculator.DailyPriceCalculator;
import ase.calculator.Forecast;
import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.DistributionSummary;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.datacube.Aggregator;
import ase.datacube.BucketAggregator;
import ase.datacube.BucketAggregator.BoundaryType;
import ase.datacube.CardinalAggregator;
import ase.datacube.MultiDimAggregator;
import ase.datacube.Table;
import ase.datacube.Tuple;
import ase.portfolio.Fill;
import ase.portfolio.Fill.LiquidityType;
import ase.portfolio.Fill.Tactic;
import ase.portfolio.Order;
import ase.portfolio.PortfolioUtils;
import ase.timeseries.Bar;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;

public class SlippageReport {
	private static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(SlippageReport.class.getName());
	private static final UnifiedDataSource uSource = new UnifiedDataSource(false);

	private static enum StatType {
		SUM, MEAN, PCT, MEDIAN
	};

	private static class StatTypeClass {
		public StatType type;
		public Pair<Integer, Integer> data;
		double mult = 100;

		public StatTypeClass(StatType type) {
			this.type = type;
		}

		public StatTypeClass(StatType type, int num, int denom, double mult) {
			this.type = type;
			this.data = new Pair<Integer, Integer>(num, denom);
			this.mult = mult;
		}
	}

	public static Report generateSlippageReport(String location, Collection<Long> dates) throws Exception {
		Vector<AttrType> dimensions = new Vector<AttrType>();
		Vector<AttrType> dim4fillAggr = new Vector<AttrType>();
		Vector<AttrType> dim4muFcast = new Vector<AttrType>();
		Vector<String> measures = new Vector<String>();
		Vector<Aggregator> aggregators = new Vector<Aggregator>();
		Vector<StatTypeClass> statTypes = new Vector<StatTypeClass>();

		String dummyAll = "ALL";
		dimensions.add(new AttrType("advp", Type.N));
		dimensions.add(new AttrType("minsIntoTrading", Type.N));
		dimensions.add(new AttrType("aggr", Type.S));
		dimensions.add(new AttrType("server", Type.S));
		dimensions.add(new AttrType("orderSize", Type.N));
		dimensions.add(new AttrType("mu", Type.N));
		dimensions.add(new AttrType("direction", Type.S));
		dimensions.add(new AttrType("dummy", Type.S));
		// TODO add even fill lot buckets
		// dimensions.add(new AttrType("evenLot", Type.N));

		dim4fillAggr.add(new AttrType("tactic", Type.S));
		dim4fillAggr.add(new AttrType("exchange", Type.S));

		dim4muFcast.add(new AttrType("mu", Type.S));

		int ii = 0;
		measures.add("$ ordered");
		statTypes.add(new StatTypeClass(StatType.SUM));

		ii++;
		measures.add("$ filled");
		statTypes.add(new StatTypeClass(StatType.SUM));

		ii++;
		measures.add("$ not filled");
		statTypes.add(new StatTypeClass(StatType.SUM));

		ii++;
		measures.add("% order $ filled");
		statTypes.add(new StatTypeClass(StatType.PCT, 1, 0, 100));

		ii++;
		measures.add("o2f bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("o2c bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 0, 10000));

		ii++;
		measures.add("f2five bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("f2ten bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("f2hour bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("f2c bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("ep2f bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 1, 10000));

		ii++;
		measures.add("uf2five bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 2, 10000));

		ii++;
		measures.add("uf2ten bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 2, 10000));

		ii++;
		measures.add("uf2c bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 2, 10000));

		ii++;
		measures.add("o2f secs");
		statTypes.add(new StatTypeClass(StatType.MEDIAN));

		ii++;
		measures.add("o2firstf secs");
		statTypes.add(new StatTypeClass(StatType.MEDIAN));

		ii++;
		measures.add("cr2o bps");
		statTypes.add(new StatTypeClass(StatType.PCT, ii, 0, 10000));

		ii++;
		measures.add("cr2o secs");
		statTypes.add(new StatTypeClass(StatType.MEDIAN));

		Table table = new Table(dimensions.toArray(new AttrType[dimensions.size()]), measures.toArray(new String[measures.size()]));
		Table table4fillAggr = new Table(dim4fillAggr.toArray(new AttrType[dim4fillAggr.size()]), measures.toArray(new String[measures.size()]));
		Table table4muFcast = new Table(dim4muFcast.toArray(new AttrType[dim4muFcast.size()]), measures.toArray(new String[measures.size()]));

		for (Long currentDate : dates) {
			List<Fill> dayFills = PortfolioUtils.loadMuifiedFills(location, currentDate, false);
			Vector<Triplet<Order, Vector<Fill>, Fill>> order2fills = invertFills(dayFills);
			Map<Long, Long> orderid2exec_ts = PortfolioUtils.loadExecServerOrderTs(location, currentDate);
			CalcResults calcres = getCalcres(location, currentDate);
			Map<Security, Attribute> sec2advp = calcres.getResult(DailyPriceCalculator.ADVP);
			Map<Security, String> sec2server = loadSecToServerMappings(location, currentDate);
			// preload bar data
			uSource.barSource.preload(calcres.getSecurities(), currentDate, currentDate);
			calcres = null;

			for (Triplet<Order, Vector<Fill>, Fill> e : order2fills) {
				Order order = e.first;
				Vector<Fill> orderFills = e.second;
				Vector<Fill> compFill = new Vector<Fill>(1);
				if (e.third != null)
					compFill.add(e.third);

				// compute dimensions
				Double advp = (sec2advp.containsKey(order.sec)) ? sec2advp.get(order.sec).asDouble() : null;
				Double minsIntoDay = (double) (order.ts - Exchange.openTime(currentDate, order.sec.primaryExchange)) / Time.MILLIS_PER_MINUTE;
				String aggr = String.valueOf(order.aggr);
				String server = sec2server.get(order.sec);
				server = (server == null) ? "unknown" : server;
				server = (orderFills.get(0).tactic == Fill.Tactic.MKT_ON_CLOSE) ? "MOC" : server;
				Double orderSize = (advp != null) ? 100.0 * Math.abs(order.shares) * order.prc / advp : null;
				Double mu = Math.abs(100.0 * order.mus.get(new Forecast("FULL", ase.calculator.Forecast.Type.MU)));
				String direction = (order.shares >= 0) ? "buy" : "sell";
				String dummy = dummyAll;

				// compute measures
				Double dollarsOrdered = Math.abs(order.shares) * order.prc;
				Double dollarsFilled = dollarsFilled(orderFills);
				Double dollarsNotFilled = dollarsFilled(compFill);
				Double o2f = orderToFillSlippage(order, orderFills);
				Double o2c = orderToTsSlippage(order, Time.fromDays(1));
				Double f2five = fillToTsSlippage(order, orderFills, 5 * Time.MILLIS_PER_MINUTE);
				Double f2ten = fillToTsSlippage(order, orderFills, 10 * Time.MILLIS_PER_MINUTE);
				Double f2hour = fillToTsSlippage(order, orderFills, Time.MILLIS_PER_HOUR);
				Double f2close = fillToCloseSlippage(order, orderFills);
				Double ep2f = expectedPriceToFillSlippage(order, orderFills);
				Double uf2five = fillToTsSlippage(order, compFill, 5 * Time.MILLIS_PER_MINUTE);
				Double uf2ten = fillToTsSlippage(order, compFill, 10 * Time.MILLIS_PER_MINUTE);
				Double uf2c = fillToCloseSlippage(order, compFill);
				Double o2ftime = orderToFillSecs(order, orderFills);
				Double o2firstftime = orderToFirstFillSecs(order, orderFills);
				Double cr2o = (orderid2exec_ts.containsKey(order.orderid)) ? orderToTsSlippage(order, orderid2exec_ts.get(order.orderid) - order.ts) : null;
				Double cr2otime = (orderid2exec_ts.containsKey(order.orderid)) ? 1.0 * (orderid2exec_ts.get(order.orderid) - order.ts) / Time.MILLIS_PER_SECOND
						: null;

				// create tuple
				Tuple tuple = table.createTuple();

				Object[] dimensionVals = {advp, minsIntoDay, aggr, server, orderSize, mu, direction, dummy };
				tuple.setDimensionArray(dimensionVals);

				Double[] measureVals = { dollarsOrdered, dollarsFilled, dollarsNotFilled, 0.0, o2f, o2c, f2five, f2ten, f2hour, f2close, ep2f, uf2five, uf2ten,
						uf2c, o2ftime, o2firstftime, cr2o, cr2otime };
				tuple.setMeasureArray(measureVals);

				table.addTuple(tuple);

				Fill firstFill = orderFills.get(0);
				Map<Forecast, Fill> muifiedFirstFill = firstFill.allocateMus();
				for (int ff = 1; ff < orderFills.size(); ff++) {
					if (Math.signum(orderFills.get(ff).shares) * Math.signum(order.shares) < 0) {
						if (order.orderid != 0)
							log.severe("Fill shares and order shares have opposite signs for orderid " + order.orderid + " on " + currentDate);
					}
				}
				for (Map.Entry<Forecast, Fill> ee : muifiedFirstFill.entrySet()) {
					String fcast = ee.getKey().name;
					double frac = ee.getValue().shares / firstFill.shares;

					Tuple subTuple = table4muFcast.createTuple();
					subTuple.setDimension(0, fcast);
					Double[] subMeasureVals = { frac * dollarsOrdered, frac * dollarsFilled, frac * dollarsNotFilled, 0.0, frac * o2f,
							(o2c == null ? null : frac * o2c), (f2five == null ? null : frac * f2five), (f2ten == null ? null : frac * f2ten),
							(f2hour == null ? null : frac * f2hour), (f2close == null ? null : frac * f2close), (ep2f == null ? null : frac * ep2f),
							(uf2five == null ? null : frac * uf2five), (uf2five == null ? null : frac * uf2five), (uf2c == null ? null : frac * uf2c), o2ftime,
							o2firstftime, (cr2o == null ? null : frac * cr2o), cr2otime };
					subTuple.setMeasureArray(subMeasureVals);

					table4muFcast.addTuple(subTuple);
				}
			}

			ListIterator<Fill> li = dayFills.listIterator();
			while (li.hasNext()) {
				Fill fill = li.next();
				Order order = fill.order;
				Vector<Fill> orderFills = new Vector<Fill>(1);
				orderFills.add(fill);

				if (order == null) {
					log.warning("Failed to map fill " + fill.fillid + " to an order.");
					continue;
				}

				// compute dimensions
				String tactic = fill.tactic.toString();
				String exchange = fill.venue.toString();

				// compute measures
				Double dollarsOrdered = Math.abs(fill.shares) * order.prc;
				Double dollarsFilled = Math.abs(fill.shares) * fill.price;
				Double o2f = orderToFillSlippage(order, orderFills);
				Double o2c = orderToTsSlippage(order, Time.fromDays(1));
				o2c = (o2c != null) ? o2c / order.shares * fill.shares : null;
				Double f2five = fillToTsSlippage(order, orderFills, 5 * Time.MILLIS_PER_MINUTE);
				Double f2ten = fillToTsSlippage(order, orderFills, 10 * Time.MILLIS_PER_MINUTE);
				Double f2hour = fillToTsSlippage(order, orderFills, Time.MILLIS_PER_HOUR);
				Double f2close = fillToCloseSlippage(order, orderFills);
				Double ep2f = expectedPriceToFillSlippage(order, orderFills);
				Double o2ftime = orderToFillSecs(order, orderFills);
				Double o2firstftime = 0.0;
				Double cr2o = null;
				Double cr2otime = null;

				// create tuple
				Tuple tuple = table4fillAggr.createTuple();
				tuple.setDimension(0, tactic);
				tuple.setDimension(1, exchange);

				Double[] measureVals = { dollarsOrdered, dollarsFilled, Double.NaN, 0.0, o2f, o2c, f2five, f2ten, f2hour, f2close, ep2f, 0.0, 0.0, 0.0,
						o2ftime, o2firstftime, cr2o, cr2otime };
				tuple.setMeasureArray(measureVals);

				table4fillAggr.addTuple(tuple);
			}
		}

		aggregators.add(new BucketAggregator(table, 0, new double[] { 5e6, 10e6, 20e6, 50e6, 100e6, 200e6 }, BoundaryType.BREAKPOINT));
		aggregators.add(new BucketAggregator(table, 1, new double[] { 60, 120, 180, 240, 300, 360 }, BoundaryType.BREAKPOINT));
		aggregators.add(new CardinalAggregator(table, 2));
		aggregators.add(new CardinalAggregator(table, 3));
		aggregators.add(new BucketAggregator(table, 4, new double[] { 0.001, 0.01, 0.1, 1.0 }, BoundaryType.BREAKPOINT));
		aggregators.add(new BucketAggregator(table, 5, new double[] { 0, 0.025, 0.05, 0.10, 0.20, 0.40 }, BoundaryType.BREAKPOINT));
		aggregators.add(new MultiDimAggregator(table, new Aggregator[] { new CardinalAggregator(table, 2),
				new BucketAggregator(table, 4, new double[] { 0.001, 0.01, 0.1, 1.0 }, BoundaryType.BREAKPOINT) }));
		aggregators.add(new CardinalAggregator(table, 6));
		aggregators.add(new CardinalAggregator(table, 7));
		aggregators.add(new CardinalAggregator(table4muFcast, 0));
		aggregators.add(new CardinalAggregator(table4fillAggr, 0));
		aggregators.add(new CardinalAggregator(table4fillAggr, 1));

		Vector<String> header = new Vector<String>();
		header.add("bucket");
		header.add("count");
		header.addAll(measures);
		Report report = new Report(header.size(), header.size());
		report.addHeader(header);
		if (dates.size() > 1) {
			Vector<Long> sortedDates = new Vector<Long>(dates);
			Collections.sort(sortedDates);
			report.addPreHeader("Covering days " + Time.toYYYYMMDD(sortedDates.firstElement()) + " - " + Time.toYYYYMMDD(sortedDates.lastElement()));
		}

		for (Aggregator agg : aggregators) {
			Vector<Pair<String, DistributionSummary[]>> stats = agg.aggregate();

			for (Pair<String, DistributionSummary[]> p : stats) {
				Vector<String> body = new Vector<String>();
				body.add(p.first);
				body.add(Float.toString((int) p.second[0].count));
				for (int kk = 0; kk < p.second.length; kk++) {
					StatTypeClass stat = statTypes.get(kk);
					switch (stat.type) {
					case MEAN:
						body.add(df.fformat((double) p.second[kk].mean));
						break;
					case MEDIAN:
						body.add(df.fformat((double) p.second[kk].median));
						break;
					case SUM:
						body.add(df.fformat(p.second[kk].count * (double) p.second[kk].mean));
						break;
					case PCT:
						double num = p.second[stat.data.first].count * p.second[stat.data.first].mean;
						double denom = p.second[stat.data.second].count * p.second[stat.data.second].mean;
						double pct = (!Double.isNaN(denom) && denom != 0.0) ? stat.mult * num / denom : Double.NaN;
						body.add(df.fformat(pct));
						break;
					default:
						break;
					}
				}
				report.addBody(body);
			}
		}

		return report;
	}

	protected static Double expectedPriceToFillSlippage(Order order, Vector<Fill> orderFills) {
		double eprc = (order.shares > 0) ? (order.prc + order.eslip / order.shares) : (order.prc - order.eslip / (-order.shares));
		double sum = 0;
		for (Fill fill : orderFills) {
			sum += fill.shares * (fill.price - eprc);
		}
		return sum;
	}

	protected static Double orderToFillSlippage(Order order, Vector<Fill> orderFills) {
		double sum = 0;
		for (Fill fill : orderFills) {
			sum += fill.shares * (fill.price - order.prc);
		}
		return sum;
	}

	protected static Double fillToTsSlippage(Order order, Vector<Fill> orderFills, long millis) throws Exception {
		double sum = 0;
		for (Fill fill : orderFills) {
			long ts = fill.ts + millis;
			if (ts > Exchange.closeTime(fill.ts, order.sec.primaryExchange)) {
				return null;
			}
			Bar bar = uSource.barSource.getBarAsOf(CollectionUtils.toSet(order.sec), ts + uSource.barSource.BAR_SPAN, order.sec.primaryExchange).get(order.sec);
			if (bar == null)
				return null;
			double price = interpolatePrice(bar, ts);
			if (!(price > 0))
				return null;
			sum += fill.shares * (price - fill.price);
		}
		return sum;
	}

	protected static Double orderToTsSlippage(Order order, Vector<Fill> orderFills, long millis) throws Exception {
		double sum = 0;
		for (Fill fill : orderFills) {
			long ts = fill.ts + millis;
			if (ts > Exchange.closeTime(fill.ts, order.sec.primaryExchange)) {
				return null;
			}
			Bar bar = uSource.barSource.getBarAsOf(CollectionUtils.toSet(order.sec), ts + uSource.barSource.BAR_SPAN, order.sec.primaryExchange).get(order.sec);
			if (bar == null)
				return null;
			double price = interpolatePrice(bar, ts);
			if (!(price > 0))
				return null;
			sum += fill.shares * (price - fill.price);
		}
		return sum;
	}

	protected static Double fillToCloseSlippage(Order order, Vector<Fill> orderFills) throws Exception {
		double sum = 0;
		for (Fill fill : orderFills) {
			long ts = Exchange.closeTime(fill.ts, order.sec.primaryExchange);
			Bar bar = uSource.barSource.getBarAsOf(CollectionUtils.toSet(order.sec), ts + uSource.barSource.BAR_SPAN, order.sec.primaryExchange).get(order.sec);
			if (bar == null)
				return null;
			double price = interpolatePrice(bar, ts);
			if (!(price > 0))
				return null;
			sum += fill.shares * (price - fill.price);
		}
		return sum;
	}

	protected static Double orderToTsSlippage(Order order, long millis) throws Exception {
		long ts = Math.min(order.ts + millis, Exchange.closeTime(order.ts, order.sec.primaryExchange));
		Bar bar = uSource.barSource.getBarAsOf(CollectionUtils.toSet(order.sec), ts + uSource.barSource.BAR_SPAN, order.sec.primaryExchange).get(order.sec);
		if (bar == null)
			return null;
		double price = interpolatePrice(bar, ts);
		if (!(price > 0))
			return null;
		return order.shares * (price - order.prc);
	}

	protected static Double dollarsFilled(Vector<Fill> orderFills) {
		double sum = 0;
		for (Fill fill : orderFills) {
			sum += Math.abs(fill.shares) * fill.price;
		}
		return sum;
	}

	protected static Double orderToFillSecs(Order order, Vector<Fill> orderFills) {
		// weighted average
		double denom = 0;
		for (Fill fill : orderFills) {
			denom += fill.shares;
		}
		double sum = 0;
		for (Fill fill : orderFills) {
			sum += fill.shares / denom * (fill.ts - order.ts) / Time.MILLIS_PER_SECOND;
		}
		return sum;
	}

	protected static Double orderToFirstFillSecs(Order order, Vector<Fill> orderFills) {
		// Fill fill = orderFills.firstElement();
		// return 1.0 * (fill.ts - order.ts) / Time.MILLIS_PER_SECOND;

		Double minSecs = Double.MAX_VALUE;
		for (Fill f : orderFills) {
			double secs = 1.0 * (f.ts - order.ts) / Time.MILLIS_PER_SECOND;
			if (secs < minSecs)
				minSecs = secs;
		}

		return minSecs;
	}

	// XXX going to to have to consider whether the price is taken as a mid or a trade...
	protected static double interpolatePrice(Bar bar, long ts) {
		assert ts >= bar.open_ts && ts <= bar.close_ts;
		double m = 1.0 * (ts - bar.open_ts) / uSource.barSource.BAR_SPAN;
		return m * bar.close + (1 - m) * bar.open;
	}

	// /XXX gets the first calcres of day
	protected static CalcResults getCalcres(String location, long currentDate) throws Exception {
		NavigableMap<Long, File> cf = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres", FileUtils.CALCRES_PATTERN);
		return (cf == null) ? null : CalcResults.restore(cf.firstEntry().getValue());
	}

	// For each order, get its fills, and a dummy "complementary" fill, which is the part of the order that wasn't filled
	protected static Vector<Triplet<Order, Vector<Fill>, Fill>> invertFills(List<Fill> fills) {
		Vector<Triplet<Order, Vector<Fill>, Fill>> result = new Vector<Triplet<Order, Vector<Fill>, Fill>>();
		Map<Order, Vector<Fill>> order2fills = new HashMap<Order, Vector<Fill>>();

		for (Fill fill : fills) {
			if (fill.order == null)
				continue;
			Vector<Fill> orderFills = order2fills.get(fill.order);
			if (orderFills == null) {
				orderFills = new Vector<Fill>();
				order2fills.put(fill.order, orderFills);
			}
			orderFills.add(fill);
		}
		// just in case, sort fills by ts
		for (Vector<Fill> orderFills : order2fills.values()) {
			Collections.sort(orderFills);
		}

		// now, create the dummy fill and the final result
		for (Map.Entry<Order, Vector<Fill>> e : order2fills.entrySet()) {
			double sum = 0;
			for (Fill f : e.getValue()) {
				sum += f.shares;
			}

			Order o = e.getKey();
			Fill compFill = null;
			// elaborate to protect us against overfills
			if ((o.shares > 0 && o.shares > sum) || (o.shares < 0 && o.shares < sum))
				compFill = new Fill(o.sec, o.ts, o.shares - sum, o.prc, o, -1, ase.data.Exchange.Type.NONE, LiquidityType.UNK, o.orderid, Tactic.UNKNOWN);

			result.add(new Triplet<Order, Vector<Fill>, Fill>(o, e.getValue(), compFill));
		}

		return result;
	}

	protected static Map<Security, String> loadSecToServerMappings(String location, long currentDate) throws IOException {
		Map<Security, String> result = new HashMap<Security, String>();
		File tickerToServerFile = new File(location + "/" + df.toYYYYMMDD(currentDate) + "/exec_tickers.txt");
		if (!tickerToServerFile.exists()) {
			log.warning("Failed to locate ticker2server file " + tickerToServerFile.toString());
			return result;
		}

		Map<String, Integer> ticker2secid = new HashMap<String, Integer>();
		File tickerFile = new File(location + "/" + df.toYYYYMMDD(currentDate) + "/tickers.txt");
		if (!tickerFile.exists()) {
			log.warning("Failed to locate ticker file " + tickerFile.toString());
			return result;
		}

		String line;
		BufferedReader reader = FileUtils.openFileReader(tickerFile);
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			String ticker = tokens[0];
			Integer secid = Integer.parseInt(tokens[1]);

			ticker2secid.put(ticker, secid);
		}
		reader.close();

		reader = FileUtils.openFileReader(tickerToServerFile);
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			String ticker = tokens[0];
			String server = tokens[1];
			Integer secid = ticker2secid.get(ticker);

			if (secid != null) {
				result.put(new Security(secid), server);
			}
		}
		reader.close();

		return result;
	}

	public static void dailyReport(String location, Exchange.Type exch, long currentDate, Set<OutputType> output) throws Exception {
		// get last 20 days
		int days = 20;
		TreeSet<Long> dates = new TreeSet<Long>();
		long date = currentDate;
		while (days > 0 && Time.toYYYYMMDD(date) > 20110507) {
			dates.add(date);
			date = Exchange.prevTradingDay(date, exch);
			--days;
		}

		// Generate last 20 day report
		Report longReport = generateSlippageReport(location, dates);
		// generate today's report
		Report shortReport = generateSlippageReport(location, CollectionUtils.toSet(currentDate));

		StringBuilder sb = new StringBuilder();
		sb.append(longReport.generateReport("  |  ", true));
		sb.append("\n\n");
		sb.append(shortReport.generateReport("  |  ", true));
		String stringReport = sb.toString();

		if (output.contains(OutputType.SCREEN)) {
			System.out.println(stringReport);
		}
		if (output.contains(OutputType.FILE)) {
			File reportDir = new File(System.getenv("ROOT_DIR") + "/reports/" + System.getenv("STRAT") + "/slippage/" + df.toYYYYMMDD(currentDate));
			reportDir.mkdirs();
			Writer writer = FileUtils.makeWriter(new File(reportDir, "slip." + df.toYYYYMMDD(currentDate) + ".txt"));
			writer.write(stringReport);
			writer.close();
		}
		if (output.contains(OutputType.EMAIL)) {
			Email.email("Slippage report for day " + df.toYYYYMMDD(currentDate), stringReport);
		}
	}
}
