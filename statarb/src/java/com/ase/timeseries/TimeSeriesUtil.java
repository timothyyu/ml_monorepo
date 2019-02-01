package ase.timeseries;

import java.util.ListIterator;
import java.util.Vector;

import ase.data.Price;

public class TimeSeriesUtil {
	public static double c2cLogrel(Bar currentBar, Bar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else if (currentBar instanceof DailyBar && previousBar instanceof DailyBar) {
			DailyBar b2 = (DailyBar) currentBar;
			DailyBar b1 = (DailyBar) previousBar;
			return Math.log((b2.adjFactor * b2.close + b2.accDividends - b1.accDividends) / (b1.adjFactor * b1.close));
		}
		else if (currentBar instanceof Bar && previousBar instanceof Bar) {
			return Math.log(currentBar.close / previousBar.close);
		}
		else {
			throw new RuntimeException("How on earth did you manage to ask for the logrel of a Bar and a DailyBar?");
		}
	}

	// Specialize for DailyBars for efficiency(?)
	public static double c2cLogrel(DailyBar currentBar, DailyBar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else {
			return Math.log((currentBar.adjFactor * currentBar.close + currentBar.accDividends - previousBar.accDividends)
					/ (previousBar.adjFactor * previousBar.close));
		}
	}

	public static double o2cLogrel(Bar bar) {
		if (bar == null) {
			return Double.NaN;
		}
		else {
			return Math.log(bar.close / bar.open);
		}
	}

	public static double c2oLogrel(Bar currentBar, Bar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else if (currentBar instanceof DailyBar && previousBar instanceof DailyBar) {
			DailyBar b2 = (DailyBar) currentBar;
			DailyBar b1 = (DailyBar) previousBar;
			return Math.log((b2.adjFactor * b2.open + b2.accDividends - b1.accDividends) / (b1.adjFactor * b1.close));
		}
		else if (currentBar instanceof Bar && previousBar instanceof Bar) {
			return Math.log(currentBar.open / previousBar.close);
		}
		else {
			throw new RuntimeException("How on earth did you manage to ask for the logrel of a Bar and a DailyBar?");
		}
	}

	public static double c2oLogrel(DailyBar currentBar, DailyBar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else {
			return Math.log((currentBar.adjFactor * currentBar.open + currentBar.accDividends - previousBar.accDividends)
					/ (previousBar.adjFactor * previousBar.close));
		}
	}
	
	public static double o2cLogrel(Bar currentBar, Bar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else if (currentBar instanceof DailyBar && previousBar instanceof DailyBar) {
			DailyBar b2 = (DailyBar) currentBar;
			DailyBar b1 = (DailyBar) previousBar;
			return Math.log((b2.adjFactor * b2.close + b2.accDividends - b1.accDividends) / (b1.adjFactor * b1.open));
		}
		else if (currentBar instanceof Bar && previousBar instanceof Bar) {
			return Math.log(currentBar.close / previousBar.open);
		}
		else {
			throw new RuntimeException("How on earth did you manage to ask for the logrel of a Bar and a DailyBar?");
		}
	}

	public static double o2cLogrel(DailyBar currentBar, DailyBar previousBar) {
		if (currentBar == null || previousBar == null) {
			return Double.NaN;
		}
		else {
			return Math.log((currentBar.adjFactor * currentBar.close + currentBar.accDividends - previousBar.accDividends)
					/ (previousBar.adjFactor * previousBar.open));
		}
	}

	public static double logrel(Price p1, Price p2) {
		return Math.log(p2.getPrice() / p1.getPrice());
	}

	public static double logrel(double p1, double p2) {
		return Math.log(p2 / p1);
	}
	
	public static double[] o2cLogrels(BarTimeSeries bts) {
		double[] logrels = new double[bts.size()];
		int ii=0;
		ListIterator<Bar> it = bts.getBars();
		while (it.hasNext()) {
			logrels[ii] = o2cLogrel(it.next());
		}
		return logrels;
	}

