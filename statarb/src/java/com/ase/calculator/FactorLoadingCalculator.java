package ase.calculator;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Map.Entry;
import java.util.NavigableMap;
import java.util.ListIterator;
import java.util.NavigableSet;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.lang.ArrayUtils;
import org.apache.commons.math.stat.regression.SimpleRegression;

import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.DateAttribute;
import ase.data.DbAttrType;
import ase.data.DistributionSummary;
import ase.data.Estimate;
import ase.data.EstimateSeries;
import ase.data.Exchange;
import ase.data.FactorLoadings;
import ase.data.Price;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLEstimateWidget;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.Bar;
import ase.timeseries.DailyBarTimeSeries;
import ase.timeseries.TimeSeriesUtil;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;
import ase.util.math.ASEMath;

public class FactorLoadingCalculator {
	private static final Logger log = LoggerFactory.getLogger(FactorLoadingCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final FactorLoadings factorLoadings;
	private final Exchange.Type primaryExch;
	private final int num_factor_days;

	private long lastcalc = 0L;

	// XXX need to add live prices!!!
	public FactorLoadingCalculator(UnifiedDataSource uSource, FactorLoadings factorLoadings, int num_factor_days, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.factorLoadings = factorLoadings;
		this.num_factor_days = num_factor_days;
		this.primaryExch = primaryExch;
	}

	public void setLastCalc(long lastcalc) {
		this.lastcalc = lastcalc;
	}

	private boolean needRecalc(long asof) {
		return Time.midnight(lastcalc) != Time.midnight(asof);
	}

	public AttrType calculateDummy(long asof) {
		AttrType factor = new CalcAttrType(FactorLoadings.MONITOR_FACTOR_PREFIX + "DUMMY");
		if (!needRecalc(asof)) {
			log.info("Not recalculating " + factor);
			return null;
		}
		log.info("Calculating " + factor);

		long date1 = Time.midnight(Exchange.subtractTradingDays(asof, num_factor_days, primaryExch));
		for (Security sec : factorLoadings.getSecurities()) {
			// XXX not quite right, should only add factor for stocks that
			// were definitely in the universe on t-1, t-2 etc...
			factorLoadings.setFactor(sec, factor, date1, 1.0);
		}
		return factor;
	}

	public AttrType calculateUni(long asof) {
		AttrType factor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "UNI");
		if (!needRecalc(asof)) {
			log.info("Not recalculating " + factor);
			return null;
		}
		log.info("Calculating " + factor);

		long date1 = Time.midnight(Exchange.subtractTradingDays(asof, num_factor_days, primaryExch));
		for (Security sec : factorLoadings.getSecurities()) {
			// XXX not quite right, should only add factor for stocks that
			// were definitely in the universe on t-1, t-2 etc...
			factorLoadings.setFactor(sec, factor, date1, 1.0);
		}
		return factor;
	}

