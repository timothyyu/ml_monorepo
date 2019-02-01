package ase.calculator;

import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.calculator.filter.SecurityFilter;
import ase.data.AttrType;
import ase.data.BarSource;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.BarV2;
import ase.timeseries.TimeSeriesUtil;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class IntradayBarCalculator extends Calculator {
	protected static final Logger log = LoggerFactory.getLogger(Calculator.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	private final Exchange.Type primaryExch;
	private final UnifiedDataSource uSource;

	public static final CalcAttrType SPREAD = new CalcAttrType("SPREAD");
	public static final CalcAttrType BA_SIZE = new CalcAttrType("baSize");
	public static final CalcAttrType BA_SIZE_SQ = new CalcAttrType("baSizeSQ");
	public static final CalcAttrType BA_DOLLARS = new CalcAttrType("baDollars");
	public static final CalcAttrType EFF_BA_DOLLARS = new CalcAttrType("baDollarsEff");

	public static CalcAttrType getAttr(CalcAttrType attr, String modifier) {
		assert attr.equals(SPREAD) || attr.equals(BA_SIZE) || attr.equals(BA_DOLLARS) || attr.equals(EFF_BA_DOLLARS) || attr.equals(BA_SIZE_SQ);
		return new CalcAttrType(attr.name + "_" + modifier, attr.datatype);
	}

	public IntradayBarCalculator(UnifiedDataSource uSource, Exchange.Type primaryExch) {
		super(true);
		this.uSource = uSource;
		this.primaryExch = primaryExch;
	}

	public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		boolean recalcLags = needToCalc(asof);
		Set<Security> pforecastable = cr.getResult(SecurityFilter.PRICE_FORECASTABLE).keySet();

		if (recalcLags)
			calculateOnce(cr, secs, asof, pforecastable);

		// a bit wild in the morning. wait until 4 bars pass
		if (asof < Exchange.openTime(asof, primaryExch) + BarSource.BAR_SPAN * 2) {
			log.info("Not running intradaybar calculations until past open...");
			return null;
		}

		long todayOpenMillis = Exchange.openTime(asof, primaryExch);
		Map<Security, BarTimeSeries> todayBarMap = uSource.barSource.getTimeSeries(secs, todayOpenMillis, asof, primaryExch);

		long startC = asof - BarSource.BAR_SPAN + 1;
		long start1 = asof - Time.fromMinutes(60) + 1;
		boolean doC = (startC >= Exchange.openTime(asof, primaryExch)) ? true : false;
		boolean do1 = (start1 >= Exchange.openTime(asof, primaryExch)) ? true : false;
		boolean doS = doC;

		for (Security sec : secs) {
			BarTimeSeries tts = todayBarMap.get(sec);
			if (tts == null) {
				// Based on our conventions, I do not think that this can ever happen
				log.severe("Could not find today bars for " + sec + " on " + df.format(asof));
				continue;
			}

			// Get 3 types of bars
			if (doC) {
				Bar bC = TimeSeriesUtil.aggregateBars(tts, startC, asof);
				processBar(sec, bC, "C", cr, asof, pforecastable);
			}
			if (do1) {
				Bar b1 = TimeSeriesUtil.aggregateBars(tts, start1, asof);
				processBar(sec, b1, "1", cr, asof, pforecastable);
			}
			if (doS) {
				Bar bS = TimeSeriesUtil.aggregateBars(tts, todayOpenMillis, asof);
				processBar(sec, bS, "S", cr, asof, pforecastable);
			}
		}

		TimeCalculator todCalc = new TimeCalculator(primaryExch, TimeCalculator.Mode.REG);
		if (doC) {
			GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_SIZE, "C"));
			AttrType bad_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_DOLLARS, "C"));
			AttrType badf_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(EFF_BA_DOLLARS, "C"));
			todCalc.calculate(cr, bad_ma, asof);
			todCalc.calculate(cr, badf_ma, asof);
		}
		if (do1) {
			GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_SIZE, "1"));
			todCalc.calculate(cr, getAttr(BA_DOLLARS, "1"), asof);
            todCalc.calculate(cr, getAttr(EFF_BA_DOLLARS, "1"), asof);
		}
		if (doS) {
			GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_SIZE, "S"));
			AttrType bad_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_DOLLARS, "S"));
			AttrType badf_ma = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(EFF_BA_DOLLARS, "S"));
			todCalc.calculate(cr, bad_ma, asof);
            todCalc.calculate(cr, badf_ma, asof);
		}
		return null;
	}

	protected Set<AttrType> calculateOnce(CalcResults cr, Set<Security> secs, long asof, Set<Security> pforecastable) throws Exception {
		long todayOpenMillis = Exchange.openTime(asof, primaryExch);
		long yesterdayOpenMillis = Exchange.subtractTradingDays(todayOpenMillis, 1, primaryExch);
		long yesterdayCloseMillis = Exchange.closeTime(yesterdayOpenMillis, primaryExch);

		Map<Security, BarTimeSeries> yesterdayBarMap = uSource.barSource.getTimeSeries(secs, yesterdayOpenMillis, yesterdayCloseMillis, primaryExch);
		for (Security sec : secs) {
			BarTimeSeries yts = yesterdayBarMap.get(sec);
			if (yts == null) {
				// Based on our conventions, I do not think that this can ever happen
				log.severe("Could not yesterday for " + sec + " on " + df.format(asof));
				continue;
			}

			Bar bSY = TimeSeriesUtil.aggregateBars(yts, yesterdayOpenMillis, yesterdayCloseMillis);
			processBar(sec, bSY, "Y", cr, asof, pforecastable);
		}
		GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_SIZE, "Y"));
		GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(BA_DOLLARS, "Y"));
		GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, getAttr(EFF_BA_DOLLARS, "Y"));
		return null;
	}

	private boolean processBar(Security sec, Bar protoBar, String modifier, CalcResults cr, long asof, Set<Security> pforecastable) throws Exception {
		if (protoBar == null) {
			log.warning("No bar found for " + sec.getSecId() + ". modifier=" + modifier + " asof=" + df.debugFormat(asof));
			return false;
		}

		if (protoBar.version < 2) {
			log.warning("Bar is not V2 for " + sec.getSecId() + ". modifier=" + modifier + " asof=" + df.debugFormat(asof));
			return false;
		}

		BarV2 bar = (BarV2) protoBar;
		if (!(bar.meanSpread > 0)) {
			log.warning("Zero mean spread for secid=" + bar.sec.getSecId() + " asof=" + df.debugFormat(bar.close_ts));
			return false;
		}

		cr.add(sec, getAttr(SPREAD, modifier), bar.close_ts, bar.meanSpread);
		if (pforecastable.contains(sec)) {
		    double basz = ((bar.meanAskSize - bar.meanBidSize) / (bar.meanAskSize + bar.meanBidSize) / bar.meanSpread) / 1.0e4;
		    double basz2 = ((bar.meanAskSize - bar.meanBidSize) / (bar.meanAskSize + bar.meanBidSize) / Math.sqrt(bar.meanSpread)) / 1.0e4;
			cr.add(sec, getAttr(BA_SIZE, modifier), bar.close_ts, basz);
			cr.add(sec, getAttr(BA_SIZE_SQ, modifier), bar.close_ts, basz2);
			double tradeDollars = bar.askTradeAmount + bar.midTradeAmount + bar.bidTradeAmount;
			cr.add(sec, getAttr(BA_DOLLARS, modifier), bar.close_ts, (bar.askTradeAmount - bar.bidTradeAmount) / tradeDollars);
			cr.add(sec, getAttr(EFF_BA_DOLLARS, modifier), bar.close_ts, (bar.effectiveAskTradeAmount - bar.effectiveBidTradeAmount) / tradeDollars);

		}
		return true;
	}
}