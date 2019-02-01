package ase.data;

public class DistributionSummary {
	public final float high;
	public final float low;
	public final float mean;
	public final float stddev;
	public final float median;
	public final int count;
	
	public DistributionSummary(float mean, float stddev, float low, float median, float high, int count) {
		this.high = high;
		this.low = low;
		this.mean = mean;
		this.stddev = stddev;
		this.median = median;
		this.count = count;
	}
	
	public String toString() {
		return mean + "|" + stddev + "|" + low + "|" + median + "|" + high + "|" + count;
	}
}
