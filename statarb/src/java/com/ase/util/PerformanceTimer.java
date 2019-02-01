package ase.util;

import gnu.trove.TLongArrayList;

public class PerformanceTimer {
	private TLongArrayList times = new TLongArrayList();
	private long start;
	private long end;

	public PerformanceTimer() {

	}

	public void start() {
		this.start = System.nanoTime();
	}

	public void end() {
		this.end = System.nanoTime();
		times.add(this.end - this.start);
	}

	public void reset() {
		this.times.clear();
	}

	public double avgTimeInMillis() {
		int n = this.times.size();
		int i = 0;
		long avgTime = 0;
		
		while (i != n) {
			avgTime += this.times.getQuick(i);
			i++;
		}
		
		return 1.0*avgTime/1e6/n;
	}
}
