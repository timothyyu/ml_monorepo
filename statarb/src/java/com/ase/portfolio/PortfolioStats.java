package ase.portfolio;

import java.io.Writer;
import java.text.ParseException;
import java.util.Arrays;
import java.util.List;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.Exchange;
import ase.reports.PerformanceReport;
import ase.reports.Report;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.Triplet;

public class PortfolioStats {
	private static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(PortfolioStats.class.getName());
	private final List<DailyStats> stats = new Vector<DailyStats>();

	public class DailyStats {
		// Instance statistics
		public final long ts;
		public final double longvalue;
		public final double shortvalue;
		// Cummulative statistics
		public final double cummulativePnl;
		public final double cummulativeDollarsTraded;
		// Difference between two instances statistcs
		public final double diffSlippagePaid;
		public final double diffEstSlippage;
		public final double diffCosts;
		// leave it a bit ambiguous on purpose, usually should be diff, but depends when portfolio fills are cleared
		public final double tradingPnl;

		public DailyStats(long ts, double lv, double sv, double cumPnl, double cumDt, double diffSp, double diffCosts, double tradingPnl, double diffEstSp) {
			assert lv >= 0;
			assert sv <= 0;
			assert ts >= 0;
			assert !Double.isNaN(cumPnl);

			this.ts = ts;
			this.longvalue = lv;
			this.shortvalue = sv;
			this.cummulativePnl = cumPnl;
			this.cummulativeDollarsTraded = cumDt;
			this.diffSlippagePaid = diffSp;
			this.diffEstSlippage = diffEstSp;
			this.diffCosts = diffCosts;
			this.tradingPnl = tradingPnl;
		}

		public double notional() {
			return longvalue - shortvalue;
		}

		public String toString() {
			return "PNLSTAT|" + df.formatLong(ts) + "|" + longvalue + "|" + shortvalue + "|" + cummulativePnl + "|" + cummulativeDollarsTraded + "|"
					+ tradingPnl + "|" + diffSlippagePaid + "|" + diffEstSlippage + "|" + diffCosts;
		}
	}

	public PortfolioStats() {
	}

	public boolean isEmpty() {
		return stats.isEmpty();
	}

	public DailyStats getLatestStats() {
		if (stats.size() == 0)
			return null;
		return stats.get(stats.size() - 1);
	}

	public void addZero() {
		stats.add(new DailyStats(0, 0, 0, 0, 0, 0, 0, 0, 0));
	}

	public void add(long ts, double lv, double sv, double cumPnl, double cumDt, double diffSp, double diffCosts, double tradingPnl, double diffEstSp) {
		stats.add(new DailyStats(ts, lv, sv, cumPnl, cumDt, diffSp, diffCosts, tradingPnl, diffEstSp));
	}

	public DailyStats getDay(int index) {
		if (index < 0 || index > stats.size()) {
			return null;
		}
		else {
			return stats.get(index);
		}
	}

	// XXX the trading pnl is tricky... if points i and i-1 are on the same day, it is tpnl_{i}-tpnl_{i-1}. if we span day, it is simply tpnl_{i}
	// In other words, it accumulates within the same day, but resets once we rollover to a new day
	public double getTradingPnl(int index) {
		if (index <= 0 || index > stats.size()) {
			return Double.NaN;
		}
		double tpnl = (Time.today(stats.get(index).ts) == Time.today(stats.get(index - 1).ts)) ? stats.get(index).tradingPnl - stats.get(index - 1).tradingPnl
				: stats.get(index).tradingPnl;
		return tpnl;
	}

	public double getTotalTradingPnl() {
		double totalTradingPnl = 0;
		for (int i = 1; i < stats.size(); i++) {
			totalTradingPnl += getTradingPnl(i);
		}
		return totalTradingPnl;
	}

	public double getTurnover(int index) {
		if (index <= 0 || index > stats.size()) {
			return Double.NaN;
		}
		return stats.get(index).cummulativeDollarsTraded - stats.get(index - 1).cummulativeDollarsTraded;
	}

	public double getPnl(int index) {
		return getPnl(index, false);
	}

	public double getPnl(int index, boolean subtractCosts) {
		if (index <= 0 || index > stats.size()) {
			return Double.NaN;
		}
		double costs = subtractCosts ? stats.get(index).diffCosts : 0;
		return stats.get(index).cummulativePnl - stats.get(index - 1).cummulativePnl - costs;
	}

	public double getReturn(int index) {
		return getReturn(index, false);
	}

	public double getReturn(int index, boolean subtractCosts) {
		if (index <= 0 || index >= stats.size()) {
			return Double.NaN;
		}

		double pnl = getPnl(index, subtractCosts);
		double notional = stats.get(index).notional();

		if (pnl == 0)
			return 0.0;
		else
			return pnl / notional;
	}

	public double upPointsPct() {
		return upPointsPct(false);
	}

