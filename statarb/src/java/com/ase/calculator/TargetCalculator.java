package ase.calculator;

import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Currency;
import ase.data.DbAttrType;
import ase.data.DistributionSummary;
import ase.data.Estimate;
import ase.data.EstimateSeries;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLAttributeWidget;
import ase.data.widget.SQLEstimateWidget;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class TargetCalculator {
	private static final Logger log = LoggerFactory.getLogger(TargetCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final long max_diff_time;

	public TargetCalculator(UnifiedDataSource uSource, long max_diff_time) {
		this.uSource = uSource;
		this.max_diff_time = max_diff_time;
	}

	public AttrType calculateConcensus(CalcResults cr, DbAttrType attrType, Set<Security> secs, long asof) throws Exception {
		AttrType tAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + tAttr);

		Map<Security, EstimateSeries<?>> estsMap = uSource.estWidget.getConsensus(SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), attrType,
				asof, asof - max_diff_time);
		log.info("Retrieved " + attrType.name + " on " + estsMap.size() + "/" + secs.size() + " stocks");

		for (Security sec : estsMap.keySet()) {
			EstimateSeries<DistributionSummary> estSeries = (EstimateSeries<DistributionSummary>) estsMap.get(sec);
			if (estSeries == null) {
				log.warning("No attribute " + attrType + " for " + sec);
				continue;
			}
			Estimate<DistributionSummary> dist = estSeries.getLaggedEstimate(0);

			Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, dist.orig);
			double price = p.first;
			if (EstimatesCalculator.SPLIT_ADJ) {
				double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
				if (splitAdj != 1)
					log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
							+ df.debugFormat(asof) + "]");
				price /= splitAdj;
			}

			Double currencyAdj = uSource.exWidget.estimateToUSD(sec, dist, EstimatesCalculator.CURRENCY_ADJ);
			if (currencyAdj == null)
				continue;

			double val = Math.log(currencyAdj * dist.value.mean / price);
			cr.add(sec, tAttr, dist.orig, val);
		}
		return tAttr;
	}

	public AttrType calculateDetailed(CalcResults cr, DbAttrType attrType, Set<Security> secs, long asof) throws Exception {
		AttrType tAttr = getResName(attrType);
		log.info("Calculating " + attrType.name + " into " + tAttr);

		Map<Security, Map<Integer, EstimateSeries<Double>>> estsMap = uSource.estWidget.getDetailed(
				SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), attrType, asof, asof - max_diff_time, false);
		log.info("Retrieved " + attrType.name + " on " + estsMap.size() + "/" + secs.size() + " stocks");

		for (Security sec : estsMap.keySet()) {
			Map<Integer, EstimateSeries<Double>> brokerSeries = estsMap.get(sec);
			long latest = 0L;
			double val = Double.NaN;
			for (EstimateSeries<Double> estSeries : brokerSeries.values()) {
				Estimate<Double> est = estSeries.getLatestEstimate();
				if (est == null)
					continue;

				Double currencyAdj = uSource.exWidget.estimateToUSD(sec, est, EstimatesCalculator.CURRENCY_ADJ);
				if (currencyAdj == null)
					continue;

				if (est.orig > latest) {
					val = currencyAdj * est.value;
					latest = est.orig;
				}
			}
			if (!Double.isNaN(val)) {
				Pair<Double, Long> p = uSource.dailySource.getLatestPriceAndTs(sec, latest);
				double price = p.first;
				if (EstimatesCalculator.SPLIT_ADJ) {
					double splitAdj = uSource.estWidget.getSplitAdjRate(sec, Time.today(p.second), asof);
					if (splitAdj != 1)
						log.info("Adjusting price of secid=" + sec.getSecId() + " with adj=" + splitAdj + " between (" + df.debugFormat(p.second) + ", "
								+ df.debugFormat(asof) + "]");
					price /= splitAdj;
				}

				double val2p = Math.log(val / price);
				cr.add(sec, tAttr, latest, val2p);
			}
		}
		return tAttr;
	}

	public static AttrType getResName(AttrType attr) {
		return new CalcAttrType(attr.name + "_2P");
	}
}
