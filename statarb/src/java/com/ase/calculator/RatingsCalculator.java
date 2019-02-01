package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.TreeMap;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Estimate;
import ase.data.EstimateSeries;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLEstimateWidget;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class RatingsCalculator {
	private static final Logger log = LoggerFactory.getLogger(RatingsCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final Exchange.Type primaryExch;

	private static final long MAX_DIFF_TIME = Time.fromDays(240);
	private static final long MAX_DECAY_TIME = Time.fromDays(45);
	private static final double EPSILON = .000001;

	//XXX *Very* wide range of delays for backfilled data.
	public static final DbAttrType REC_C = new DbAttrType("RECOMMENDATION_CE", "RECOMMENDATION_CE", 0L, Time.fromDays(1));
	public static final DbAttrType REC_D = new DbAttrType("RECOMMENDATION_DE", "RECOMMENDATION_DE", 0L, Time.fromDays(1));

	public RatingsCalculator(UnifiedDataSource uSource, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.primaryExch = primaryExch;
	}

	private Pair<Estimate<Double>, Estimate<Double>> getEstimates(EstimateSeries<Double> series) {
		Estimate<Double> e2 = null;
		Estimate<Double> e1 = null;
		int ii = 0;
		for (ii = 0; ii < series.size(); ii++) {
			Estimate<Double> e = series.getLaggedDailyEstimate(ii);
			if (e != null && e.value != 6) {
				e2 = e;
				break;
			}
		}
		for (int jj = ii + 1; jj < series.size(); jj++) {
			Estimate<Double> e = series.getLaggedDailyEstimate(jj);
			if (e != null && e.value != 6) {
				e1 = e;
				break;
			}
		}
		return new Pair<Estimate<Double>, Estimate<Double>>(e1, e2);
	}

	public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		log.info("Calculating Ratings...");
		Set<AttrType> res = new HashSet<AttrType>();
		Map<Security, EstimateSeries<?>> estsMap = uSource.estWidget.getConsensus(SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), REC_C, asof, asof
				- MAX_DIFF_TIME - MAX_DECAY_TIME);

		int attrcnt = 0;
		AttrType rdiffCAttr = new CalcAttrType("ratDiffC");
		for (Security sec : estsMap.keySet()) {
			EstimateSeries<Double> estSeries = (EstimateSeries<Double>) estsMap.get(sec);
			Pair<Estimate<Double>, Estimate<Double>> p = getEstimates(estSeries);
			Estimate<Double> e2 = p.second;
			Estimate<Double> e1 = p.first;
			if (e1 == null || e2 == null)
				continue;
			if (e2.orig - e1.orig > MAX_DIFF_TIME)
				continue;
			double val = -1 * (e2.value - e1.value); // lower rating is an upgrade
			if (Math.abs(val) < EPSILON)
				continue;

			cr.add(sec, rdiffCAttr, e2.orig, val);
			attrcnt++;
		}
		log.info("Calculated " + attrcnt + " of " + rdiffCAttr.name);

		//sigma bounding
	    BoundingCalculator sbndCalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);
		AttrType rdiff_bs = sbndCalc.calculate(cr, rdiffCAttr, 5.0);
        AttrType rdiff_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, rdiff_bs);
        AttrType rdiff_bs_ba_d5 = DecayCalculator.calculate(cr, rdiff_bs_ba, asof, Time.fromDays(5), 3);
        AttrType rdiff_bs_ba_d10 = DecayCalculator.calculate(cr, rdiff_bs_ba, asof, Time.fromDays(10), 3);
        AttrType rdiff_bs_d5 = DecayCalculator.calculate(cr, rdiff_bs, asof, Time.fromDays(5), 3);
        AttrType rdiff_bs_d10 = DecayCalculator.calculate(cr, rdiff_bs, asof, Time.fromDays(10), 3);
		
		AttrType rdiffDAttr = new CalcAttrType("ratDiffD");
		// /XXX search back for 3 years instead of asof- MAX_DIFF_TIME
		Map<Security, Map<Integer, EstimateSeries<Double>>> ratMap = uSource.estWidget.getDetailed(SQLEstimateWidget.associateSecidsWithDates(secs, Long.MIN_VALUE), REC_D, asof, asof - Time.fromDays(1095), false);

		attrcnt = 0;
		for (Map.Entry<Security, Map<Integer, EstimateSeries<Double>>> ent : ratMap.entrySet()) {
			Security sec = ent.getKey();
			double diff = 0.0;
			NavigableMap<Long, Vector<Double>> date2Diff = new TreeMap<Long, Vector<Double>>();
			for (EstimateSeries<Double> estSeries : ent.getValue().values()) {
				Pair<Estimate<Double>, Estimate<Double>> p = getEstimates(estSeries);
				Estimate<Double> e2 = p.second;
				Estimate<Double> e1 = p.first;
				if (e1 == null || e2 == null)
					continue;
				// /XXX note here that we diff against the most recent confirmation
				if (e2.orig - e1.mostRecentConfirmation() > MAX_DIFF_TIME)
					continue;

				double val = -1 * (e2.value - e1.value); // lower rating is an upgrade
				if (Math.abs(val) < EPSILON)
					continue;

				// if ( Exchange.affectsSameDay(e1.orig, e2.orig, primaryExch)) {
				// diff += val;
				// }
				// else {
				diff = val;
				// }
				Vector<Double> diffs = date2Diff.get(e2.orig);
				if (diffs == null) {
					diffs = new Vector<Double>();
					date2Diff.put(e2.orig, diffs);
				}
				diffs.add(diff);
			}
			Map.Entry<Long, Vector<Double>> latestRes = date2Diff.lastEntry();
			if (latestRes == null) {
				log.warning("No broker estimates found for " + sec.getSecId() + " / " + rdiffDAttr.name + " at " + df.debugFormat(asof));
				continue;
			}
			attrcnt++;
			cr.add(sec, rdiffDAttr, latestRes.getKey(), ASEMath.mean(latestRes.getValue()));
		}
		log.info("Calculated " + attrcnt + " of " + rdiffDAttr.name);

		//sigma boundings
		AttrType rdiffD_bs = sbndCalc.calculate(cr, rdiffDAttr, 12500);
        AttrType rdiffD_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, rdiffD_bs);
        AttrType rdiffD_bs_ba_d5 = DecayCalculator.calculate(cr, rdiffD_bs_ba, asof, Time.fromDays(5), 3);
        AttrType rdiffD_bs_ba_d10 = DecayCalculator.calculate(cr, rdiffD_bs_ba, asof, Time.fromDays(10), 3);
        AttrType rdiffD_bs_d5 = DecayCalculator.calculate(cr, rdiffD_bs, asof, Time.fromDays(5), 3);
        AttrType rdiffD_bs_d10 = DecayCalculator.calculate(cr, rdiffD_bs, asof, Time.fromDays(10), 3);
		
		return res;
	}
}
