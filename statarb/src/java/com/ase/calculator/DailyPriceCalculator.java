package ase.calculator;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import ase.calculator.CalcMaster.Mode;
import ase.calculator.filter.SecurityFilter;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.DailyBar;
import ase.timeseries.DailyBarTimeSeries;
import ase.timeseries.TimeSeries;
import ase.timeseries.TimeSeriesUtil;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;

public class DailyPriceCalculator extends Calculator {
	private final int TECH_4CAST_DAYSBACK = 3;
	private final int adv_days_back;
	private final Exchange.Type primaryExch;

	private final UnifiedDataSource uSource;

	public static final CalcAttrType HL = new CalcAttrType("hl");
	public static final CalcAttrType QHL = new CalcAttrType("qhl");
	public static final CalcAttrType O2C = new CalcAttrType("o2c");
	public static final CalcAttrType C2C = new CalcAttrType("c2c");
	public static final CalcAttrType C2O = new CalcAttrType("c2o");
	public static final CalcAttrType RV = new CalcAttrType("rvol");
	public static final CalcAttrType ADVP = new CalcAttrType("advp");
	public static final CalcAttrType HD_ADVP = new CalcAttrType("hd_advp");
	public static final CalcAttrType PRC = new CalcAttrType("prc");
	public static final CalcAttrType OPEN = new CalcAttrType("open");
	public static final CalcAttrType HIGH = new CalcAttrType("high");
	public static final CalcAttrType LOW = new CalcAttrType("low");
	public static final CalcAttrType QHIGH = new CalcAttrType("qhigh");
	public static final CalcAttrType QLOW = new CalcAttrType("qlow");
	public static final CalcAttrType SPLIT = new CalcAttrType("split");
	public static final CalcAttrType DIV = new CalcAttrType("div");
	public static final CalcAttrType CASHEQ = new CalcAttrType("casheq");

	public DailyPriceCalculator(UnifiedDataSource uSource, int adv_days_back, Exchange.Type primaryExch) {
		super(true);
		this.uSource = uSource;
		this.adv_days_back = adv_days_back;
		this.primaryExch = primaryExch;
	}

