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
import ase.calculator.Forecast;
import ase.data.Exchange;
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

public class MuReport {
	private static final Logger log = LoggerFactory.getLogger(MuReport.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static Report createMuReport(Portfolio currentPortfolio, Portfolio sodPortfolio, Portfolio sowPortfolio, Portfolio somPortfolio)
			throws SQLException, IOException {

		String[] header = new String[] { "forecast", "notional", "lbias", "port. %", "day turn.", "day turn. %", "day bps", "day pnl", "trading pnl",
				"week pnl", "month pnl", "life pnl" };
		Report report = new Report(header.length, header.length);
		report.addPreHeader("As of: " + df.formatHuman(currentPortfolio.getMostRecentPriceTs()));
		report.addHeader(header);

		Map<Forecast, Portfolio> currentMus = currentPortfolio.getMuPortfolios();
		Map<Forecast, Portfolio> sodMus = sodPortfolio.getMuPortfolios();
		Map<Forecast, Portfolio> weekMus = (sowPortfolio != null) ? sowPortfolio.getMuPortfolios() : null;
		Map<Forecast, Portfolio> monthMus = (somPortfolio != null) ? somPortfolio.getMuPortfolios() : null;

		for (Forecast fcast : currentMus.keySet()) {
			Portfolio cmu = currentMus.get(fcast);
			Portfolio dmu = (sodMus != null && sodMus.containsKey(fcast)) ? sodMus.get(fcast) : null;
			Portfolio wmu = (weekMus != null && weekMus.containsKey(fcast)) ? weekMus.get(fcast) : null;
			Portfolio mmu = (monthMus != null && monthMus.containsKey(fcast)) ? monthMus.get(fcast) : null;

			Double turnover = cmu.stats.getLatestStats().cummulativeDollarsTraded - (dmu != null ? dmu.stats.getLatestStats().cummulativeDollarsTraded : 0);
			Double turnoverPct = (dmu != null) ? 100 * turnover / dmu.getNotional() : Double.NaN;
			Double fdpnl = (dmu != null) ? cmu.getPnl() - dmu.getPnl() : cmu.getPnl();
			// Double daybps = (dmu != null) ? 10000.0 * fdpnl / dmu.getNotional() : 10000.0 * fdpnl / cmu.getNotional();
			Double daybps = 10000.0 * fdpnl / cmu.getNotional();
			if (daybps.isInfinite() || daybps.isNaN())
				daybps = Double.NaN;
			Double tpnl = cmu.stats.getLatestStats().tradingPnl;
			Double fwpnl = (wmu != null) ? cmu.getPnl() - wmu.getPnl() : Double.NaN;
			Double fmpnl = (mmu != null) ? cmu.getPnl() - mmu.getPnl() : Double.NaN;
			double longval = cmu.getLongShortValue().first;
			double shortval = cmu.getLongShortValue().second;
			double lbias = 100.0 * (longval + shortval) / (longval - shortval);
			double perc = 100.0 * cmu.getNotional() / currentPortfolio.getNotional();

			report.addBody(new String[] { fcast.name, df.fformat(cmu.getNotional()), df.fformat(lbias), df.fformat(perc), df.fformat(turnover),
					df.fformat(turnoverPct), df.fformat(daybps), df.fformat(fdpnl), df.fformat(tpnl), df.fformat(fwpnl), df.fformat(fmpnl), df.fformat(cmu.getPnl()) });
		}
		return report;
	}

	public static void muReport(String location, Exchange.Type exch, long currentDate, boolean oldSystem, Set<OutputType> output, boolean live)
			throws Exception {
		Pair<Portfolio, Portfolio> dayPortfolios = PortfolioUtils.processDayPortfolio(location, exch, currentDate, oldSystem, live, true, 0);
		Portfolio sodPortfolio = dayPortfolios.first;
		Portfolio eodPortfolio = dayPortfolios.second;

		Portfolio weekPortfolio = PortfolioUtils.restoreDayPortfolio(location, Exchange.startOfTradingWeek(currentDate, exch), true);
		Portfolio monthPortfolio = PortfolioUtils.restoreDayPortfolio(location, Exchange.startOfTradingMonth(currentDate, exch), true);

		Report report = createMuReport(eodPortfolio, sodPortfolio, weekPortfolio, monthPortfolio);
		Sorter sorter = new Sorter();
		sorter.add(6, ReportAttrType.N, ReportSortType.DESC); // sort by day bps
		report.sort(sorter);
		String stringReport = report.generateReport("  |  ", true);

		if (output.contains(OutputType.SCREEN)) {
			System.out.println(stringReport);
		}
		if (output.contains(OutputType.FILE)) {
			File outdir = new File(System.getenv("ROOT_DIR") + "/" + "reports" + "/" + System.getenv("STRAT") + "/" + "pnl" + "/" + df.toYYYYMMDD(currentDate));
			outdir.mkdirs();

			File outfile = new File(outdir, "mu.pnl." + df.toYYYYMMDD(currentDate) + ".txt");
			Writer writer = FileUtils.makeWriter(outfile);
			writer.write(stringReport);
			writer.close();
		}
	}
}
