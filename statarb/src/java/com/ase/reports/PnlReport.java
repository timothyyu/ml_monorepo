package ase.reports;

import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.apps.DailyManager.OutputType;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.XRef;
import ase.data.widget.SQLSecurityWidget;
import ase.portfolio.Fill;
import ase.portfolio.Portfolio;
import ase.portfolio.PortfolioUtils;
import ase.portfolio.Position;
import ase.reports.Report.ReportAttrType;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class PnlReport {
	private static final Logger log = LoggerFactory.getLogger(PnlReport.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	protected static Map<Security, Double> pnlDiff(Portfolio cp, Portfolio pp) {
		Map<Security, Double> pd = new HashMap<Security, Double>();

		for (Security sec : cp.getSecurities()) {
			Position cpos = cp.getPosition(sec);
			Position ppos = (pp != null) ? pp.getPosition(sec) : null;
			Double pnl = (ppos != null) ? cpos.getPnl() - ppos.getPnl() : Double.NaN;
			pd.put(sec, pnl);
		}
		return pd;
	}

	public static Report pnlReport(Portfolio currentPortfolio, Portfolio sodPortfolio, Portfolio sowPortfolio, Portfolio somPortfolio) throws SQLException,
			IOException {
		//assert that the portfolios are real portfolios
		assert (currentPortfolio == null || !currentPortfolio.allowFracPos);
		assert (sodPortfolio == null || !sodPortfolio.allowFracPos);
		assert (sowPortfolio == null || !sowPortfolio.allowFracPos);
		assert (somPortfolio == null || !somPortfolio.allowFracPos);
		
		String[] header = new String[] { "ticker", "secid", "size", "price", "notional", "day turnover", "day pnl", "trading pnl", "week pnl", "month pnl",
				"life pnl", "price timestamp", "bad price" };
		Report report = new Report(header.length - 1, header.length);

		// output position info
		// get the positions by ticker
		Set<Security> secs = currentPortfolio.getSecurities();
		Map<Security, String> sec2ticker = SQLSecurityWidget.instance().getXrefMap(secs, currentPortfolio.getAsOf(), XRef.TIC);

		Double longv = currentPortfolio.stats.getLatestStats().longvalue;
		Double shortv = currentPortfolio.stats.getLatestStats().shortvalue;
		Double daypnl = currentPortfolio.stats.getPnl(currentPortfolio.stats.size()-1);
		Double dayreturn = currentPortfolio.stats.getReturn(currentPortfolio.stats.size()-1);
		Double totalpnl = currentPortfolio.getPnl();
		Double weekpnl = sowPortfolio != null ? currentPortfolio.getPnl() - sowPortfolio.getPnl() : Double.NaN;
		Double monthpnl = somPortfolio != null ? currentPortfolio.getPnl() - somPortfolio.getPnl() : Double.NaN;
		Double tradingpnl = currentPortfolio.stats.getLatestStats().tradingPnl;
		// trading portfolio
		Portfolio tradingPortfolio = currentPortfolio.getTradingPortfolio();

		report.addPreHeader("As of: " + df.formatHuman(currentPortfolio.getAsOf()));
		report.addPreHeader("Long: " + df.fformat(longv) + ", Short: " + df.fformat(shortv) + ", Day return: " + df.fformat(ASEMath.BPS_MULTIPLIER * dayreturn) + " bps, Day PnL: "
				+ df.fformat(daypnl) + ", Total PnL: " + df.fformat(totalpnl));
		report.addPreHeader("");
		report.addHeader(header);
		report.addHeader(new String[] { "TOTAL", "", "", "", df.fformat(currentPortfolio.getNotional()),
				df.fformat(currentPortfolio.stats.getLatestStats().cummulativeDollarsTraded - sodPortfolio.stats.getLatestStats().cummulativeDollarsTraded), df.fformat(daypnl),
				df.fformat(tradingpnl), df.fformat(weekpnl), df.fformat(monthpnl), df.fformat(totalpnl), "", "0" });

		// long range pnl diffs
		Map<Security, Double> weekPnlMap = pnlDiff(currentPortfolio, sowPortfolio);
		Map<Security, Double> monthPnlMap = pnlDiff(currentPortfolio, somPortfolio);

		for (Security sec : secs) {
			Position currentPosition = currentPortfolio.getPosition(sec);
			Position sodPosition = sodPortfolio.getPosition(sec);
			Position tradingPosition = tradingPortfolio.getPosition(sec);

			String ticker = sec2ticker.get(sec);
			int secid = sec.getSecId();
			int size = currentPosition.getIntShares();
			double price = currentPosition.getLatestPrice();
			long price_ts = currentPosition.getPriceTs();
			double notional = currentPosition.notional();
			double dayPnL = currentPosition.getPnl() - (sodPosition != null ? sodPosition.getPnl() : 0);
			double tradingPnL = (tradingPosition != null) ? tradingPosition.getPnl() : 0;
			double weekPnL = weekPnlMap.get(sec);
			double monthPnL = monthPnlMap.get(sec);
			double lifePnL = currentPosition.getPnl();
			double dayTurnover = currentPosition.getDollarsTraded() - (sodPosition != null ? sodPosition.getDollarsTraded() : 0);
			int badPrice = (currentPortfolio.getAsOf() - price_ts > 5 * Time.MILLIS_PER_DAY) ? 1 : 0;

			report.addBody(new String[] { ticker, String.valueOf(secid), String.valueOf(size), df.fformat(price), df.fformat(notional),
					df.fformat(dayTurnover), df.fformat(dayPnL), df.fformat(tradingPnL), df.fformat(weekPnL), df.fformat(monthPnL), df.fformat(lifePnL),
					df.formatHumanShort(price_ts), String.valueOf(badPrice) });
		}

		return report;
	}

	public static void continuousPnl(String location, Exchange.Type exch, long currentDate, Exchange.Type exchType, boolean oldSystem, Set<OutputType> output)
			throws Exception {
		long sleepyTime = 1 * 60 * 1000L;

		// INTRA-DAY COMPONENT
		// do not start getting prices until market open
		while (Time.now() <= Exchange.openTime(Time.now(), exchType)) {
			try {
				Thread.currentThread().sleep(sleepyTime);
			}
			catch (InterruptedException e) {
			}
		}

		// Main loop,
		while (Time.now() <= Exchange.closeTime(Time.now(), exchType)) {
			// update(location, day, exchType, oldSystem, true, toFile);
			singlePnl(location, exch, currentDate, oldSystem, output, true);
			try {
				Thread.currentThread().sleep(sleepyTime);
			}
			catch (InterruptedException e) {
				log.severe("My spleep was interrupted");
			}
		}

		// WAIT A BIT FOR FINAL BARS TO BE WRITTEN, since this is what we will
		// be using for eod prices afterwards
		try {
			Thread.currentThread().sleep(30L * 1000L);
		}
		catch (InterruptedException e) {
			log.severe("My spleep was interrupted");
		}

		// END-OF-DAY COMPONENT
		singlePnl(location, exch, currentDate, oldSystem, output, false);
	}

	public static void singlePnl(String location, Exchange.Type exch, long currentDate, boolean oldSystem, Set<OutputType> output, boolean live)
			throws Exception {
		PortfolioUtils.uSource.lqWidget.setIdentifier("pnl");
		Pair<Portfolio, Portfolio> dayPortfolios = PortfolioUtils.processDayPortfolio(location, exch, currentDate, oldSystem, live, false, 0);
		Portfolio sodPortfolio = dayPortfolios.first;
		Portfolio eodPortfolio = dayPortfolios.second;

		Portfolio weekPortfolio = PortfolioUtils.restoreDayPortfolio(location, Exchange.startOfTradingWeek(currentDate, exch), false);
		Portfolio monthPortfolio = PortfolioUtils.restoreDayPortfolio(location, Exchange.startOfTradingMonth(currentDate, exch), false);

		Report report = pnlReport(eodPortfolio, sodPortfolio, weekPortfolio, monthPortfolio);
		Sorter sorter = new Sorter();
		sorter.add(12, ReportAttrType.S, ReportSortType.ASC); // good prices
																// first
		sorter.add(6, ReportAttrType.N, ReportSortType.ABS); // sort by day pnl
		sorter.add(0, ReportAttrType.S, ReportSortType.ASC); // sort by tickers
		report.sort(sorter);
		String stringReport = report.generateReport("  |  ", true);

		if (output.contains(OutputType.SCREEN)) {
			System.out.println(stringReport);
		}
		if (output.contains(OutputType.FILE)) {
			File outdir = new File(System.getenv("ROOT_DIR") + "/" + "reports" + "/" + System.getenv("STRAT") + "/" + "pnl" + "/" + df.toYYYYMMDD(currentDate));
			outdir.mkdirs();

			File outfile = new File(outdir, "pnl." + df.toYYYYMMDD(currentDate) + ".txt");
			Writer writer = FileUtils.makeWriter(outfile);
			writer.write(stringReport);
			writer.close();
		}
	}

}