	public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof, CalcMaster.Mode mode) throws Exception {
		boolean recalcLags = needToCalc(asof);
		if (recalcLags) {
			calculateOnce(cr, secs, asof);
			applyCalculations(cr, secs, asof, 0, TECH_4CAST_DAYSBACK+1);
		}
		if ((mode == Mode.SIM) && asof == Exchange.closeTime(asof, primaryExch)) {
			log.warning("Calculating day C without using intrabars. Asof=" + df.debugFormat(asof));
			calculateRepeatedly(cr, secs, asof, false);
			applyCalculations(cr, secs, asof, -1, 0);
		}
		else if (asof > Exchange.openTime(asof, primaryExch)) {
			calculateRepeatedly(cr, secs, asof, true);
			applyCalculations(cr, secs, asof, -1, 0);
		}
		return null;
	}

	protected Set<AttrType> calculateOnce(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		log.info("Calculating daily prices once...");
		long startdate = Time.today(Exchange.subtractTradingDays(asof, adv_days_back, primaryExch));
		long technicalsStartDate = Time.today((Exchange.subtractTradingDays(asof, TECH_4CAST_DAYSBACK, primaryExch)));
		long today = Time.today(asof);

		// range [asof-adv_days_back,asof-1]
		Map<Security, DailyBarTimeSeries> dailyBarMap = uSource.dailySource.getTimeSeries(secs, startdate, Exchange.prevTradingDay(asof, primaryExch),
				primaryExch);
		Map<Security, TimeSeries<Pair<Double, Double>>> qhlMap = uSource.barSource.getQuantileHL(secs, technicalsStartDate,
				Exchange.prevTradingDay(asof, primaryExch), Exchange.REGULAR_TRADING_MILLIS, primaryExch);
		// XXX only need to get the capMap once per day
		Map<Security, Triplet<Double, Double, Double>> capAdjMap = uSource.dailySource.pw.getAdjustments(secs, today);
		Map<Security, Attribute> pforecastable = cr.getResult(SecurityFilter.PRICE_FORECASTABLE);

		for (Security sec : secs) {
			DailyBarTimeSeries bts = dailyBarMap.get(sec);
			if (bts == null) {
				log.severe("Could not find daily prices for " + sec + " on " + df.format(asof));
				continue;
			}

			// XXX should only put in cap adjustments if they are non-trivial
			cr.add(sec, DIV, today, capAdjMap.get(sec).first);
			cr.add(sec, CASHEQ, today, capAdjMap.get(sec).second);
			cr.add(sec, SPLIT, today, capAdjMap.get(sec).third);

			double advp = bts.getAverageVolPrice(adv_days_back, 0);
			cr.add(sec, ADVP, today, advp);

			for (int daylag = 0; daylag < TECH_4CAST_DAYSBACK + 1; daylag++) {
				DailyBar bar2 = bts.getLag(daylag);
				DailyBar bar1 = bts.getLag(daylag + 1);

				if (bar1 == null || bar2 == null) {
					log.warning("No bars found for " + sec.getSecId() + " on " + df.debugFormat(asof));
					continue;
				}
				// should perhaps make relative vol based off of vwap instead of close
				cr.add(sec, lattr(RV, daylag), today, Math.log(bar2.notional() / advp));
				cr.add(sec, lattr(PRC, daylag), today, bar2.close);

				if (pforecastable.containsKey(sec)) {
					cr.add(sec, lattr(HL, daylag), today, Math.log(bar2.close / Math.sqrt(bar2.high * bar2.low)));
					cr.add(sec, lattr(O2C, daylag), today, TimeSeriesUtil.o2cLogrel(bar2));
					cr.add(sec, lattr(C2C, daylag), today, TimeSeriesUtil.c2cLogrel(bar2, bar1));
					cr.add(sec, lattr(C2O, daylag), today, TimeSeriesUtil.c2oLogrel(bar2, bar1));

					// /XXX this needs to be eventually moved in the main loop and throw a warning if it is null
					Pair<Double, Double> qhl = qhlMap.get(sec).getLag(daylag);
					if (qhl != null && qhl.first != null && qhl.second != null) {
						cr.add(sec, lattr(QHL, daylag), today, Math.log(bar2.close / Math.sqrt(qhl.first * qhl.second)));
					}
				}
			}
		}
		return null;
	}

	protected Set<AttrType> calculateRepeatedly(CalcResults cr, Set<Security> secs, long asof, boolean useIntraBars) throws Exception {
		log.info("Calculating daily price current...");
		long startdate = Time.today(Exchange.subtractTradingDays(asof, adv_days_back, primaryExch));

		// range [asof-adv_days_back,asof]]
		Map<Security, BarTimeSeries> halfDayBarMap = null;
		if (useIntraBars) {
			halfDayBarMap = uSource.barSource.getHalfDayTimeSeries(secs, startdate, Time.today(asof), Math.max(0, asof - Exchange.openTime(asof, primaryExch)),
					primaryExch);
		}
		else {
			assert asof == Exchange.closeTime(asof, primaryExch);
			halfDayBarMap = new HashMap<Security, BarTimeSeries>();
			for (Map.Entry<Security, DailyBarTimeSeries> e : uSource.dailySource.getTimeSeries(secs, startdate, Time.today(asof), primaryExch).entrySet())
				halfDayBarMap.put(e.getKey(), e.getValue());
		}

		// range [asof-1 (or -2),asof]
		Map<Security, DailyBarTimeSeries> twoDayBarMap = uSource.getDailyBarTimeSeries(secs, Time.today(Exchange.subtractTradingDays(asof, 2, primaryExch)),
				asof, primaryExch);
		// day=asof
		Map<Security, Pair<Double, Double>> qhlMap = uSource.barSource.getQuantileHL(secs, Time.today(asof), Math.max(0, asof - Exchange.openTime(asof, primaryExch)),
				primaryExch);
		Map<Security, Attribute> pforecastable = cr.getResult(SecurityFilter.PRICE_FORECASTABLE);

		for (Security sec : secs) {
			BarTimeSeries bts = halfDayBarMap.get(sec);
			DailyBarTimeSeries dts = twoDayBarMap.get(sec);
			if (bts == null || dts == null) {
				// /XXX Based on our conventions, I do not think that this can ever happen
				log.severe("Could not find prices for " + sec + " on " + df.format(asof));
				continue;
			}

			// /XXX if no bars are found for security, this will probably be 0 or NaN
			double advp = bts.getAverageVolPrice(adv_days_back, 1);
			if (!(advp > 0)) {
				log.warning("Bad " + HD_ADVP.name + " for security " + sec.getSecId() + " and asof=" + df.debugFormat(asof));
			}
			cr.add(sec, HD_ADVP, asof, advp);

			int daylag = -1;
			DailyBar bar2 = dts.getLag(0);
			DailyBar bar1 = dts.getLag(1);

			if (bar1 == null || bar2 == null || bts.getLag(0) == null) {
				log.warning("No bars found for " + sec.getSecId() + " on " + asof);
				continue;
			}

			// should perhaps make relative vol based off of vwap instead of close
			// /XXX Divide apples with apples. Use last bar of bts
			cr.add(sec, lattr(RV, daylag), asof, Math.log(bts.getLag(0).notional() / advp));
			cr.add(sec, lattr(PRC, daylag), asof, bar2.close);
			cr.add(sec, OPEN, asof, bar2.open);
			cr.add(sec, HIGH, asof, bar2.high);
			cr.add(sec, LOW, asof, bar2.low);

			if (pforecastable.containsKey(sec)) {
				if (bar2.isValid()) {
					cr.add(sec, lattr(HL, daylag), asof, Math.log(bar2.close / Math.sqrt(bar2.high * bar2.low)));
					cr.add(sec, lattr(O2C, daylag), asof, TimeSeriesUtil.o2cLogrel(bar2));
					cr.add(sec, lattr(C2C, daylag), asof, TimeSeriesUtil.c2cLogrel(bar2, bar1));
					cr.add(sec, lattr(C2O, daylag), asof, TimeSeriesUtil.c2oLogrel(bar2, bar1));
				}
				else {
					log.severe("Not calculating technicals on suspicious bar: " + bar2);
				}
				// /XXX this needs to be eventually moved in the main loop and throw a warning if it is null
				Pair<Double, Double> qhl = qhlMap.get(sec);
				if (qhl != null && qhl.first != null && qhl.second != null) {
					cr.add(sec, lattr(QHL, daylag), asof, Math.log(bar2.close / Math.sqrt(qhl.first * qhl.second)));
					cr.add(sec, QHIGH, asof, qhl.first);
					cr.add(sec, QLOW, asof, qhl.second);
				}
			}
		}
		return null;
	}

	protected void applyCalculations(CalcResults cr, Set<Security> secs, long asof, int fromLag, int toLag) throws Exception {
		BoundingCalculator sbcalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);
		TimeCalculator todCalc = new TimeCalculator(primaryExch, TimeCalculator.Mode.REG);
		TimeCalculator invTodCalc = new TimeCalculator(primaryExch, TimeCalculator.Mode.INV);
		TimeCalculator revTodCalc = new TimeCalculator(primaryExch, TimeCalculator.Mode.REV);
		
		for (int daylag = fromLag; daylag < toLag; daylag++) {
			AttrType bto2c = RescaleCalculator.calculate(cr, lattr(O2C, daylag), BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);
			AttrType btc2c = RescaleCalculator.calculate(cr, lattr(C2C, daylag), BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);
			AttrType btc2o = RescaleCalculator.calculate(cr, lattr(C2O, daylag), BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);

			AttrType o2crvol = RescaleCalculator.calculate(cr, lattr(O2C, daylag), lattr(RV, daylag), RescaleCalculator.Mode.TANH);
			AttrType o2crvolbeta = RescaleCalculator.calculate(cr, o2crvol, BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);

			AttrType o2c_va = RescaleCalculator.calculate(cr, lattr(O2C, daylag), lattr(RV, daylag), RescaleCalculator.Mode.TANH);
			AttrType o2c_va_ba = RescaleCalculator.calculate(cr, o2c_va, BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);
			AttrType o2c_va_ba_bs = sbcalc.calculate(cr, o2c_va_ba, 5.0);
			AttrType o2c_va_ba_bs_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, o2c_va_ba_bs);

			AttrType o2c_ba = RescaleCalculator.calculate(cr, lattr(O2C, daylag), BarraCalculator.B_BETA, RescaleCalculator.Mode.INV);
			AttrType o2c_ba_va = RescaleCalculator.calculate(cr, o2c_ba, lattr(RV, daylag), RescaleCalculator.Mode.TANH);
			AttrType o2c_ba_va_bs = sbcalc.calculate(cr, o2c_ba_va, 5.0);
			AttrType o2c_ba_va_bs_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, o2c_ba_va_bs);

			// sigma bounding
			sbcalc.calculate(cr, o2crvolbeta, 5.0);
			AttrType bhl_bs = sbcalc.calculate(cr, lattr(HL, daylag), 5.0);
			AttrType bqhl_bs = sbcalc.calculate(cr, lattr(QHL, daylag), 5.0);
			AttrType bdo2c_bs = sbcalc.calculate(cr, bto2c, 5.0);
			AttrType bdc2c_bs = sbcalc.calculate(cr, btc2c, 5.0);
			AttrType bdc2o_bs = sbcalc.calculate(cr, btc2o, 5.0);

			AttrType bhl_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, bhl_bs);
			AttrType bhl_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, bhl_bs);

			AttrType bqhl_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, bqhl_bs);
			AttrType bqhl_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, bqhl_bs);

			AttrType bdo2c_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, bdo2c_bs);
			AttrType bdc2c_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, bdc2c_bs);
			AttrType bdc2o_bs_sa = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, bdc2o_bs);

			AttrType bdo2c_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, bdo2c_bs);
			AttrType bdc2c_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, bdc2c_bs);
			AttrType bdc2o_bs_ba = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, bdc2o_bs);
			AttrType bdc2o_bs_ba_ta = revTodCalc.calculate(cr, bdc2o_bs_ba, asof);
			
			if (daylag == -1) {
			    AttrType bhl_bs_sa_ta = todCalc.calculate(cr, bhl_bs_sa, asof);
			    AttrType bhl_bs_ba_ta = todCalc.calculate(cr, bhl_bs_ba, asof);
			    
			    AttrType bqhl_bs_sa_ta = todCalc.calculate(cr, bqhl_bs_sa, asof);
			    AttrType bqhl_bs_ba_ta = todCalc.calculate(cr, bqhl_bs_ba, asof);
			    
			    AttrType bdo2c_bs_sa_ta = todCalc.calculate(cr, bdo2c_bs_sa, asof);
			    AttrType bdo2c_bs_ba_ta = todCalc.calculate(cr, bdo2c_bs_ba, asof);
			}
			else if (daylag > 1) {
                AttrType bhl_bs_sa_tai = invTodCalc.calculate(cr, bhl_bs_sa, asof);
                AttrType bhl_bs_ba_tai = invTodCalc.calculate(cr, bhl_bs_ba, asof);
                
                AttrType bqhl_bs_sa_tai = invTodCalc.calculate(cr, bqhl_bs_sa, asof);
                AttrType bqhl_bs_ba_tai = invTodCalc.calculate(cr, bqhl_bs_ba, asof);
                
                AttrType bdo2c_bs_sa_tai = invTodCalc.calculate(cr, bdo2c_bs_sa, asof);
                AttrType bdo2c_bs_ba_tai = invTodCalc.calculate(cr, bdo2c_bs_ba, asof);			    
			}
		}
	}

	public static AttrType lattr(CalcAttrType attr, int lag) {
		if (lag == -1) {
			return new CalcAttrType(attr.name + "C");
		}
		return new CalcAttrType(attr.name + lag);
	}
}
