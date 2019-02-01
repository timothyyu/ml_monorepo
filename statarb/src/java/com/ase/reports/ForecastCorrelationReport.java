package ase.reports;

import java.io.File;
import java.io.Writer;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.collections15.BidiMap;
import org.apache.commons.collections15.bidimap.DualTreeBidiMap;
import org.apache.commons.lang.ArrayUtils;
import org.ujmp.core.Matrix;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DoubleMatrix2D;
import org.ujmp.core.doublematrix.calculation.general.decomposition.Eig;

import ase.apps.DailyManager.OutputType;
import ase.calculator.BarraCalculator;
import ase.calculator.Forecast;
import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.portfolio.PortfolioUtils;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Triplet;

public class ForecastCorrelationReport {
	private static final Logger log = LoggerFactory.getLogger(ForecastCorrelationReport.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	protected static final int REPEAT_ROW_NAMES = 8;

	protected static boolean barraIndustryFactor(AttrType factor) {
		String name = factor.name.substring(2);
		if (BarraCalculator.BARRA_INDUSTRIES.contains(name))
			return true;
		else
			return false;
	}

	// XXX We make absolutely sure that forecast FULL is row 0. It will make things much easier when we process the data matrix
	public static Triplet<BidiMap<String, Integer>, BidiMap<String, Integer>, Matrix> fcCorrMatrix(Map<Integer, Map<Forecast, Double>> forecasts,
			Map<Security, Map<AttrType, Attribute>> exposures) {
		BidiMap<String, Integer> forecastName2Row = new DualTreeBidiMap<String, Integer>();
		BidiMap<String, Integer> factorName2Row = new DualTreeBidiMap<String, Integer>();
		BidiMap<Integer, Integer> secid2Column = new DualTreeBidiMap<Integer, Integer>();
		int numRows = 0;
		int numColumns = 0;

		// manually insert FULL
		forecastName2Row.put("FULL", 0);
		numRows++;

		// figure out how many forecasts are there
		for (Map.Entry<Integer, Map<Forecast, Double>> e1 : forecasts.entrySet()) {
			Integer secid = e1.getKey();
			if (!secid2Column.containsKey(secid))
				secid2Column.put(secid, numColumns++);
			for (Map.Entry<Forecast, Double> e2 : e1.getValue().entrySet()) {
				Forecast fc = e2.getKey();
				if (!forecastName2Row.containsKey(fc.name))
					forecastName2Row.put(fc.name, numRows++);
			}
		}

		// figure out how many factors are there, ignoring industry factors
		for (Map.Entry<Security, Map<AttrType, Attribute>> e1 : exposures.entrySet()) {
			Integer secid = e1.getKey().getSecId();
			if (!secid2Column.containsKey(secid))
				secid2Column.put(secid, numColumns++);
			for (Map.Entry<AttrType, Attribute> e2 : e1.getValue().entrySet()) {
				AttrType f = e2.getKey();
				if (barraIndustryFactor(f))
					continue;
				if (!factorName2Row.containsKey(f.name))
					factorName2Row.put(f.name, numRows++);
			}
		}

		// the matrix is assumed to be (num_forecestats + num_factors) x (num_secs), i.e., dimensions x observations
		DoubleMatrix2D data = DoubleMatrix2D.factory.zeros(numRows, numColumns);

		for (Map.Entry<Integer, Map<Forecast, Double>> e1 : forecasts.entrySet()) {
			int column = secid2Column.get(e1.getKey());
			for (Map.Entry<Forecast, Double> e2 : e1.getValue().entrySet()) {
				int row = forecastName2Row.get(e2.getKey().name);
				double value = e2.getValue();
				data.setAsDouble(value, row, column);
			}
		}

		for (Map.Entry<Security, Map<AttrType, Attribute>> e1 : exposures.entrySet()) {
			int column = secid2Column.get(e1.getKey().getSecId());
			for (Map.Entry<AttrType, Attribute> e2 : e1.getValue().entrySet()) {
				if (barraIndustryFactor(e2.getKey()))
					continue;
				int row = factorName2Row.get(e2.getKey().name);
				double value = e2.getValue().asDouble();
				data.setAsDouble(value, row, column);
			}
		}

		return new Triplet<BidiMap<String, Integer>, BidiMap<String, Integer>, Matrix>(forecastName2Row, factorName2Row, data);
	}

	public static void fcCorrReport(String location, Exchange.Type exch, long currentDate, Set<OutputType> output) throws Exception {
		// Get the last mu file of the day
		NavigableMap<Long, File> muFiles = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/mus", FileUtils.MUS_PATTERN);
		if (muFiles == null || muFiles.size() == 0) {
			log.severe("Failed to locate a mu file in location");
			return;
		}
		File muFile = muFiles.lastEntry().getValue();

		// Get the last calcres of the day
		NavigableMap<Long, File> calcresFiles = FileUtils.getDumpedFiles(location + "/" + df.toYYYYMMDD(currentDate) + "/calcres", FileUtils.CALCRES_PATTERN);
		if (calcresFiles == null || calcresFiles.size() == 0) {
			log.severe("Failed to locate a calcres file in location");
			return;
		}
		File calcresFile = calcresFiles.lastEntry().getValue();
		CalcResults calcres = CalcResults.restore(calcresFile);

		Triplet<BidiMap<String, Integer>, BidiMap<String, Integer>, Matrix> corrInfo = fcCorrMatrix(PortfolioUtils.loadMus(muFile),
				calcres.getFactorExposures(true, true));

		// //////////////////
		// /CORRELATION PART
		// //////////////////

		Vector<String> corrHeader = new Vector<String>();
		corrHeader.add("");
		int cnt = 1;
		for (String s : corrInfo.first.keySet()) {
			corrHeader.add(s);
			if (cnt++ % REPEAT_ROW_NAMES == 0) {
				corrHeader.add("");
			}
		}
		for (String s : corrInfo.second.keySet()) {
			corrHeader.add(s);
			if (cnt++ % REPEAT_ROW_NAMES == 0) {
				corrHeader.add("");
			}
		}

		Report corrReport = new Report(corrHeader.size(), corrHeader.size());
		corrReport.addHeader(corrHeader);

		Matrix corrMatrix = corrInfo.third.transpose(Ret.LINK).corrcoef(Ret.NEW, false);
		for (String r : corrInfo.first.keySet()) {
			Vector<String> body = new Vector<String>();
			body.add(r);
			cnt = 1;
			int matrixRow = corrInfo.first.inverseBidiMap().getKey(r);
			for (String c : corrInfo.first.keySet()) {
				int matrixColumn = corrInfo.first.inverseBidiMap().getKey(c);
				double value = corrMatrix.getAsDouble(matrixRow, matrixColumn);

				String accent = "";
				if (matrixRow == matrixColumn)
					accent = "";
				else if (Math.abs(value) > 0.8)
					accent = "*** ";
				else if (Math.abs(value) > 0.6)
					accent = "** ";
				else if (Math.abs(value) > 0.4)
					accent = "* ";

				body.add(accent + df.fformat(value));
				if (cnt++ % REPEAT_ROW_NAMES == 0) {
					body.add(r);
				}
			}
			for (String c : corrInfo.second.keySet()) {
				int matrixColumn = corrInfo.second.inverseBidiMap().getKey(c);
				double value = corrMatrix.getAsDouble(matrixRow, matrixColumn);

				String accent = "";
				if (matrixRow == matrixColumn)
					accent = "";
				else if (Math.abs(value) > 0.8)
					accent = "*** ";
				else if (Math.abs(value) > 0.7)
					accent = "** ";
				else if (Math.abs(value) > 0.5)
					accent = "* ";

				body.add(accent + df.fformat(value));
				if (cnt++ % REPEAT_ROW_NAMES == 0) {
					body.add(r);
				}
			}
			corrReport.addBody(body);
		}

		// Eigendecomposition of the forecast correlation matrix
		// Assert that forecast Row, which we want to remove from this computation is indeed row 0
		assert corrInfo.first.get("FULL").equals(0);
		int F = (corrInfo.first.keySet().size() - 1);
		Eig.EigMatrix eig1 = new Eig.EigMatrix(corrMatrix.select(Ret.LINK, "1-" + F + ";1-" + F));
		double[] d = eig1.getRealEigenvalues();
		double[] dc = new double[d.length];
		// XXX why the fuck are they in ascending order?
		ArrayUtils.reverse(d);
		double sum = 0.0;
		for (int i = 0; i < d.length; i++) {
			sum += d[i];
			dc[i] = sum;
		}
		for (int i = 0; i < d.length; i++) {
			d[i] = 100.0 * d[i] / sum;
			dc[i] = 100.0 * dc[i] / sum;
		}

		corrReport.addPreHeader("Forecast correlation matrix EigenValue mass (%): ");
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < d.length; i++)
			sb.append(df.fformat(d[i]) + "%, ");
		corrReport.addPreHeader(sb.substring(0, sb.length() - 2));

		corrReport.addPreHeader("Forecast correlation matrix EigenValue cummulative mass (%): ");
		sb = new StringBuilder();
		for (int i = 0; i < dc.length; i++)
			sb.append(df.fformat(dc[i]) + "%, ");
		corrReport.addPreHeader(sb.substring(0, sb.length() - 2));
		corrReport.addPreHeader("");

		// //////////////////
		// /COVARIANCE PART
		// //////////////////

		Matrix covMatrix = corrInfo.third.transpose(Ret.LINK).cov(Ret.NEW, false);
		// Assert that forecast Row, which we want to remove from this computation is indeed row 0
		assert corrInfo.first.get("FULL").equals(0);
		Eig.EigMatrix eig2 = new Eig.EigMatrix(covMatrix.select(Ret.LINK, "1-" + F + ";1-" + F));
		d = eig2.getRealEigenvalues();
		ArrayUtils.reverse(d);
		sum = 0.0;
		for (int i = 0; i < d.length; i++) {
			sum += d[i];
			dc[i] = sum;
		}
		for (int i = 0; i < d.length; i++) {
			d[i] = 100.0 * d[i] / sum;
			dc[i] = 100.0 * dc[i] / sum;
		}

		Vector<String> covHeader = new Vector<String>();
		covHeader.add("");
		for (int i = 1; i <= F; i++)
			covHeader.add("Eigen" + i + " (" + df.fformat(d[i - 1]) + "%)");
		Report covReport = new Report(covHeader.size(), covHeader.size());
		covReport.addHeader(covHeader);

		covReport.addPreHeader("Forecast covariance matrix EigenValue mass (%): ");
		sb = new StringBuilder();
		for (int i = 0; i < d.length; i++)
			sb.append(df.fformat(d[i]) + "%, ");
		covReport.addPreHeader(sb.substring(0, sb.length() - 2));

		covReport.addPreHeader("Forecast covariance matrix EigenValue cummulative mass (%): ");
		sb = new StringBuilder();
		for (int i = 0; i < dc.length; i++)
			sb.append(df.fformat(dc[i]) + "%, ");
		covReport.addPreHeader(sb.substring(0, sb.length() - 2));
		covReport.addPreHeader("");

		Matrix U = eig2.getV();
		for (String r : corrInfo.first.keySet()) {
			if (r.equals("FULL"))
				continue;
			Vector<String> body = new Vector<String>();
			body.add(r);
			// XXX note how we subtract 1. This is because by removing row 0 of forecast FULL, everything shifted by 1
			int matrixRow = corrInfo.first.inverseBidiMap().getKey(r) - 1;
			for (int matrixColumn = F - 1; matrixColumn >= 0; matrixColumn--) {
				double value = U.getAsDouble(matrixRow, matrixColumn);
				// Do not present small values corresponding to 10% of the forecast's variance
				if (Math.abs(value) > Math.sqrt(0.05))
					body.add(df.fformat(value) + " (" + df.fformat(value * value) + ")");
				else
					body.add("");
			}
			covReport.addBody(body);
		}

		File reportDir = new File(System.getenv("ROOT_DIR") + "/reports/" + System.getenv("STRAT") + "/various/" + df.toYYYYMMDD(currentDate));
		reportDir.mkdirs();
		Writer writer = FileUtils.makeWriter(new File(reportDir, "mucorr." + df.toYYYYMMDD(currentDate) + ".txt"));
		writer.write(corrReport.generateReport(" | ", true));
		writer.write(covReport.generateReport(" | ", true));
		writer.close();

		System.out.println(corrReport.generateReport(" | ", true));
		System.out.println(covReport.generateReport(" | ", true));
	}
}