	public Set<AttrType> calculatePrice(long asof) throws Exception {
		Set<AttrType> ret = new HashSet<AttrType>();
		AttrType factor_h = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "PRICE_H");
		AttrType factor_m = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "PRICE_M");
		AttrType factor_l = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "PRICE_L");
		ret.add(factor_h);
		ret.add(factor_m);
		ret.add(factor_l);

		if (!needRecalc(asof)) {
			log.info("Not recalculating price factors..");
			return ret;
		}
		log.info("Calculating price factors...");
		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + 1, primaryExch));
		// /XXX set range to [start date, prev close]
		Map<Security, DailyBarTimeSeries> pMap = uSource.getDailyBarTimeSeries(factorLoadings.getSecurities(), startdate,
				Exchange.prevClose(asof, primaryExch), primaryExch);
		for (Security sec : pMap.keySet()) {
			DailyBarTimeSeries dbts = pMap.get(sec);
			ListIterator<Bar> bars = dbts.getBars();
			while (bars.hasNext()) {
				Bar bar = bars.next();
				// XXX bars can be null for days for which we have no data (e.g., halted trading, new security, bad compustat data etc)
				if (bar == null)
					continue;
				AttrType bucket = null;
				double price = bar.close;
				if (price < 10.0) {
					bucket = factor_l;
				}
				else if (price > 80.0) {
					bucket = factor_h;
				}
				else {
					bucket = factor_m;
				}
				factorLoadings.setFactor(sec, bucket, Exchange.closeTime(bar.close_ts, primaryExch), 1.0);
			}
		}
		return ret;
	}

	public Set<AttrType> calculateForecastFactors(long asof) throws Exception {
	    log.info("Calculating forecast factors...");
	    Set<AttrType> ret = new HashSet<AttrType>();
	    Map<String,DbAttrType> forecasts = new HashMap<String,DbAttrType>();
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "HLB", new DbAttrType("fc_hlB"));
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "RRB", new DbAttrType("fc_rrb"));
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "O2CVADJ", new DbAttrType("fc_o2cvadj_new"));
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "CEST", new DbAttrType("fc_cestd10"));
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "CTG", new DbAttrType("fc_ctgd10"));
        forecasts.put(FactorLoadings.MONITOR_FACTOR_PREFIX + "CRTG", new DbAttrType("fc_crtg10"));
        for (Map.Entry<String, DbAttrType> ent : forecasts.entrySet()) {            
            Map<Security, Attribute> attrMapCurr = uSource.attrSource.getAttrAsOf(factorLoadings.getSecurities(), ent.getValue(), asof);
            Map<Security, Attribute> attrMapPast = uSource.attrSource.getAttrAsOf(factorLoadings.getSecurities(), ent.getValue(), Exchange.addTradingDays(asof, -2, primaryExch));
            CalcAttrType forecastCurr = new CalcAttrType(ent.getKey() + "_C");
            CalcAttrType forecastPast = new CalcAttrType(ent.getKey() + "_2");
            for ( Attribute attr : attrMapCurr.values()) {
                factorLoadings.setFactor(attr.sec, forecastCurr, asof, attr.asDouble());
            }
            for ( Attribute attr : attrMapPast.values()) {
                factorLoadings.setFactor(attr.sec, forecastPast, asof, attr.asDouble());
            }
            ret.add(forecastCurr);
            ret.add(forecastPast);
        }
        return ret;
	}

	public AttrType calculateMom(long asof, int lookback, boolean intraday) throws Exception {
		AttrType factor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "MOM" + lookback);
		log.info("Calculating " + factor);

		Vector<Triplet<Security, Long, Double>> rawLoadings = new Vector<Triplet<Security, Long, Double>>();
		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + lookback + 1, primaryExch));
		Map<Security, DailyBarTimeSeries> pMap = uSource.getDailyBarTimeSeries(factorLoadings.getSecurities(), startdate, asof, primaryExch);
		double tot = 0.0, totsq = 0.0;
		int cnt = 0;
		int lag = intraday ? 0 : 1;
		long millis = intraday ? asof : Exchange.prevClose(asof, primaryExch);
		for (; lag <= num_factor_days; millis = Exchange.prevClose(millis, primaryExch), lag++) {
			if (lag == 0 && !(millis > Exchange.openTime(millis, primaryExch))) {
				log.warning("Skipping calculating " + factor + " for " + df.debugFormat(millis) + ". We are intraday and exchange is closed.");
				continue;
			}
			// /XXX Take out this optimization for now. In order to re-introduce it, we need to save somewhere the mean and sigma of the raw loadings.
			// /Not sure if it is worth the trouble, as doing everything from scratch costs <0.5sec
			// // only calc hist once per day...
			// if (!needRecalc(asof) && lag > 0) {
			// log.info("Not recalculating historical " + factor);
			// break;
			// }
			log.info("Calculating " + factor + " to " + df.format(millis));
			for (Security sec : pMap.keySet()) {
				DailyBarTimeSeries dpts = pMap.get(sec);
				if (dpts == null) {
					log.warning("No prices for security: " + sec.getSecId());
					continue;
				}

				double ret = dpts.getLogrel(lag, lookback);
				if (Double.isNaN(ret)) {
					log.warning("skipping " + factor + " for sec: " + sec.getSecId() + ", date: " + df.format(millis) + " because bad logrel at lag " + lag);
					continue;
				}
				tot += ret;
				totsq += ret * ret;
				cnt++;

				rawLoadings.add(new Triplet<Security, Long, Double>(sec, millis, ret));
			}
		}

		// center and normalize the raw loadings
		double allMean = tot / cnt;
		double allSigma = ASEMath.sigma(tot, totsq, cnt);
		for (Triplet<Security, Long, Double> e : rawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= allMean;
			exp /= allSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, factor, ts, exp);
		}
		log.info("Momentum dist: " + allMean + " / " + allSigma);
		return factor;
	}

	public AttrType calculateVol(long asof, int lookback, boolean intraday) throws Exception {
		AttrType factor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "VOL" + lookback);
		log.info("Calculating " + factor);

		Vector<Triplet<Security, Long, Double>> rawLoadings = new Vector<Triplet<Security, Long, Double>>();
		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + lookback + 1, primaryExch));
		Map<Security, DailyBarTimeSeries> pMap = uSource.getDailyBarTimeSeries(factorLoadings.getSecurities(), startdate, asof, primaryExch);
		int lag = intraday ? 0 : 1;
		long millis = intraday ? asof : Exchange.prevClose(asof, primaryExch);
		double tot = 0.0, totsq = 0.0;
		int cnt = 0;
		for (; lag <= num_factor_days; millis = Exchange.prevClose(millis, primaryExch), lag++) {
			if (lag == 0 && !(millis > Exchange.openTime(millis, primaryExch))) {
				log.warning("Skipping calculating " + factor + " for " + df.debugFormat(millis) + ". We are intraday and exchange is closed.");
				continue;
			}
			// /XXX Take out this optimization for now. In order to re-introduce it, we need to save somewhere the mean and sigma of the raw loadings.
			// /Not sure if it is worth the trouble, as doing everything from scratch costs <0.5sec
			// only calc hist once per day...
			// if (!needRecalc(asof) && lag > 0) {
			// log.info("Not recalculating historical " + factor);
			// break;
			// }
			log.info("calculating " + factor + " to " + df.format(millis));
			for (Security sec : pMap.keySet()) {
				DailyBarTimeSeries dpts = pMap.get(sec);
				double[] logrels = dpts.getLogrelArray(1, lag, lookback);
				double sigma = ASEMath.meansig(logrels).second;
				if (Double.isNaN(sigma)) {
					log.warning("Could not calculate sigma for " + sec.getSecId() + " on " + df.format(millis));
					continue;
				}
				tot += sigma;
				totsq += sigma * sigma;
				cnt++;
				rawLoadings.add(new Triplet<Security, Long, Double>(sec, millis, sigma));
			}
		}

		// center and normalize the raw loadings
		double allMean = tot / cnt;
		double allSigma = ASEMath.sigma(tot, totsq, cnt);
		for (Triplet<Security, Long, Double> e : rawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= allMean;
			exp /= allSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, factor, ts, exp);
		}

		log.info("Vol dist: " + allMean + " / " + allSigma);
		return factor;
	}

	public Pair<Set<AttrType>, Set<AttrType>> calculateBarra(long asof) throws Exception {
		if (!needRecalc(asof)) {
			log.info("Not recalculating Barra factors...");
			return new Pair<Set<AttrType>, Set<AttrType>>(new HashSet<AttrType>(), new HashSet<AttrType>());
		}
		BarraCalculator barraCalc = new BarraCalculator(uSource, num_factor_days, primaryExch);
		return barraCalc.calculate(factorLoadings, asof);
	}

	public Set<AttrType> calculateGICS(long asof) throws Exception {
		if (!needRecalc(asof)) {
			log.info("Not recalculating GICS factors...");
			return new HashSet<AttrType>();
		}
		GICSCalculator gicsCalc = new GICSCalculator(uSource, num_factor_days, primaryExch);
		return gicsCalc.calculate(factorLoadings, asof);
	}

	public Set<AttrType> calculateCredit(long asof) throws Exception {
		if (!needRecalc(asof)) {
			log.info("Not recalculating Credit factors...");
			return new HashSet<AttrType>();
		}
		CreditCalculator credCalc = new CreditCalculator(uSource, num_factor_days, primaryExch);
		return credCalc.calculate(factorLoadings, asof);
	}

	public Set<AttrType> calculateSizeFacs(long asof) throws Exception {
		Set<AttrType> ret = new HashSet<AttrType>();
		if (!needRecalc(asof)) {
			log.info("Not recalculating Size Factors...");
			return ret;
		}

		log.info("Calculating Size Factors");
		AttrType sizeFactorType = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "SIZE");
		AttrType sizenlFactorType = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "SIZENL");

		Vector<Triplet<Security, Long, Double>> sizeRawLoadings = new Vector<Triplet<Security, Long, Double>>();
		Vector<Triplet<Security, Long, Double>> sizeNlRawLoadings = new Vector<Triplet<Security, Long, Double>>();

		long date1 = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + 1, primaryExch));
		Map<Security, NavigableMap<Long, Attribute>> capMap = uSource.attrSource.getRange(factorLoadings.getSecurities(), PassThruCalculator.CAP, date1, asof);

		double tot = 0.0, totsq = 0.0, totNL = 0.0, totsqNL = 0.0;
		int cnt = 0;
		// /XXX the loop can be made slightly more efficient but it would be trickier weighting caps according to their time span
		for (Map.Entry<Security, NavigableMap<Long, Attribute>> e : capMap.entrySet()) {
			Security sec = e.getKey();
			NavigableMap<Long, Attribute> capSeries = e.getValue();

			int lag = 1;
			long millis = Exchange.prevClose(asof, primaryExch);
			for (; lag <= num_factor_days; millis = Exchange.prevClose(millis, primaryExch), lag++) {
				Map.Entry<Long, Attribute> cap = capSeries.floorEntry(millis);
				if (cap == null) {
					log.warning("Could not calculate size for " + sec.getSecId() + " on " + df.format(millis));
					continue;
				}
				double size = Math.log(cap.getValue().asDouble() / 1e6);
				sizeRawLoadings.add(new Triplet<Security, Long, Double>(sec, millis, size));

				double sizenl = Math.pow(size, 3);
				sizeNlRawLoadings.add(new Triplet<Security, Long, Double>(sec, millis, sizenl));

				tot += size;
				totsq += size * size;
				totNL += sizenl;
				totsqNL += sizenl * sizenl;
				cnt++;
			}
		}

		// center and normalize the raw loadings
		double sizeMean = tot / cnt;
		double sizeSigma = ASEMath.sigma(tot, totsq, cnt);
		for (Triplet<Security, Long, Double> e : sizeRawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= sizeMean;
			exp /= sizeSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, sizeFactorType, ts, exp);
		}
		// center and normalize the raw loadings
		double sizenlMean = totNL / cnt;
		double sizenlSigma = ASEMath.sigma(totNL, totsqNL, cnt);
		for (Triplet<Security, Long, Double> e : sizeNlRawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= sizenlMean;
			exp /= sizenlSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, sizenlFactorType, ts, exp);
		}

		ret.add(sizeFactorType);
		ret.add(sizenlFactorType);
		log.info("Size dist: " + sizeMean + " / " + sizeSigma);
		log.info("SizeNl dist: " + sizenlMean + " / " + sizenlSigma);
		return ret;
	}

	public Set<AttrType> calculateE2PFac(long asof) throws Exception {
		AttrType e2pFactorType = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "E2P");
		Set<AttrType> res = CollectionUtils.toSet(e2pFactorType);

		// calc once per day
		if (!needRecalc(asof)) {
			log.info("Not recalculating " + e2pFactorType);
			return res;
		}
		log.info("Calculating " + e2pFactorType);

		// XXX need to update this to get latest eps, not the 130 days ago version
		Vector<Triplet<Security, Long, Double>> rawLoadings = new Vector<Triplet<Security, Long, Double>>();
		long start_millis = Exchange.closeTime(Exchange.subtractTradingDays(asof, num_factor_days, primaryExch), primaryExch);
		Set<Security> secs = factorLoadings.getSecurities();
		Map<Security, Attribute> capMap = uSource.attrSource.getAttrAsOf(secs, PassThruCalculator.CAP, start_millis);
		Map<Security, Double> incMap = uSource.attrSource.getAverage(secs, FundamentalCalculator.INCOME, start_millis - Time.fromDays(365), start_millis);
		double tot = 0.0, totsq = 0.0;
		int cnt = 0;
		for (Security sec : secs) {
			Attribute capAttr = capMap.get(sec);
			if (capAttr == null) {
				log.warning("Could not look up Capitalization for " + sec + " as of " + df.format(start_millis));
				continue;
			}
			double cap = capAttr.asDouble() / 1e6;
			double inc = incMap.get(sec);
			double val = inc / cap;
			if (Double.isNaN(val)) {
				log.warning("Could not compute E2P factor for security " + sec.getSecId());
				continue;
			}

			rawLoadings.add(new Triplet<Security, Long, Double>(sec, start_millis, val));
			tot += val;
			totsq += val * val;
			cnt++;
		}

		// center and normalize the raw loadings
		double allMean = tot / cnt;
		double allSigma = ASEMath.sigma(tot, totsq, cnt);
		for (Triplet<Security, Long, Double> e : rawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= allMean;
			exp /= allSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, e2pFactorType, ts, exp);
		}
		log.info("E2p dist: " + allMean + " / " + allSigma);
		return res;
	}

	public Set<AttrType> calculateEE2PFac(long asof) throws Exception {
		AttrType ee2pType = EarningsEstimatesCalculator.getResName(0);
		AttrType ee2pFactorType = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + ee2pType.name);
		log.info("Calculating " + ee2pFactorType);

		Set<AttrType> res = CollectionUtils.toSet(ee2pFactorType);

		// calc once per day
		if (!needRecalc(asof)) {
			log.info("Not recalculating " + ee2pFactorType);
			return res;
		}

		Set<Security> secs = factorLoadings.getSecurities();
		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days, primaryExch));

		Vector<Triplet<Security, Long, Double>> rawLoadings = new Vector<Triplet<Security, Long, Double>>();
		double tot = 0.0, totsq = 0.0;
		int cnt = 0;

		Map<Security, NavigableSet<Long>> sec2calendarPeriods = uSource.estWidget.getCalendarPeriods(secs, PeriodCalculator.PERIOD_YEARS, asof);
		Map<Pair<Security, Long>, EstimateSeries<?>> secAndPeriod2Estimates = new HashMap<Pair<Security, Long>, EstimateSeries<?>>();

		for (long date = startdate; date < Time.today(asof); date = Exchange.nextTradingDay(date, primaryExch)) {
			long dateCloseTime = Exchange.closeTime(date, primaryExch);
			// Check which series we already have and which we need
			Map<Security, EstimateSeries<?>> estsMap = new HashMap<Security, EstimateSeries<?>>();
			Map<Security, Attribute> querySecs = new HashMap<Security, Attribute>();
			for (Security sec : secs) {
				NavigableSet<Long> periods = sec2calendarPeriods.get(sec);
				if (periods == null) {
					log.warning("Failed to find next calendar period for sec " + sec.getSecId() + " and date " + df.debugFormat(dateCloseTime));
					continue;
				}
				Long perioddate = periods.ceiling(dateCloseTime);
				if (perioddate == null) {
					log.warning("Failed to find next calendar period for sec " + sec.getSecId() + " and date " + df.debugFormat(dateCloseTime));
					continue;
				}

				EstimateSeries<?> series = secAndPeriod2Estimates.get(new Pair<Security, Long>(sec, perioddate));
				if (series != null)
					estsMap.put(sec, series);
				else
					querySecs.put(sec, new DateAttribute(new AttrType("CALENDAR_PERIOD", Type.D), sec, perioddate, perioddate, asof));
			}

			// get the next calendar period after date
			if (querySecs.size() > 0) {
				Map<Security, EstimateSeries<?>> subEstsMap = uSource.estWidget.getConsensus(SQLEstimateWidget.associateSecidsWithDates(querySecs),
						EstimatesCalculator.EEPSA_C, asof, startdate - Time.fromDays(365));
				// add the data in the cache
				for (Map.Entry<Security, EstimateSeries<?>> ent : subEstsMap.entrySet()) {
					Security sec = ent.getKey();
					EstimateSeries<?> series = ent.getValue();
					Attribute pd = querySecs.get(sec);
					long perioddate = pd.asDate();
					secAndPeriod2Estimates.put(new Pair<Security, Long>(sec, perioddate), series);
				}
				// reconcile the two maps
				estsMap.putAll(subEstsMap);
			}

			for (Map.Entry<Security, EstimateSeries<?>> ent : estsMap.entrySet()) {
				Security sec = ent.getKey();
				EstimateSeries<DistributionSummary> estSeries = (EstimateSeries<DistributionSummary>) ent.getValue();
				if (estSeries == null) {
					log.warning("No attribute " + EstimatesCalculator.EEPSA_C.name + " for " + sec.getSecId() + " at " + df.debugFormat(dateCloseTime));
					continue;
				}

				Estimate<DistributionSummary> est = estSeries.getFloorEstimate(dateCloseTime);
				if (est == null) {
					log.warning("No " + EstimatesCalculator.EEPSA_C.name + " estimate for " + sec.getSecId() + " at period=" + estSeries.perioddate + " and <="
							+ df.debugFormat(dateCloseTime));
					continue;
				}

				Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, est.orig);
				double price = p.first;
				if (Double.isNaN(price)) {
					log.warning("Could not find price for " + sec.getSecId() + " at " + df.debugFormat(est.orig));
					continue;
				}
				if (EstimatesCalculator.SPLIT_ADJ) {
					double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
					if (splitAdj != 1)
						log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
								+ df.debugFormat(asof) + "]");
					price /= splitAdj;
				}

				Double currencyAdj = uSource.exWidget.estimateToUSD(sec, est, EstimatesCalculator.CURRENCY_ADJ);
				if (currencyAdj == null)
					continue;

				double val = currencyAdj * est.value.mean / price;
				rawLoadings.add(new Triplet<Security, Long, Double>(sec, dateCloseTime, val));
				tot += val;
				totsq += val * val;
				cnt++;
			}
		}

		// center and normalize the raw loadings
		double allMean = tot / cnt;
		double allSigma = ASEMath.sigma(tot, totsq, cnt);
		for (Triplet<Security, Long, Double> e : rawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= allMean;
			exp /= allSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, ee2pFactorType, ts, exp);
		}
		log.info("Ee2p dist: " + allMean + " / " + allSigma);
		return res;
	}

	protected Pair<double[], Map<Security, double[]>> uniLogrels(Map<Security, BarTimeSeries> bars, Map<Security, NavigableMap<Long, Attribute>> capMap, long ts) {
		Map<Security, double[]> secLogrels = new HashMap<Security, double[]>();
		double[] uniLogrels = null;
		double totalCap = 0;
		for (Map.Entry<Security, BarTimeSeries> e : bars.entrySet()) {
			Security sec = e.getKey();
			BarTimeSeries bts = e.getValue();
			double[] sl = TimeSeriesUtil.o2cLogrels(bts);
			if (uniLogrels == null) {
				uniLogrels = new double[sl.length];
				Arrays.fill(uniLogrels, 0.0);
			}
			secLogrels.put(e.getKey(), sl);

			// get the cap
			NavigableMap<Long, Attribute> cts = capMap.get(sec);
			Entry<Long, Attribute> temp = cts.floorEntry(ts);
			if (temp == null) {
				log.warning("No cap entry for secid=" + sec.getSecId() + " millis=" + df.debugFormat(ts));
				continue;
			}
			Double cap = temp.getValue().asDouble() / 1e6;
			totalCap += cap;

			for (int ii = 0; ii < sl.length; ii++) {
				double ret = Math.exp(sl[ii]) - 1;
				if (Double.isNaN(ret))
					continue;
				uniLogrels[ii] += cap * ret;
			}
		}

		for (int ii = 0; ii < uniLogrels.length; ii++) {
			uniLogrels[ii] = Math.log(uniLogrels[ii] / totalCap + 1);
		}

		return new Pair<double[], Map<Security, double[]>>(uniLogrels, secLogrels);
	}

	public AttrType calculateIntradayBeta(long asof, int lookback) throws Exception {
		int num_factor_days = 1;

		AttrType factor = new CalcAttrType(FactorLoadings.MONITOR_FACTOR_PREFIX + "INTRADAY_BETA" + lookback);
		if (!needRecalc(asof)) {
			log.info("Not recalculating ase beta factors...");
			return factor;
		}
		log.info("Calculating " + factor);

		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + lookback - 1, primaryExch));
		Vector<Pair<double[], Map<Security, double[]>>> dailyLogrels = new Vector<Pair<double[], Map<Security, double[]>>>();
		Map<Security, NavigableMap<Long, Attribute>> cMap = uSource.attrSource
				.getRange(factorLoadings.getSecurities(), PassThruCalculator.CAP, startdate, asof);

		for (long date = startdate; date < Time.today(asof); date = Exchange.nextTradingDay(date, primaryExch)) {
			Map<Security, BarTimeSeries> bars = uSource.barSource.getTimeSeries(factorLoadings.getSecurities(), Exchange.openTime(date, primaryExch),
					Exchange.closeTime(date, primaryExch), primaryExch);
			dailyLogrels.add(uniLogrels(bars, cMap, Exchange.closeTime(date, primaryExch)));
		}

		int lag = 0;
		long millis = Exchange.prevClose(asof, primaryExch);

		// For each factor day
		for (; lag < num_factor_days; lag++, millis = Exchange.prevClose(millis, primaryExch)) {
			Map<Security, SimpleRegression> regressions = new HashMap<Security, SimpleRegression>();

			// accumulate regression return pairs over the past lookback days, for all securities
			int n = dailyLogrels.size();
			for (int ii = n - lag - 1; ii > dailyLogrels.size() - lag - 1 - lookback; ii--) {
				Pair<double[], Map<Security, double[]>> day = dailyLogrels.get(ii);
				double[] uniLogrels = day.first;

				for (Map.Entry<Security, double[]> e : day.second.entrySet()) {
					Security sec = e.getKey();
					double[] logrels = e.getValue();
					SimpleRegression regression = regressions.get(e.getKey());
					if (regression == null)
						regressions.put(sec, regression = new SimpleRegression());

					for (int xx = 0; xx < logrels.length; xx++) {
						if (!Double.isNaN(logrels[xx])) {
							regression.addData(uniLogrels[xx], logrels[xx]);
						}
					}
				}
			}

			// extract slope of regression
			for (Map.Entry<Security, SimpleRegression> e : regressions.entrySet()) {
				Security sec = e.getKey();
				double beta = e.getValue().getSlope();
				if (Double.isNaN(beta))
					continue;
				factorLoadings.setFactor(sec, factor, millis, beta);
			}
		}

		return factor;
	}

	public AttrType calculateBeta(long asof, int lookback) throws Exception {
		AttrType factor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "ASE_BETA" + lookback);
		if (!needRecalc(asof)) {
			log.info("Not recalculating ase beta factors...");
			return factor;
		}
		log.info("Calculating " + factor);

		long startdate = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + lookback, primaryExch));

		Map<Security, DailyBarTimeSeries> pMap = uSource.getDailyBarTimeSeries(factorLoadings.getSecurities(), startdate, asof, primaryExch);
		Map<Security, NavigableMap<Long, Attribute>> cMap = uSource.attrSource
				.getRange(factorLoadings.getSecurities(), PassThruCalculator.CAP, startdate, asof);

		double[] uniLogrels = new double[num_factor_days + lookback];
		double[] uniCap = new double[num_factor_days + lookback];
		Arrays.fill(uniLogrels, 0.0);
		Arrays.fill(uniCap, 0.0);

		for (Map.Entry<Security, DailyBarTimeSeries> e : pMap.entrySet()) {
			Security sec = e.getKey();
			DailyBarTimeSeries pts = e.getValue();
			NavigableMap<Long, Attribute> cts = cMap.get(sec);

			if (pts == null) {
				log.warning("No prices for security: " + sec.getSecId());
				continue;
			}
			if (cts == null) {
				log.warning("No caps for security: " + sec.getSecId());
				continue;
			}

			int lag = 1;
			long millis = Exchange.prevClose(asof, primaryExch);
			for (; lag < uniLogrels.length; millis = Exchange.prevClose(millis, primaryExch), lag++) {
				Double logrel = pts.getLogrel(lag, 1);
				Entry<Long, Attribute> temp = cts.floorEntry(millis);
				if (temp == null) {
					log.warning("No cap entry for secid=" + sec.getSecId() + " millis=" + df.debugFormat(millis));
					continue;
				}

				if (Double.isNaN(logrel)) {
					log.warning("Nan logrel for secid=" + sec.getSecId() + " and lag=" + lag);
					continue;
				}

				Double cap = temp.getValue().asDouble() / 1e6;
				uniCap[lag] += cap;
				uniLogrels[lag] += cap * (Math.exp(logrel) - 1);
			}
		}
		for (int i = 0; i < uniLogrels.length; i++) {
			uniLogrels[i] /= uniCap[i];
			uniLogrels[i] = Math.log(uniLogrels[i] + 1);
		}

		for (Map.Entry<Security, DailyBarTimeSeries> e : pMap.entrySet()) {
			Security sec = e.getKey();
			DailyBarTimeSeries pts = e.getValue();
			double[] logrels = pts.getLogrelArray(1, 0);
			ArrayUtils.reverse(logrels);
			// assert uniLogrels.length == logrels.length;

			int lag = 1;
			long millis = Exchange.prevClose(asof, primaryExch);
			for (; lag <= num_factor_days; millis = Exchange.prevClose(millis, primaryExch), lag++) {
				SimpleRegression lr = new SimpleRegression();
				for (int xx = lag; xx < lag + lookback; xx++) {
					if (Double.isNaN(logrels[xx]))
						continue;
					lr.addData(uniLogrels[xx], logrels[xx]);
				}
				double beta = lr.getSlope();

				if (Double.isNaN(beta)) {
					log.warning("Failed to regress out beta for " + sec.getSecId());
					continue;
				}
				factorLoadings.setFactor(sec, factor, millis, beta);
			}
		}

		/*
		 * // verification double uniBeta = 0; double uniWeight = 0; for (Security sec : pMap.keySet()) { Double beta = factorLoadings.getLoadingAsOf(sec,
		 * factor, asof); NavigableMap<Long, Attribute> cts = cMap.get(sec); if (Double.isNaN(beta) || cts == null) continue; Entry<Long, Attribute> temp =
		 * cts.floorEntry(asof); if (temp == null) continue; uniBeta += beta * temp.getValue().asDouble(); uniWeight += temp.getValue().asDouble(); }
		 * 
		 * log.info("Cap weighted beta is " + uniBeta / uniWeight);
		 */

		return factor;
	}

	public AttrType calculateShortInterestFactor(long asof) throws Exception {
		AttrType siFactor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + "SIFracNL");

		if (!needRecalc(asof)) {
			log.info("Not recalculating Short Interest Factor...");
			return siFactor;
		}

		log.info("Calculating Short Interest Factor");
		Vector<Triplet<Security, Long, Double>> rawLoadings = new Vector<Triplet<Security, Long, Double>>();
		long date1 = Time.today(Exchange.subtractTradingDays(asof, num_factor_days + 1, primaryExch));

		// redefine attributes so that they do not have a maxage
		Map<Security, NavigableMap<Long, Attribute>> floatMap = uSource.attrSource.getRange(factorLoadings.getSecurities(), PassThruCalculator.FLOAT, date1, asof);
		Map<Security, NavigableMap<Long, Attribute>> siMap = uSource.attrSource.getRange(factorLoadings.getSecurities(), ShortInterestCalculator.TOTAL_SHORT_INTEREST, date1, asof);

		double tot = 0.0, totsq = 0.0;
		int cnt = 0;
		for (Security sec : factorLoadings.getSecurities()) {
			NavigableMap<Long, Attribute> siSeries = siMap.get(sec);
			NavigableMap<Long, Attribute> floatSeries = floatMap.get(sec);

			if (siSeries.isEmpty()) {
				log.warning("No short interest data found for " + sec.getSecId() + ", fromDate=" + df.debugFormat(date1) + ", asof=" + df.debugFormat(asof));
				continue;
			}
			if (floatSeries.isEmpty()) {
				log.warning("No float data found for " + sec.getSecId() + ", fromDate=" + df.debugFormat(date1) + ", asof=" + df.debugFormat(asof));
				continue;
			}

			int lag = 1;
			long millis = Exchange.prevClose(asof, primaryExch);
			for (; lag <= num_factor_days; millis = Exchange.prevClose(millis, primaryExch), lag++) {
				Map.Entry<Long, Attribute> sie = siSeries.floorEntry(millis);
				if (sie == null) {
					log.warning("No short interest data for " + sec.getSecId() + " before " + df.debugFormat(millis));
					break;
				}

				Map.Entry<Long, Attribute> fe = floatSeries.floorEntry(millis);
				if (fe == null) {
					log.warning("No float data for " + sec.getSecId() + " before " + df.debugFormat(millis));
					break;
				}

				double si = sie.getValue().asDouble();
				double fl = fe.getValue().asDouble();
				double val = Math.pow(si / fl, 2.0);

				if (Double.isNaN(val) || Double.isInfinite(val)) {
					log.warning("Bad exposure computed for " + sec.getSecId() + ", millis=" + df.debugFormat(millis) + ", val=" + val + ", short interest="
							+ si + ", float=" + fl);
					continue;
				}

				rawLoadings.add(new Triplet<Security, Long, Double>(sec, millis, val));
				tot += val;
				totsq += val * val;
				cnt++;
			}
		}

		// center and normalize the raw loadings
		double allMean = tot / cnt;
		double allSigma = ASEMath.sigma(tot, totsq, cnt);
		log.info("SIFracNL dist: " + allMean + " / " + allSigma);
		for (Triplet<Security, Long, Double> e : rawLoadings) {
			Security sec = e.first;
			long ts = e.second;
			double exp = e.third;

			exp -= allMean;
			exp /= allSigma;
			exp = BoundingCalculator.boundDouble(exp, 0, 50000);
			factorLoadings.setFactor(sec, siFactor, ts, exp);
		}
		log.info("SIFracNL dist: " + allMean + " / " + allSigma);
		return siFactor;
	}
}
