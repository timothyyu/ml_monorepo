package ase.reports;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Vector;

import ase.data.Security;
import ase.portfolio.PortfolioStats;
import ase.portfolio.PortfolioStats.DailyStats;
import ase.reports.Report.ReportAttrType;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.util.ASEFormatter;
import ase.util.Pair;
import ase.util.Triplet;

public class PerformanceReport {
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static Report secReport(Security sec, PortfolioStats ps) {
		Vector<DailyStats> stats = ps.getStats();

		// String[] header = new String[] { "ts", "shares", "price", "daypnl", "traded dollars" };
		// Report report = new Report(header.length, header.length);
		// report.addHeader(header);
		Report report = new Report(6, 6);

		DailyStats start = ps.getStats().get(0);
		report.addBody(new String[] { Integer.toString(sec.getSecId()), df.formatHumanShort(start.ts), df.fformat(start.longvalue),
				df.fformat(start.shortvalue), df.fformat(0.0), df.fformat(0.0) });
		// iterate to generate body
		for (int i = 1; i < stats.size(); i++) {
			DailyStats prev = stats.get(i - 1);
			DailyStats curr = stats.get(i);

			Vector<String> line = new Vector<String>();
			// stats component
			report.addBody(new String[] { Integer.toString(sec.getSecId()), df.formatHumanShort(curr.ts), df.fformat(curr.longvalue),
					df.fformat(curr.shortvalue), df.fformat(curr.cummulativePnl - prev.cummulativePnl),
					df.fformat(curr.cummulativeDollarsTraded - prev.cummulativeDollarsTraded) });
		}

		return report;
	}
	
	public static Report report(PortfolioStats ps, boolean includeCosts, Map<String, Vector<String>> extraInfo) {
		if (includeCosts) {
			ps = ps.costAdjust();
		}

		Vector<DailyStats> stats = ps.getStats();
		extraInfo = (extraInfo == null) ? new HashMap<String, Vector<String>>() : extraInfo;

		Vector<String> header = new Vector<String>();
		header.addAll(Arrays.asList(new String[] { "ts", "long", "short", "cum. pnl", "daypnl", "day return", "traded", "trading pnl" }));
		if (includeCosts)
			header.addAll(Arrays.asList(new String[] { "slippage", "est slippage", "costs" }));
		for (Map.Entry<String, Vector<String>> e : extraInfo.entrySet()) {
			assert stats.size() == e.getValue().size();
			header.add(e.getKey());
		}
		Report report = new Report(header.size(), header.size());
		report.addHeader(header);

		// first line of body
		Vector<String> startLine = new Vector<String>();
		DailyStats start = stats.get(0);
		// stats component
		startLine.addAll(Arrays.asList(new String[] { df.formatHumanShort(start.ts), df.fformat(start.longvalue), df.fformat(start.shortvalue),
				df.fformat(start.cummulativePnl), df.fformat(0.0), df.fformat(0.0), df.fformat(0.0), df.fformat(0.0) }));
		if (includeCosts)
			startLine.addAll(Arrays.asList(new String[] { df.fformat(0.0), df.fformat(0.0), df.fformat(0.0) }));
		// extra component
		for (Map.Entry<String, Vector<String>> e : extraInfo.entrySet())
			startLine.add(e.getValue().get(0));
		report.addBody(startLine);
				
		// iterate to generate body
		for (int i = 1; i < stats.size(); i++) {
			DailyStats curr = stats.get(i);

			Vector<String> line = new Vector<String>();
			// stats component
			line.addAll(Arrays.asList(new String[] { df.formatHumanShort(curr.ts), df.fformat(curr.longvalue), df.fformat(curr.shortvalue),
					df.fformat(curr.cummulativePnl), df.fformat(ps.getPnl(i)), df.fformat(10000.0 * ps.getReturn(i)), df.fformat(ps.getTurnover(i)),
					df.fformat(ps.getTradingPnl(i))}));
			if (includeCosts)
				line.addAll(Arrays.asList(new String[] { df.fformat(curr.diffSlippagePaid), df.fformat(curr.diffEstSlippage), df.fformat(curr.diffCosts) }));
			// extra component
			for (Map.Entry<String, Vector<String>> e : extraInfo.entrySet())
				line.add(e.getValue().get(i));

			report.addBody(line);
		}

		Pair<DailyStats, DailyStats> drawdown = ps.computeDrawdown();
		Triplet<Double, Double, Double> sharpe = ps.computeSharpe();
		double upDays = ps.upPointsPct();
		double ttPnl = ps.getTotalTradingPnl();

		// generate preheader
		report.addPreHeader("Data points: " + (stats.size() - 1));
		report.addPreHeader("Total PnL: " + df.fformat(stats.get(stats.size() - 1).cummulativePnl - stats.get(0).cummulativePnl));
		report.addPreHeader("Total Trading PnL: " + df.fformat(ttPnl));
		report.addPreHeader("Mean: " + df.fformat(sharpe.first * 100) + "%");
		report.addPreHeader("Sigma: " + df.fformat(sharpe.second * 100) + "%");
		report.addPreHeader("Sharpe: " + df.fformat(sharpe.third));
		if (drawdown.first != null) {
			report.addPreHeader("Max drawdown: " + df.fformat(drawdown.first.cummulativePnl - drawdown.second.cummulativePnl) + " or "
					+ df.fformat(100 * (drawdown.first.cummulativePnl - drawdown.second.cummulativePnl) / (drawdown.first.cummulativePnl))
					+ "% of cum pnl at peak, between " + df.formatMins(drawdown.first.ts) + " and " + df.formatMins(drawdown.second.ts));
		}
		else {
			report.addPreHeader("No drawdown");
		}
		if (!Double.isNaN(upDays)) {
			report.addPreHeader("Up days: " + df.fformat(100 * upDays) + "%");
		}
		report.addPreHeader("");

		return report;
	}