	public double upPointsPct(boolean subtractCosts) {
		if (stats.size() < 2)
			return Double.NaN;

		int up = 0;
		int total = 0;

		for (int i = 1; i < stats.size(); i++) {
			if (getPnl(i, subtractCosts) > 0)
				up++;
			total++;
		}

		return (double) up / total;
	}

	public Pair<DailyStats, DailyStats> computeDrawdown() {
		if (stats.size() <= 1)
			return new Pair<DailyStats, DailyStats>(null, null);

		DailyStats runningMax = stats.get(0);
		DailyStats peak = stats.get(0);
		DailyStats trough = null;
		double maxDrawdown = 0;

		for (int i = 1; i < stats.size(); i++) {
			DailyStats current = stats.get(i);
			if (current.cummulativePnl >= runningMax.cummulativePnl) {
				runningMax = current;
				continue;
			}
			else if (runningMax.cummulativePnl - current.cummulativePnl > maxDrawdown) {
				peak = runningMax;
				trough = current;
				maxDrawdown = runningMax.cummulativePnl - current.cummulativePnl;
			}
		}

		if (maxDrawdown > 0)
			return new Pair<DailyStats, DailyStats>(peak, trough);
		else
			return new Pair<DailyStats, DailyStats>(null, null);
	}

	public Triplet<Double, Double, Double> computeSharpe() {
		return computeSharpe(false);
	}

	public Triplet<Double, Double, Double> computeSharpe(boolean subtractCosts) {
		double sum = 0;
		double sum2 = 0;
		int cnt = 0;
		for (int i = 1; i < stats.size(); i++) {
			double dr = getReturn(i, subtractCosts);
			if (Double.isNaN(dr))
				continue;
			sum += dr;
			sum2 += dr * dr;
			cnt++;
		}

		double mean = sum / cnt;
		double sigma = Math.sqrt((sum2 - mean * mean) / (cnt - 1));
		mean *= Time.BIZ_DAYS_PER_YEAR;
		sigma *= Math.sqrt(Time.BIZ_DAYS_PER_YEAR);
		double sharpe = mean / sigma;
		return new Triplet<Double, Double, Double>(mean, sigma, sharpe);
	}

	public Vector<DailyStats> getStats() {
		return new Vector<DailyStats>(stats);
	}

	public void updateStats(Portfolio port, double slippage, double costs, double estSlippage) {
		assert port != null;
		log.info("Updating stats on portfolio: " + port.name + ".");
		double lv = 0.0, sv = 0.0, pnl = 0.0, dt = 0.0;
		for (Position pos : port.getPositions()) {
			if (!pos.isValid()) {
				// if (pos.sec.isAlive()) log.warning("Not updating stats for: " + pos);
				continue;
			}
			if (pos.notional() >= 0) {
				lv += pos.notional();
			}
			else if (pos.notional() < 0) {
				sv += pos.notional();
			}
			pnl += pos.getPnl();
			dt += pos.getDollarsTraded();
		}

		Portfolio tradingPortfolio = port.getTradingPortfolio();
		double tradingPnl = tradingPortfolio.getPnl();

		this.stats.add(new DailyStats(port.getAsOf(), lv, sv, pnl, dt, slippage, costs, tradingPnl, estSlippage));
	}

	public void updateStats(String line) throws NumberFormatException, ParseException {
		assert line != null;
		String[] tokens = line.split("\\|");
		assert tokens[0].equals("PNLSTAT");
		assert tokens.length == 10;

		this.stats.add(new DailyStats(df.parseLong(tokens[1]).getTime(), Double.parseDouble(tokens[2]), Double.parseDouble(tokens[3]), Double
				.parseDouble(tokens[4]), Double.parseDouble(tokens[5]), Double.parseDouble(tokens[7]), Double.parseDouble(tokens[9]), Double
				.parseDouble(tokens[6]), Double.parseDouble(tokens[8])));
	}

	public void dump(Writer writer) throws Exception {
		Report report = PerformanceReport.report(this, false, null);
		writer.write(report.generateReport("  |  ", true));
	}

	public void clear() {
		stats.clear();
	}

	public PortfolioStats costAdjust() {
		PortfolioStats ps = new PortfolioStats();

		double[] cummulativeCosts = new double[this.stats.size()];
		Arrays.fill(cummulativeCosts, 0.0);
		for (int i = 1; i < stats.size(); i++) {
			cummulativeCosts[i] = cummulativeCosts[i - 1] + stats.get(i).diffCosts; // + stats.get(i).diffSlippagePaid;
		}

		for (int i = 0; i < stats.size(); i++) {
			DailyStats stat = stats.get(i);
			ps.add(stat.ts, stat.longvalue, stat.shortvalue, stat.cummulativePnl - cummulativeCosts[i], stat.cummulativeDollarsTraded, stat.diffSlippagePaid,
					stat.diffCosts, stat.tradingPnl, stat.diffEstSlippage);
		}

		return ps;
	}

	public int size() {
		return stats.size();
	}
}