	// XXX only works for intraday bars!!!
	public static Bar aggregateBars(Vector<Bar> bars) {
		if (bars == null || bars.size() == 0)
			return null;
		Bar first = bars.firstElement();
		if (bars.size() == 1)
			return new Bar(first);
		double open = first.open;
		long open_ts = first.open_ts;
		double vol = 0;
		double high = first.high;
		double low = first.low;
		for (Bar b : bars) {
			vol += b.volume;
			if (b.high > high)
				high = b.high;
			if (b.low < low)
				low = b.low;
		}
		Bar last = bars.lastElement();
		double close = last.close;
		long close_ts = last.close_ts;
		return new Bar(last.sec, open_ts, close_ts, open, high, low, close, vol);
	}

	public static Bar aggregateBars(BarTimeSeries ts) {
		return aggregateBars(ts, Long.MIN_VALUE, Long.MAX_VALUE);
	}

	public static Bar aggregateBars(BarTimeSeries ts, long t1, long t2) {
		if (ts == null || ts.size() == 0)
			return null;
		long open_ts = Long.MAX_VALUE;
		long close_ts = Long.MIN_VALUE;
		double open;
		double high = Double.MIN_VALUE;
		double low = Double.MAX_VALUE;
		double close;
		double volume = 0;
		double meanSpread = 0;
		double meanEffectiveSpread = 0;
		double meanBidSize = 0;
		double meanAskSize = 0;
		int trades = 0;
		int bidTrades = 0;
		int midTrades = 0;
		int askTrades = 0;
		int effectiveBidTrades = 0;
		int effectiveMidTrades = 0;
		int effectiveAskTrades = 0;
		double bidTradeAmount = 0;
		double midTradeAmount = 0;
		double askTradeAmount = 0;
		double effectiveBidTradeAmount = 0;
		double effectiveMidTradeAmount = 0;
		double effectiveAskTradeAmount = 0;
		int barCount = 0;

		Bar firstBar = null;
		Bar lastBar = null;
		ListIterator<Bar> it = ts.getBars();
		while (it.hasNext()) {
			Bar b = it.next();
			if (b == null)
				continue;
			if (b.close_ts < t1)
				continue;
			else if (b.close_ts > t2)
				break;

			if (firstBar == null)
				firstBar = b;
			lastBar = b;
			barCount++;

			high = Math.max(high, b.high);
			low = Math.min(low, b.low);
			volume += b.volume;

			if (b.version > 1) {
				BarV2 b2 = (BarV2) b;
				meanSpread += b2.meanSpread;
				meanEffectiveSpread += b2.meanEffectiveSpread * b2.trades;
				meanBidSize += b2.meanBidSize;
				meanAskSize += b2.meanAskSize;
				trades += b2.trades;
				bidTrades += b2.bidTrades;
				midTrades += b2.midTrades;
				askTrades += b2.askTrades;
				effectiveBidTrades += b2.effectiveBidTrades;
				effectiveAskTrades += b2.effectiveAskTrades;
				effectiveMidTrades += b2.effectiveMidTrades;
				bidTradeAmount += b2.bidTradeAmount;
				askTradeAmount += b2.askTradeAmount;
				midTradeAmount += b2.midTradeAmount;
				effectiveBidTradeAmount += b2.effectiveBidTradeAmount;
				effectiveAskTradeAmount += b2.effectiveAskTradeAmount;
				effectiveMidTradeAmount += b2.effectiveMidTradeAmount;
			}
		}

		if (firstBar == null)
			return null;

		open_ts = firstBar.open_ts;
		close_ts = lastBar.close_ts;
		open = firstBar.open;
		close = lastBar.close;

		if (firstBar.version > 1) {
			meanSpread /= barCount;
			meanEffectiveSpread /= trades;
			meanBidSize /= barCount;
			meanAskSize /= barCount;
		}

		if (firstBar.version == 1) {
			return new Bar(firstBar.sec, open_ts, close_ts, open, high, low, close, volume);
		}
		else if (firstBar.version == 2) {
			return new BarV2(firstBar.sec, open_ts, close_ts, open, high, low, close, volume, meanSpread, meanEffectiveSpread, meanBidSize, meanAskSize,
					trades, bidTrades, midTrades, askTrades, effectiveBidTrades, effectiveMidTrades, effectiveAskTrades, bidTradeAmount, midTradeAmount,
					askTradeAmount, effectiveBidTradeAmount, effectiveMidTradeAmount, effectiveAskTradeAmount);
		}
		throw new RuntimeException("We should have never reached this point");
	}
}
