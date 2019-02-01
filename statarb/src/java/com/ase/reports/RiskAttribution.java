package ase.reports;

import java.io.File;
import java.io.Writer;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Map.Entry;
import java.util.NavigableMap;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import org.ujmp.core.Matrix;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DenseDoubleMatrix2D;
import org.ujmp.core.doublematrix.SparseDoubleMatrix2D;

import ase.apps.DailyManager.OutputType;
import ase.calculator.FactorCalculator;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.XRef;
import ase.data.widget.SQLSecurityWidget;
import ase.portfolio.Portfolio;
import ase.portfolio.PortfolioUtils;
import ase.portfolio.Position;
import ase.reports.Report.ReportAttrType;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.util.ASEFormatter;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class RiskAttribution {

	private static final Logger log = LoggerFactory.getLogger(RiskAttribution.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static Report createDailyReport(String location, long currentDate, Exchange.Type exch, boolean oldSystem, Set<OutputType> output) throws Exception {
		// Get the portfolio for the day
		Portfolio portfolio = PortfolioUtils.processDayPortfolio(location, exch, currentDate, oldSystem, false, false, 0).second;
		// get the last calcres for the day
		NavigableMap<Long, File> calcresFiles = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres", FileUtils.CALCRES_PATTERN);
		if (calcresFiles == null) {
			log.severe("Failed to identify any calcres files for day " + df.toYYYYMMDD(currentDate));
			return null;
		}
		// gets the last calcres of the day
		File calcresFile = calcresFiles.lastEntry().getValue();
		CalcResults calcres = CalcResults.restore(calcresFile);

		// the set of securities that will operate on
		Vector<Security> secs = new Vector<Security>();
		secs.addAll(portfolio.getSecurities());
		int N = secs.size();

		// the relevant factors
		Vector<AttrType> factors = new Vector<AttrType>();
		factors.addAll(calcres.getFactors(true, false));
		int F = factors.size();

		// The matrices that we will use
		// factor loadings NxF
		Matrix X = DenseDoubleMatrix2D.factory.zeros(N, F);
		// factor covariance
		Matrix V = DenseDoubleMatrix2D.factory.zeros(F, F);
		// residual variances
		Matrix R = SparseDoubleMatrix2D.factory.eye(N, N);
		// The matrix of our curent positions
		Matrix P = DenseDoubleMatrix2D.factory.zeros(N, 1);

		Map<Security, Map<AttrType, Attribute>> loadings = calcres.getAllExposures();
		Map<Security, Attribute> rvars = calcres.getResult(FactorCalculator.RVAR_ATTR);

		// populate the matrices
		for (int ii = 0; ii < secs.size(); ii++) {
			Security sec = secs.get(ii);
			Position pos = portfolio.getPosition(sec);
			P.setAsDouble(pos.notional(), ii, 0);
			double rvar = rvars.containsKey(sec) ? rvars.get(sec).asDouble() : 0.0;
			R.setAsDouble(rvar, ii, ii);

			Map<AttrType, Attribute> secLoadings = loadings.get(sec);
			if (secLoadings == null || secLoadings.isEmpty())
				continue;
			for (int jj = 0; jj < factors.size(); jj++) {
				Attribute a = secLoadings.get(factors.get(jj));
				if (a != null)
					X.setAsDouble(a.asDouble(), ii, jj);
			}
		}

		Map<AttrType, Integer> factorToIndex = new HashMap<AttrType, Integer>();
		for (int ff = 0; ff < factors.size(); ff++) {
			factorToIndex.put(factors.get(ff), ff);
		}

		Iterator<Entry<Pair<AttrType, AttrType>, Double>> it = calcres.getFactorCov();
		while (it.hasNext()) {
			Entry<Pair<AttrType, AttrType>, Double> e = it.next();
			int ii = factorToIndex.get(e.getKey().first);
			int jj = factorToIndex.get(e.getKey().second);
			double v = e.getValue();
			V.setAsDouble(v, ii, jj);
			V.setAsDouble(v, jj, ii);
		}

		// compute statistics
		// Factor Exposures
		Matrix E = X.transpose().mtimes(P);

		// compute total risk
		double risk = (E.transpose().mtimes(V).mtimes(E).plus(P.transpose().mtimes(R).mtimes(P))).sqrt(Ret.NEW).getValueSum();

		// Factor marginal contribution to risk
		Matrix FMCR = V.mtimes(E).times(1 / risk);
		// Security marginal contribution to risk
		Matrix SMCR = R.mtimes(P).times(1 / risk);

		// Risk contributions
		Matrix FC = E.times(FMCR);
		Matrix SC = P.times(SMCR);

		double factorRisk = FC.getValueSum();
		double secRisk = SC.getValueSum();

//		 //Matrix whose each entry is the corresponding variance, covariance of factors in dollars^2
//		 Matrix FV0 = E.mtimes(E.transpose()).times(V);
//		 //Matrix whose diagonal contains the residual variances in dollars^2
//		 Matrix RV0 = P.power(Ret.LINK, 2).mtimes(R);
//		
//		 //collapse FV0, RV0 to column vectors, where each entry is the sum of the corresponding row
//		 Matrix FV1 = FV0.sum(Ret.NEW, Matrix.ROW, false);
//		 Matrix RV1 = RV0.sum(Ret.NEW, Matrix.ROW, false);
//		
//		 double factorVariance = FV1.getValueSum();
//		 double residualVariance = RV1.getValueSum();
//		 double var = factorVariance + residualVariance;

		String[] header = new String[] { "Name", "$ contribution to risk", "% contribution to risk", "type" };
		Report report = new Report(header.length - 1, header.length);
		report.addHeader(header);
		report.addPreHeader("Total Risk: " + df.fformat(risk)+"$");
		report.addPreHeader("% of risk due to factor exposure: " + df.fformat(100 * factorRisk / risk));
		report.addPreHeader("% of risk due to residual security exposure: " + df.fformat(100 * secRisk / risk));

		Map<Security, String> tickers = SQLSecurityWidget.instance().getXrefMap(portfolio.getSecurities(), currentDate, XRef.TIC);
		for (int ii = 0; ii < secs.size(); ii++) {
			report.addBody(new String[] { tickers.get(secs.get(ii)), df.fformat(SC.getAsDouble(ii, 0)), df.fformat(100.0 * SC.getAsDouble(ii, 0) / risk), "1" });
		}
		for (int ii = 0; ii < factors.size(); ii++) {
			report.addBody(new String[] { factors.get(ii).name, df.fformat(FC.getAsDouble(ii, 0)), df.fformat(100.0 * FC.getAsDouble(ii, 0) / risk), "0" });
		}

		Sorter sorter = new Sorter();
		sorter.add(3, ReportAttrType.S, ReportSortType.ASC);
		sorter.add(1, ReportAttrType.N, ReportSortType.DESC);
		sorter.add(0, ReportAttrType.S, ReportSortType.ASC);
		report.sort(sorter);

		return report;
	}
	
	public static void dailyReport(String location, long currentDate, Exchange.Type exch, boolean oldSystem, Set<OutputType> output) throws Exception {
		Report report = createDailyReport(location, currentDate, exch, oldSystem, output);
		if (report == null)
			return;

		String stringReport = report.generateReport("  |  ", true);
		if (output.contains(OutputType.SCREEN)) {

			System.out.println(stringReport);
		}
		if (output.contains(OutputType.FILE)) {
			File reportDir = new File(System.getenv("ROOT_DIR") + "/reports/" + System.getenv("STRAT") + "/risk/" + df.toYYYYMMDD(currentDate));
			reportDir.mkdirs();
			Writer writer = FileUtils.makeWriter(new File(reportDir, "risk." + df.toYYYYMMDD(currentDate) + ".txt"));
			writer.write(stringReport);
			writer.close();
		}
		if (output.contains(OutputType.EMAIL)) {
			Email.email("Risk attribution report for day " + df.toYYYYMMDD(currentDate), stringReport);
		}

	}
}
