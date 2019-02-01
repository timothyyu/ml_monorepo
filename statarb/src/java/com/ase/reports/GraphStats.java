package ase.reports;

import java.io.File;
import java.io.Writer;
import java.util.logging.Logger;

import ase.data.Exchange;
import ase.portfolio.PortfolioStats;
import ase.portfolio.PortfolioUtils;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class GraphStats {
	private static final Logger log = LoggerFactory.getLogger(GraphStats.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public static void intradayLive(String location, Exchange.Type exch, long currentDate, int interval) throws Exception {
		PortfolioStats stats = PortfolioUtils.getIntradayStats(location, currentDate, exch, Math.min(Exchange.closeTime(currentDate, exch), Time.now()),
				interval);

		long open = Exchange.openTime(currentDate, exch);
		long close = Exchange.closeTime(currentDate, exch);
		long from = open;
		long to = from + Time.MILLIS_PER_MINUTE * interval;
		int index = 1;

		String[] pnlHeader = new String[] { "Timestamp", "PnL", "Trading PnL" };
		Report pnlReport = new Report(pnlHeader.length, pnlHeader.length);
		pnlReport.addHeader(pnlHeader);

		String[] sizeHeader = new String[] { "Timestamp", "Long Side", "Short Side", "Turnover" };
		Report sizeReport = new Report(sizeHeader.length, sizeHeader.length);
		sizeReport.addHeader(sizeHeader);

		for (; to <= close; from = to, to += Time.MILLIS_PER_MINUTE * interval, index++) {
			String time = df.formatHumanShort(to);
			time = time.substring(time.length() - 8, time.length());
			if (index < stats.size()) {
				assert to == stats.getDay(index).ts;

				double dayPnl = stats.getDay(index).cummulativePnl - stats.getDay(0).cummulativePnl;
				double dayTradingPnl = stats.getDay(index).tradingPnl;
				pnlReport.addBody(new String[] { time, df.fformat(dayPnl), df.fformat(dayTradingPnl) });

				double longv = stats.getDay(index).longvalue;
				double shortv = -stats.getDay(index).shortvalue;
				double turnover = stats.getDay(index).cummulativeDollarsTraded - stats.getDay(0).cummulativeDollarsTraded;
				sizeReport.addBody(new String[] { time, df.fformat(longv), df.fformat(shortv), df.fformat(turnover) });
			}
			else {
				pnlReport.addBody(new String[] { time, "null", "null" });
				sizeReport.addBody(new String[] { time, "null", "null", "null" });
			}
		}

		File outputDir = new File(System.getenv("ROOT_DIR") + "/" + "reports" + "/" + System.getenv("STRAT") + "/" + "pnl" + "/" + df.toYYYYMMDD(currentDate));
		outputDir.mkdir();

		Writer writer = FileUtils.makeWriter(new File(outputDir, "pnl_stats." + df.toYYYYMMDD(currentDate) + ".txt"));
		writer.write(pnlReport.generateReport("|", false));
		writer.close();

		writer = FileUtils.makeWriter(new File(outputDir, "size_stats." + df.toYYYYMMDD(currentDate) + ".txt"));
		writer.write(sizeReport.generateReport("|", false));
		writer.close();
	}

	public static Pair<Report, Report> perf(PortfolioStats stats) {
		String[] pnlHeader = new String[] { "Timestamp", "Total PnL", "Total Trading PnL" };
		Report pnlReport = new Report(pnlHeader.length, pnlHeader.length);
		pnlReport.addHeader(pnlHeader);

		String[] sizeHeader = new String[] { "Timestamp", "Notional", "Turnover" };
		Report sizeReport = new Report(sizeHeader.length, sizeHeader.length);
		sizeReport.addHeader(sizeHeader);

		double cummulativeTradingPnl = 0;
		for (int index = 1; index < stats.size(); index++) {
			String time = df.formatShort(stats.getDay(index).ts);

			double totalPnl = stats.getDay(index).cummulativePnl;
			double totalTradingPnl = stats.getDay(index).tradingPnl + cummulativeTradingPnl;
			cummulativeTradingPnl += stats.getDay(index).tradingPnl;
			pnlReport.addBody(new String[] { time, df.fformat(totalPnl), df.fformat(totalTradingPnl) });

			double longv = stats.getDay(index).longvalue;
			double shortv = -stats.getDay(index).shortvalue;
			double notional = longv + shortv;
			double turnover = stats.getDay(index).cummulativeDollarsTraded - stats.getDay(index - 1).cummulativeDollarsTraded;
			sizeReport.addBody(new String[] { time, df.fformat(notional), df.fformat(turnover) });
		}

		return new Pair<Report, Report>(pnlReport, sizeReport);
	}
}
