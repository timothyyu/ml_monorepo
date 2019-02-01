package ase.calculator;

import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Exchange;
import ase.data.ReutersAnnDate;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.data.widget.SQLEstimateWidget.DateType;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class EarningsDateCalculator {
	private static final Logger log = LoggerFactory.getLogger(EarningsDateCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final TrendingCalculator trCalc;

	private static final long MIN_CALC_TIME = 0L;
	private long lastcalc = 0L;

	// speficy yahoo source but may want to make an enum
	// XXX backfilled data already have their born dates adjusted
	private static final DbAttrType YAHOO_EARN_DATE = new DbAttrType("FUTURE_ANN_DATE", "FUTURE_ANN_DATE", 0L, 0L, 10);

	public static final CalcAttrType earnFracAttrType = new CalcAttrType("earnDateFrac");
	public static final CalcAttrType recentEarningsAttrType = new CalcAttrType("recentEarnings");

	private static final int EARN_TRADING_DAYS = 5;

	public EarningsDateCalculator(UnifiedDataSource uSource, FactorCalculator fCalc) {
		this.uSource = uSource;
		this.trCalc = new TrendingCalculator(this.uSource, fCalc);
	}

	private long adjustEarningsDate(long earndate, Security sec) {
		if (!Exchange.isTradingDay(earndate, sec.primaryExchange)) {
			earndate = Exchange.nextTradingDay(earndate, sec.primaryExchange);
		}
		return earndate;
	}

	public void calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		if (asof < lastcalc + MIN_CALC_TIME) {
			log.info("Not Calculating Earnings.  Waiting until " + df.format(lastcalc + MIN_CALC_TIME));
			return;
		}
		log.info("Calculatring Earnings date attributes");

		Map<Security, Attribute> pastAttrs = uSource.attrSource.getAttrAsOf(secs, YAHOO_EARN_DATE, asof);
		Map<Security, Attribute> futureAttrs = uSource.attrSource.getUpcoming(secs, YAHOO_EARN_DATE, asof);

		for (Security sec : pastAttrs.keySet()) {
			Attribute attr = pastAttrs.get(sec);
			long earndate = adjustEarningsDate(attr.asDate(), sec);

			if (earndate >= Exchange.subtractTradingDays(asof, EARN_TRADING_DAYS, sec.primaryExchange)) {
				double val = 1.0 - ((double) Exchange.tradingTimeBetween(earndate, asof, sec.primaryExchange)) / Time.fromDays(EARN_TRADING_DAYS);
				cr.add(sec, earnFracAttrType, asof, val);
				if (earndate != Time.midnight(earndate)) {
					cr.add(sec, recentEarningsAttrType, earndate, 1.0);
				}
				else {
					log.warning("Earnings Date for " + sec.getSecId() + " at " + df.format(earndate) + " has no time!  Skipping for some reason...");
				}
			}
		}

		for (Security sec : futureAttrs.keySet()) {
			Attribute attr = futureAttrs.get(sec);
			long earndate = adjustEarningsDate(attr.asDate(), sec);

			if (earndate <= Exchange.addTradingDays(asof, EARN_TRADING_DAYS, sec.primaryExchange)) {
				double val = 1.0 - ((double) Exchange.tradingTimeBetween(asof, earndate, sec.primaryExchange)) / Time.fromDays(EARN_TRADING_DAYS);
				cr.add(sec, earnFracAttrType, asof, val);
			}
		}
		lastcalc = asof;

		// TrendingCalculator trCalc = new TrendingCalculator(uSource);
		BoundingCalculator sbndCalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);

		AttrType recentEarn_TC = trCalc.calculate(cr, recentEarningsAttrType, asof, TrendingCalculator.Mode.C2C);
		AttrType recentEarn_TC_BS = sbndCalc.calculate(cr, recentEarn_TC, 5.0);
		DecayCalculator.calculate(cr, recentEarn_TC_BS, asof, Time.fromDays(5), 3);

		AttrType recentEarn_TR = trCalc.calculate(cr, recentEarningsAttrType, asof, TrendingCalculator.Mode.RSDC2C);
		AttrType recentEarn_TR_BS = sbndCalc.calculate(cr, recentEarn_TR, 5.0);
		DecayCalculator.calculate(cr, recentEarn_TR_BS, asof, Time.fromDays(5), 3);
	}

	public void reutersCalculate(CalcResults cr, Set<Security> secs, long asof, Exchange.Type exch) throws Exception {
		if (asof < lastcalc + MIN_CALC_TIME) {
			log.info("Not Calculating Earnings.  Waiting until " + df.format(lastcalc + MIN_CALC_TIME));
			return;
		}
		log.info("Calculatring Earnings date attributes");

		Map<Security, Vector<ReutersAnnDate>> past = uSource.estWidget.getEstimatePeriods(secs, PeriodCalculator.PERIOD_QUARTERS, DateType.PAST, 1, asof);
		Map<Security, Vector<ReutersAnnDate>> future = uSource.estWidget.getEstimatePeriods(secs, PeriodCalculator.PERIOD_QUARTERS, DateType.FUTURE, 1, asof);

		for (Security sec : secs) {
			ReutersAnnDate pastAnn = (past.containsKey(sec) && past.get(sec).size() > 0) ? past.get(sec).get(0) : null;
			ReutersAnnDate futureAnn = (future.containsKey(sec) && future.get(sec).size() > 0) ? future.get(sec).get(0) : null;

			// Reuters updates their info at the end of the day. see if a "future ann" was actually announced in the morning, in which case it should become
			// "past"
			if (futureAnn != null && futureAnn.alreadyAnnounced(exch, asof)) {
				pastAnn = futureAnn;
				futureAnn = null;
			}

			// now do the work
			if (pastAnn != null) {
				long earndate = pastAnn.estimateAnnTs(exch);
				if (earndate >= Exchange.subtractTradingDays(asof, EARN_TRADING_DAYS, sec.primaryExchange)) {
					double val = 1.0 - ((double) Exchange.tradingTimeBetween(earndate, asof, sec.primaryExchange)) / Time.fromDays(EARN_TRADING_DAYS);
					cr.add(sec, earnFracAttrType, asof, val);
					if (earndate != Time.midnight(earndate)) {
						cr.add(sec, recentEarningsAttrType, earndate, 1.0);
					}
					else {
						log.warning("Earnings Date for " + sec.getSecId() + " at " + df.debugFormat(earndate) + " has no time!  Skipping for some reason...");
					}
				}
			}

			if (futureAnn != null) {
				long earndate = pastAnn.estimateAnnTs(exch);

				if (earndate <= Exchange.addTradingDays(asof, EARN_TRADING_DAYS, sec.primaryExchange)) {
					double val = 1.0 - ((double) Exchange.tradingTimeBetween(asof, earndate, sec.primaryExchange)) / Time.fromDays(EARN_TRADING_DAYS);
					cr.add(sec, earnFracAttrType, asof, val);
				}
			}
		}

		lastcalc = asof;

		// TrendingCalculator trCalc = new TrendingCalculator(uSource);
		AttrType recentEarn_T = trCalc.calculate(cr, recentEarningsAttrType, asof, TrendingCalculator.Mode.C2C);

		BoundingCalculator sbndCalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);
		AttrType recentEarn_T_BS = sbndCalc.calculate(cr, recentEarn_T, 5.0);
		DecayCalculator.calculate(cr, recentEarn_T_BS, asof, Time.fromDays(5), 3);

		recentEarn_T = trCalc.calculate(cr, recentEarningsAttrType, asof, TrendingCalculator.Mode.RSDC2C);
		recentEarn_T_BS = sbndCalc.calculate(cr, recentEarn_T, 5.0);
		DecayCalculator.calculate(cr, recentEarn_T_BS, asof, Time.fromDays(5), 3);
	}
}