	// XXX Special symbol FULL is reserved for full portfolio
	public static String multiReport(Map<String, PortfolioStats> portfolios, boolean includeCosts, Map<String, Map<String, Vector<String>>> extras) {
		extras = (extras == null) ? new HashMap<String, Map<String, Vector<String>>>() : extras;
		StringBuilder sb = new StringBuilder();

		String[] diffHeader = new String[] { "name", "mean % diff", "sigma % diff", "sharpe diff", "cum pnl diff", "marginal" };
		Report diffReport = new Report(diffHeader.length - 1, diffHeader.length);
		diffReport.addHeader(diffHeader);

		PortfolioStats full = portfolios.get("FULL");
		full = includeCosts ? full.costAdjust() : full;
		Triplet<Double, Double, Double> fullSharpe = full.computeSharpe();
		diffReport.addBody(new String[] { "FULL", df.fformat(100 * fullSharpe.first), df.fformat(100 * fullSharpe.second), df.fformat(fullSharpe.third),
				df.fformat(full.getLatestStats().cummulativePnl), "0" });

		for (Map.Entry<String, PortfolioStats> m : portfolios.entrySet()) {
			if (m.getKey().equals("FULL"))
				continue;
			PortfolioStats ps = includeCosts ? m.getValue().costAdjust() : m.getValue();
			Triplet<Double, Double, Double> marginalSharpe = ps.computeSharpe();
			diffReport.addBody(new String[] { m.getKey(), df.fformat(100 * (marginalSharpe.first - fullSharpe.first)),
					df.fformat(100 * (marginalSharpe.second - fullSharpe.second)), df.fformat(marginalSharpe.third - fullSharpe.third),
					df.fformat(ps.getLatestStats().cummulativePnl - full.getLatestStats().cummulativePnl), "1" });
		}

		Sorter diffSorter = new Sorter();
		diffSorter.add(5, ReportAttrType.N, ReportSortType.ASC);
		diffSorter.add(3, ReportAttrType.N, ReportSortType.ASC);
		diffReport.sort(diffSorter);
		sb.append(diffReport.generateReport("  |  ", true));

		sb.append("\n\n");
		sb.append("FULL" + "\n");
		sb.append(report(portfolios.get("FULL"), true, extras.get("FULL")).generateReport("  |  ", true));
		for (Map.Entry<String, PortfolioStats> m : portfolios.entrySet()) {
			if (m.getKey().equals("FULL"))
				continue;
			sb.append("\n\n");
			sb.append(m.getKey() + "\n");
			sb.append(report(m.getValue(), true, extras.get(m.getKey())).generateReport("  |  ", true));
		}

		return sb.toString();
	}
}
