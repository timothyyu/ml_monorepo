package ase.timeseries;

import ase.data.Security;

public class BarV2 extends Bar {
	public final int trades;
	public final double meanSpread;
	public final double meanEffectiveSpread;
	public final double meanBidSize;
	public final double meanAskSize;
	public final double bidTrades;
	public final double midTrades;
	public final double askTrades;
	public final double effectiveBidTrades;
	public final double effectiveMidTrades;
	public final double effectiveAskTrades;
	public final double bidTradeAmount;
	public final double midTradeAmount;
	public final double askTradeAmount;
	public final double effectiveBidTradeAmount;
	public final double effectiveMidTradeAmount;
	public final double effectiveAskTradeAmount;

	public BarV2(Security sec, long open_ts, long close_ts, double open, double high, double low, double close, double volume, double meanSpread,
			double meanEffectiveSpread, double meanBidSize, double meanAskSize, int trades, int bidTrades, int midTrades, int askTrades,
			int effectiveBidTrades, int effectiveMidTrades, int effectiveAskTrades, double bidTradeAmount, double midTradeAmount, double askTradeAmount,
			double effectiveBidTradeAmount, double effectiveMidTradeAmount, double effectiveAskTradeAmount) {
		super(sec, open_ts, close_ts, open, high, low, close, volume);
		this.trades = trades;
		this.meanSpread = meanSpread;
		this.meanEffectiveSpread = meanEffectiveSpread;
		this.meanBidSize = meanBidSize;
		this.meanAskSize = meanAskSize;
		this.bidTrades = bidTrades;
		this.midTrades = midTrades;
		this.askTrades = askTrades;
		this.effectiveBidTrades = effectiveBidTrades;
		this.effectiveMidTrades = effectiveMidTrades;
		this.effectiveAskTrades = effectiveAskTrades;
		this.bidTradeAmount = bidTradeAmount;
		this.midTradeAmount = midTradeAmount;
		this.askTradeAmount = askTradeAmount;
		this.effectiveBidTradeAmount = effectiveBidTradeAmount;
		this.effectiveMidTradeAmount = effectiveMidTradeAmount;
		this.effectiveAskTradeAmount = effectiveAskTradeAmount;

		this.version = 2;
	}

	public String toString() {
		return "" + sec + "|" + open_ts + "|" + close_ts + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume + "|" + meanSpread + "|"
				+ meanEffectiveSpread + "|" + meanBidSize + "|" + meanAskSize + "|" + trades + "|" + bidTrades + "|" + midTrades + "|" + askTrades + "|"
				+ effectiveBidTrades + "|" + effectiveMidTrades + "|" + effectiveAskTrades + "|" + bidTradeAmount + "|" + midTradeAmount + "|" + askTradeAmount
				+ "|" + effectiveBidTradeAmount + "|" + effectiveMidTradeAmount + "|" + effectiveAskTradeAmount;
	}

	public String toHRString() {
		return "" + sec + "|" + df.format(open_ts) + "|" + df.format(close_ts) + "|" + open + "|" + high + "|" + low + "|" + close + "|" + volume + "|"
				+ meanSpread + "|" + meanEffectiveSpread + "|" + meanBidSize + "|" + meanAskSize + "|" + trades + "|" + bidTrades + "|" + midTrades + "|"
				+ askTrades + "|" + effectiveBidTrades + "|" + effectiveMidTrades + "|" + effectiveAskTrades + "|" + bidTradeAmount + "|" + midTradeAmount
				+ "|" + askTradeAmount + "|" + effectiveBidTradeAmount + "|" + effectiveMidTradeAmount + "|" + effectiveAskTradeAmount;
	}
}
