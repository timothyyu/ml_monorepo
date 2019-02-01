package ase.calculator;

import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.TreeMap;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.DistributionSummary;
import ase.data.Estimate;
import ase.data.EstimateSeries;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLEstimateWidget;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class EstDiffCalculator {
	private static final Logger log = LoggerFactory.getLogger(EstDiffCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final long max_diff_time;
	private final long max_decay_time;

	private final static double EPSILON = 0.000001;

	public EstDiffCalculator(UnifiedDataSource uSource, long max_diff_time, long max_decay_time) {
		this.uSource = uSource;
		this.max_diff_time = max_diff_time;
		this.max_decay_time = max_decay_time;
	}

	public AttrType calculateConcensus(CalcResults cr, DbAttrType attrType, Set<Security> secs, AttrType periodType, long asof) throws Exception {
		AttrType diffAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + diffAttr.name);

		// get next period dates
		Map<Security, Attribute> dates = cr.getResult(periodType);
		Map<Security, EstimateSeries<?>> estMap = uSource.estWidget.getConsensus(SQLEstimateWidget.associateSecidsWithDates(dates), attrType, asof, asof
				- max_diff_time - max_decay_time);
		log.info("Retrieved " + attrType.name + " on " + estMap.size() + "/" + secs.size() + " stocks");

		for (Security sec : estMap.keySet()) {
			EstimateSeries<DistributionSummary> estSeries = (EstimateSeries<DistributionSummary>) estMap.get(sec);
			if (estSeries == null) {
				log.warning("No past estimates for for " + sec + " " + attrType + " " + df.format(asof));
				continue;
			}
			Estimate<DistributionSummary> e2 = estSeries.getLaggedDailyEstimate(0);
			Estimate<DistributionSummary> e1 = estSeries.getLaggedDailyEstimate(1);
			if (e2 == null || e1 == null) {
				log.warning("Could not look up " + attrType + " for " + sec);
				continue;
			}

			if (e2.orig - e1.orig > max_diff_time)
				continue;

			if (e2.currency != e1.currency) {
				log.warning("Estimate series with different currencies for secid=" + sec.getSecId() + ", e1=" + e1.toString() + ", e2=" + e2.toString());
				continue;
			}
			Double currencyAdj = uSource.exWidget.estimateToUSD(sec, e2, EstimatesCalculator.CURRENCY_ADJ);
			if (currencyAdj == null)
				continue;
			double val = currencyAdj * (e2.value.mean - e1.value.mean);

			if (Math.abs(val) < EPSILON)
				continue;

			Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, e2.orig);
			double price = p.first;
			if (EstimatesCalculator.SPLIT_ADJ) {
				double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
				if (splitAdj != 1)
					log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
							+ df.debugFormat(asof) + "]");
				price /= splitAdj;
			}
			cr.add(sec, diffAttr, e2.orig, val / price);
		}
		return diffAttr;
	}

	public AttrType calculateTargetConcensus(CalcResults cr, DbAttrType attrType, Set<Security> secs, long asof) throws Exception {
		AttrType diffAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + diffAttr.name);

		Map<Security, EstimateSeries<?>> secMap = uSource.estWidget.getConsensus(SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), attrType,
				asof, asof - max_diff_time - max_decay_time);
		log.info("Retrieved " + attrType.name + " on " + secMap.size() + "/" + secs.size() + " stocks");

		for (Security sec : secMap.keySet()) {
			EstimateSeries<DistributionSummary> estSeries = (EstimateSeries<DistributionSummary>) secMap.get(sec);

			Estimate<DistributionSummary> e2 = estSeries.getLaggedDailyEstimate(0);
			Estimate<DistributionSummary> e1 = estSeries.getLaggedDailyEstimate(1);
			if (e2 == null || e1 == null) {
				if (e2 == null && e1 == null) {
					log.warning("Could not look up " + attrType + " for " + sec);
				}
				continue;
			}

			if (e2.orig - e1.orig > max_diff_time)
				continue;

			if (e2.currency != e1.currency) {
				log.warning("Estimate series with different currencies for secid=" + sec.getSecId() + ", e1=" + e1.toString() + ", e2=" + e2.toString());
				continue;
			}
			Double currencyAdj = uSource.exWidget.estimateToUSD(sec, e2, EstimatesCalculator.CURRENCY_ADJ);
			if (currencyAdj == null)
				continue;
			double val = currencyAdj * (e2.value.mean - e1.value.mean);

			if (Math.abs(val) < EPSILON)
				continue;

			Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, e2.orig);
			double price = p.first;
			if (EstimatesCalculator.SPLIT_ADJ) {
				double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
				if (splitAdj != 1)
					log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
							+ df.debugFormat(asof) + "]");
				price /= splitAdj;
			}

			cr.add(sec, diffAttr, e2.orig, val / price);
		}
		return diffAttr;
	}

	public AttrType calculateDetailed(CalcResults cr, DbAttrType attrType, Set<Security> secs, AttrType periodType, long asof) throws Exception {
		AttrType diffAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + diffAttr.name);

		Map<Security, Attribute> dates = cr.getResult(periodType);
		Map<Security, Map<Integer, EstimateSeries<Double>>> secMap = uSource.estWidget.getDetailed(SQLEstimateWidget.associateSecidsWithDates(dates), attrType,
				asof, asof - max_diff_time - max_decay_time, false);
		log.info("Retrieved " + attrType.name + " on " + secMap.size() + "/" + secs.size() + " stocks");

		int attrcnt = 0;
		for (Security sec : secMap.keySet()) {
			Map<Integer, EstimateSeries<Double>> brokerMap = secMap.get(sec);
			if (brokerMap == null) {
				log.warning("No brokers estimates on " + sec + " " + attrType + " " + df.format(asof));
				continue;
			}

			NavigableMap<Long, Vector<Double>> date2Diff = new TreeMap<Long, Vector<Double>>();
			long latestTs = 0L;
			for (Map.Entry<Integer, EstimateSeries<Double>> ent : brokerMap.entrySet()) {
				EstimateSeries<Double> estSeries = ent.getValue();
				Estimate<Double> e2 = estSeries.getLaggedDailyEstimate(0);
				Estimate<Double> e1 = estSeries.getLaggedDailyEstimate(1);

				if (e2 == null || e1 == null) {
					// log.warning("Could not find estimates on " + sec.getSecId() + " " + attrType + " " + df.format(asof) + " in " + estSeries.toString());
					continue;
				}
				if (e2.orig - e1.orig > max_diff_time)
					continue;

				if (e2.currency != e1.currency) {
					log.warning("Estimate series with different currencies for secid=" + sec.getSecId() + ", e1=" + e1.toString() + ", e2=" + e2.toString());
					continue;
				}
				Double currencyAdj = uSource.exWidget.estimateToUSD(sec, e2, EstimatesCalculator.CURRENCY_ADJ);
				if (currencyAdj == null)
					continue;
				double diff = currencyAdj * (e2.value - e1.value);

				if (Math.abs(diff) < EPSILON)
					continue;

				Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, e2.orig);
				double price = p.first;
				if (EstimatesCalculator.SPLIT_ADJ) {
					double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
					if (splitAdj != 1)
						log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
								+ df.debugFormat(asof) + "]");
					price /= splitAdj;
				}
				diff /= price;

				// need to check same day brokers and add up
				Vector<Double> diffs = date2Diff.get(Time.midnight(e2.orig));
				if (diffs == null) {
					diffs = new Vector<Double>();
					date2Diff.put(Time.midnight(e2.orig), diffs);
				}
				diffs.add(diff);
				if (e2.orig > latestTs)
					latestTs = e2.orig;
				// log.info("Sec: " + sec.getSecId() + " " + df.fformat(price) + " " + e1 + " " + e2);
			}
			Map.Entry<Long, Vector<Double>> latestRes = date2Diff.lastEntry();
			if (latestRes == null) {
				log.warning("No broker estimates found for " + sec.getSecId() + " / " + diffAttr.name + " at " + df.debugFormat(asof));
				continue;
			}

			cr.add(sec, diffAttr, latestTs, ASEMath.mean(latestRes.getValue()));
			attrcnt++;
		}
		log.info("Calculated " + attrcnt + " of " + diffAttr.name);
		return diffAttr;
	}

	public AttrType calculateTargetDetailed(CalcResults cr, DbAttrType attrType, Set<Security> secs, long asof) throws Exception {
		AttrType diffAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + diffAttr.name);

		Map<Security, Map<Integer, EstimateSeries<Double>>> secMap = uSource.estWidget.getDetailed(
				SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), attrType, asof, asof - max_diff_time - max_decay_time, false);
		log.info("Retrieved " + attrType.name + " on " + secMap.size() + "/" + secs.size() + " stocks");

		for (Security sec : secMap.keySet()) {
			Map<Integer, EstimateSeries<Double>> brokerSeries = secMap.get(sec);

			NavigableMap<Long, Vector<Double>> date2Diff = new TreeMap<Long, Vector<Double>>();
			long latestTs = 0L;
			for (EstimateSeries<Double> estSeries : brokerSeries.values()) {
				Estimate<Double> e2 = estSeries.getLaggedDailyEstimate(0);
				Estimate<Double> e1 = estSeries.getLaggedDailyEstimate(1);
				if (e2 == null || e1 == null) {
					// log.warning("Could not look up " + attrType + " from " + estSeries.toString());
					continue;
				}
				if (e2.orig - e1.orig > max_diff_time)
					continue;

				if (e2.currency != e1.currency) {
					log.warning("Estimate series with different currencies for secid=" + sec.getSecId() + ", e1=" + e1.toString() + ", e2=" + e2.toString());
					continue;
				}
				Double currencyAdj = uSource.exWidget.estimateToUSD(sec, e2, EstimatesCalculator.CURRENCY_ADJ);
				if (currencyAdj == null)
					continue;
				double diff = currencyAdj * (e2.value - e1.value);

				if (Math.abs(diff) < EPSILON)
					continue;

				Vector<Double> diffs = date2Diff.get(Time.midnight(e2.orig));
				if (diffs == null) {
					diffs = new Vector<Double>();
					date2Diff.put(Time.midnight(e2.orig), diffs);
				}
				diffs.add(diff);
				if (e2.orig > latestTs)
					latestTs = e2.orig;
			}
			Map.Entry<Long, Vector<Double>> latestRes = date2Diff.lastEntry();
			if (latestRes == null) {
				log.warning("No broker estimates found for " + sec.getSecId() + " / " + diffAttr.name + " at " + df.debugFormat(asof));
				continue;
			}
			Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, latestRes.getKey());
			double price = p.first;
			if (EstimatesCalculator.SPLIT_ADJ) {
				double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
				if (splitAdj != 1)
					log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
							+ df.debugFormat(asof) + "]");
				price /= splitAdj;
			}

			cr.add(sec, diffAttr, latestTs, ASEMath.mean(latestRes.getValue()) / price);
		}
		return diffAttr;
	}

	public static AttrType getResName(AttrType attr) {
		return new CalcAttrType(attr.name + "_Diff");
	}
}
