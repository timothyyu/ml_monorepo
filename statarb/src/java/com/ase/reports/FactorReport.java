package ase.reports;

import gnu.trove.TDoubleArrayList;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.util.HashMap;
import java.util.Map;
import java.util.HashSet;
import java.util.NavigableMap;
import java.util.Collection;
import java.util.Set;
import java.util.TreeSet;
import java.util.logging.Logger;

import ase.apps.DailyManager.OutputType;
import ase.calculator.Forecast;
import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.CalcAttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.NumericAttribute;
import ase.data.Exchange;
import ase.data.Security;
import ase.portfolio.Portfolio;
import ase.portfolio.PortfolioUtils;
import ase.portfolio.Position;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.util.ASEFormatter;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.math.ASEMath;

public class FactorReport {
	private static final Logger log = LoggerFactory.getLogger(FactorReport.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private static final String HIGH = "_H";
	private static final String LOW = "_L";
	private static final String MEDIUM = "_M";

	protected static Map<AttrType, Pair<Double, Integer>> totalFactorPnl(long date) throws IOException {
		File reportFile = new File(System.getenv("ROOT_DIR") + "/reports/" + System.getenv("STRAT") + "/factors/" + df.toYYYYMMDD(date) + "/" + "factors."
				+ df.toYYYYMMDD(date) + ".txt");

		Map<AttrType, Pair<Double, Integer>> result = new HashMap<AttrType, Pair<Double, Integer>>();
		if (reportFile.exists()) {
			String line;
			BufferedReader reader = FileUtils.openFileReader(reportFile);
			while ((line = reader.readLine()) != null) {
				if (!(line.replace(" ", "").startsWith("F:") || line.replace(" ", "").startsWith("M:")))
					continue;
				String[] tokens = line.replace(" ", "").split("\\|");
				if (tokens.length != 8)
					continue;
				AttrType factor = new AttrType(tokens[0], Type.N);
				Double totalPnL = Double.valueOf(tokens[7]);
				Integer since = Integer.valueOf(tokens[8]);

				result.put(factor, new Pair<Double, Integer>(totalPnL, since));
			}
			reader.close();
		}
		return result;
	}

	protected static String getFactorSuffix(double[] pcts, double exp) {
		int xx;
		for (xx = 0; xx < pcts.length && exp > pcts[xx]; xx++)
			;

		if (xx == 0)
			return LOW;
		else if (xx == 1)
			return MEDIUM;
		else if (xx == 2)
			return HIGH;
		else
			throw new RuntimeException();
	}

	protected static boolean isBinaryFactor(double[] vec) {
		boolean binary = true;
		final int n = vec.length;
		for (int i = 0; i != n; i++) {
			if (vec[i] < 0.0 || vec[i] > 1.0) {
				binary = false;
				break;
			}
		}
		return binary;
	}

	protected static Map<AttrType, double[]> bucketize(Set<AttrType> factors, Map<Security, Map<AttrType, Attribute>> exposures) {
		Map<AttrType, double[]> buckets = new HashMap<AttrType, double[]>();
		Map<AttrType, TDoubleArrayList> points = new HashMap<AttrType, TDoubleArrayList>();
		for (AttrType factor : factors) {
			points.put(factor, new TDoubleArrayList());
		}

		for (Map<AttrType, Attribute> secExp : exposures.values()) {
			for (Map.Entry<AttrType, Attribute> e : secExp.entrySet()) {
				points.get(e.getKey()).add(e.getValue().asDouble());
			}
		}

		for (AttrType factor : factors) {
			TDoubleArrayList fpoints = points.get(factor);
			if (isBinaryFactor(fpoints.toNativeArray())) {
				buckets.put(factor, null);
				continue;
			}

			if (fpoints.size() < 10) {
				log.severe("Factor " + factor.name + " has fewer than 10 exposures. Not bucketizing...");
				buckets.put(factor, null);
				continue;
			}

			double[] pct = ASEMath.percentiles(fpoints.toNativeArray(), new double[] { 33, 67 });
			buckets.put(factor, pct);
		}

		return buckets;
	}

	public static Report createDailyReport(String location, long currentDate, Exchange.Type exch, boolean oldSystem, Set<OutputType> output, boolean runOnForecasts) throws Exception {
		// Get the portfolio for the day
		Pair<Portfolio, Portfolio> portfolios = PortfolioUtils.processDayPortfolio(location, exch, currentDate, oldSystem, false, false, 0);
		Portfolio sodPortfolio = portfolios.first;
		Portfolio eodPortfolio = portfolios.second;
		
		NavigableMap<Long, File> calcresFiles = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres", FileUtils.CALCRES_PATTERN);
		
		if (calcresFiles == null) {
			log.severe("Failed to identify any calcres files for day " + df.toYYYYMMDD(currentDate));
			return null;
		}
		// gets the last calcres of the day		
		File calcresFile = calcresFiles.lastEntry().getValue();		
		System.out.println("Using calcres file: " + calcresFile.getAbsolutePath());
		
		CalcResults calcres = CalcResults.restore(calcresFile);

        Set<AttrType> factors = new HashSet<AttrType>();        
        Map<Security, Map<AttrType, Attribute>> exposures = new HashMap<Security, Map<AttrType, Attribute>>();
		if (runOnForecasts) {
    		Collection<Forecast> forecasts = Forecast.loadDefs("/apps/ase/config/opt.prod.cfg");
    		for ( Forecast forecast : forecasts ) {
    		    Map<Security, Double> vals = forecast.calculate(calcres, 5);
    		    AttrType forecastAttr = new CalcAttrType(forecast.name); 
    		    factors.add(forecastAttr);
    		    for ( Map.Entry<Security, Double> ent : vals.entrySet()) {
    		        Map<AttrType, Attribute> secAttrs = exposures.get(ent.getKey());
    		        if ( secAttrs == null ) {
    		            secAttrs = new HashMap<AttrType, Attribute>();
    		            exposures.put(ent.getKey(), secAttrs);
    		        }
    		        secAttrs.put(forecastAttr, new NumericAttribute(forecastAttr, ent.getKey(), calcres.getAsOf(), ent.getValue() * 1e4, calcres.getAsOf()));
    		    }
    		}
		}
		else {
		    factors = new TreeSet<AttrType>(calcres.getFactors(true, true));
	        exposures = calcres.getFactorExposures(true, true);
		}
		
		Map<AttrType, Double> factorDayPnL = new HashMap<AttrType, Double>();
		Map<AttrType, Double> factorExpNotional = new HashMap<AttrType, Double>();
		Map<AttrType, Double> factorNotional = new HashMap<AttrType, Double>();
		
		Map<AttrType, double[]> factorBuckets = bucketize(factors, exposures);
		 //Ammend factors with their bucketized versions
		for (Map.Entry<AttrType, double[]> e : factorBuckets.entrySet()) {
			if (e.getValue() != null) {
				factors.add(new AttrType(e.getKey().name + LOW, Type.N));
				factors.add(new AttrType(e.getKey().name + MEDIUM, Type.N));
				factors.add(new AttrType(e.getKey().name + HIGH, Type.N));
			}
		}

		// init maps
		for (AttrType factor : factors) {
			factorDayPnL.put(factor, 0.0);
			factorNotional.put(factor, 0.0);
			factorExpNotional.put(factor, 0.0);
		}
		// compute statistics for day
		for (Security sec : eodPortfolio.getSecurities()) {
			Position eodPosition = eodPortfolio.getPosition(sec);
			Position sodPosition = sodPortfolio.getPosition(sec);

			int secid = sec.getSecId();
			double notional = eodPosition.notional();
			double dayPnL = eodPosition.getPnl() - (sodPosition != null ? sodPosition.getPnl() : 0);
			
			if (Double.isNaN(dayPnL)) { 
				log.warning("NaN day PnL for "+secid+" on day "+df.formatShort(currentDate));
				continue;
			}

			Map<AttrType, Attribute> secExposures = exposures.get(sec);
			if (secExposures == null) {
				log.warning("No exposures found for secid " + secid + " using calcres " + calcresFile);
				continue;
			}

			for (Map.Entry<AttrType, Attribute> e : secExposures.entrySet()) {
				AttrType factor = e.getKey();
				double exp = e.getValue().asDouble();
				double[] pcts = factorBuckets.get(factor);

				factorDayPnL.put(factor, factorDayPnL.get(factor) + exp * dayPnL);
				factorExpNotional.put(factor, factorExpNotional.get(factor) + exp * notional);
				factorNotional.put(factor, factorNotional.get(factor) + Math.abs(exp * notional));
				if (pcts != null) {
					factor = new AttrType(factor.name + getFactorSuffix(pcts, exp), Type.N);
					exp = 1;
					factorDayPnL.put(factor, factorDayPnL.get(factor) + exp * dayPnL);
					factorNotional.put(factor, factorNotional.get(factor) + exp * notional);
				}
			}
		}

		Map<AttrType, Pair<Double, Integer>> prevDayTotalPnl = totalFactorPnl(Exchange.prevTradingDateTime(currentDate, exch));
		Map<AttrType, Pair<Double, Integer>> prevWeekTotalPnl = totalFactorPnl(Exchange.endOfPreviousTradingWeek(currentDate, exch));
		Map<AttrType, Pair<Double, Integer>> prevMonthTotalPnl = totalFactorPnl(Exchange.endOfPreviousTradingMonth(currentDate, exch));

		// finally assemble the report
		String[] header = new String[] { "factor", "notional exposure", "% exposure", "day pnl", "daypnl %", "week pnl", "month pnl", "total pnl", "since" };
		Report report = new Report(header.length, header.length);
		String today = df.toYYYYMMDD(currentDate);
		report.addPreHeader("As of: " + df.formatHuman(eodPortfolio.getMostRecentPriceTs()));
		report.addHeader(header);
		for (AttrType factor : factors) {
			Double notional = factorExpNotional.get(factor);
			Double pct = 100 * factorExpNotional.get(factor) / (eodPortfolio.getLongShortValue().first - eodPortfolio.getLongShortValue().second);
			Double daypnl = factorDayPnL.get(factor);
			Double daypnlp = 100.0 * factorDayPnL.get(factor) / factorNotional.get(factor);
			Pair<Double, Integer> p1 = prevDayTotalPnl.get(factor);
			Pair<Double, Integer> p2 = prevWeekTotalPnl.get(factor);
			Pair<Double, Integer> p3 = prevMonthTotalPnl.get(factor);

			Double totalpnl = (p1 != null) ? p1.first + daypnl : daypnl;
			Integer since = (p1 != null) ? p1.second : Integer.valueOf(today);
			Double weekpnl = (p2 != null && p2.second.equals(since)) ? totalpnl - p2.first : Double.NaN;
			Double monthpnl = (p3 != null && p3.second.equals(since)) ? totalpnl - p3.first : Double.NaN;

			report.addBody(new String[] { factor.name, df.fformat(notional), df.fformat(pct), df.fformat(daypnl), df.fformat(daypnlp), df.fformat(weekpnl), df.fformat(monthpnl),
					df.fformat(totalpnl), since.toString() });
		}
		return report;
	}

	public static void dailyReport(String location, long currentDate, Exchange.Type exch, boolean oldSystem, Set<OutputType> output, boolean runOnForecasts) throws Exception {
		Report report = createDailyReport(location, currentDate, exch, oldSystem, output, runOnForecasts);
		if (report == null)
			return;

		Sorter sorter = new Sorter();
		int sortcol = runOnForecasts ? 4 : 3;
		sorter.add(sortcol, Report.ReportAttrType.N, ReportSortType.DESC);
		report.sort(sorter);
		String stringReport = report.generateReport("  |  ", true);
		if (output.contains(OutputType.SCREEN)) {

			System.out.println(stringReport);
		}
		if (output.contains(OutputType.FILE)) {
			File reportDir = new File(System.getenv("ROOT_DIR") + "/reports/" + System.getenv("STRAT") + "/factors/" + df.toYYYYMMDD(currentDate));
			reportDir.mkdirs();
			Writer writer = FileUtils.makeWriter(new File(reportDir, "factors." + df.toYYYYMMDD(currentDate) + ".txt"));
			writer.write(stringReport);
			writer.close();
		}
		if (output.contains(OutputType.EMAIL)) {
			Email.email("Factor report for day " + df.toYYYYMMDD(currentDate), stringReport);
		}

	}
}
