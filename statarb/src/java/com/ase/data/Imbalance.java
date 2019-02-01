package ase.data;

import ase.timeseries.TimestampedDatum;

public class Imbalance implements TimestampedDatum {

	public final Security sec;
	public final long ts;
	public final int matchedQty;
	public final int imbalance;
	public final double refPrice;
	public final double nearPrice;
	public final double farPrice;
	public final double lastTick;
	public final double bid;
	public final double ask;
	
	public Imbalance(Security sec, long ts, int matchedQty, int imbalance, double refPrice, double nearPrice, double farPrice, double lastTick, double bid,
			double ask) {
		this.sec = sec;
		this.ts = ts;
		this.matchedQty = matchedQty;
		this.imbalance = imbalance;
		this.refPrice = refPrice;
		this.nearPrice = nearPrice;
		this.farPrice = farPrice;
		this.lastTick = lastTick;
		this.bid = bid;
		this.ask = ask;
	}

	public long getTs() {
		return ts;
	}
}
