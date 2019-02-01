package ase.reports;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Security;
import ase.portfolio.IdealTrades;
import ase.portfolio.OptInfo;
import ase.reports.Report.ReportAttrType;
import ase.reports.Report.ReportSortType;
import ase.reports.Report.Sorter;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class OptReports {
	private static final Logger log = LoggerFactory.getLogger(OptReports.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	
	public static void constraintTightnessReport(IdealTrades idealPortfolio, Map<Security, Pair<Double, Double>> finalBounds, double maxFactorExposure,
			CalcResults calcres, Logger log) {
		final double MAX_CONSTRAINT_TIGHNESS = 0.95;

		// Compute tightness of individual security bounds
		int totalSecs = 0;
		int lowerTightSecs = 0;
		int upperTightSecs = 0;
		double lowerTightDollars = 0;
		double upperTightDollars = 0;
		double totalDollars = 0;

		for (Map.Entry<Security, OptInfo> e : idealPortfolio.getPortfolio().entrySet()) {
			Security sec = e.getKey();
			OptInfo oi = e.getValue();
			// get bounds
			Pair<Double, Double> bounds = finalBounds.get(sec);
			if (bounds == null) {
				log.severe("Security in ideal portfolio is not associated with bounds: " + sec.getSecId());
			}

			double lb = bounds.first;
			double ub = bounds.second;
			double pos = oi.target_position;

			totalSecs++;
			totalDollars += Math.abs(pos);

			if (pos < MAX_CONSTRAINT_TIGHNESS * lb) {
				lowerTightSecs++;
				lowerTightDollars += Math.abs(pos);
			}

			if (pos > MAX_CONSTRAINT_TIGHNESS * ub) {
				upperTightSecs++;
				upperTightDollars += Math.abs(pos);
			}
		}

		StringBuilder sb = new StringBuilder();
		sb.append("***** Constraint Tightness Report *****\n");
		sb.append("Upper tight secs: " + upperTightSecs + " / " + totalSecs + "\n");
		sb.append("Upper tight dollars: " + df.fformat(upperTightDollars) + " / " + df.fformat(totalDollars) + " (" + df.fformat(100.0 * upperTightDollars/totalDollars) + "%)\n");
		sb.append("Lower tight secs: " + lowerTightSecs + " / " + totalSecs + "\n");
		sb.append("Lower tight dollars: " + df.fformat(lowerTightDollars) + " / " + df.fformat(totalDollars) + " (" + df.fformat(100.0 * lowerTightDollars/totalDollars) + "%)\n");

		// factor exposures
		Set<AttrType> factors = calcres.getFactors(true, false);
		Map<Security, Map<AttrType, Attribute>> exposures = calcres.getFactorExposures(true, false);
		Map<AttrType, Double> dollarFactorExposure = new HashMap<AttrType, Double>();
		for (AttrType factor : factors) {
			dollarFactorExposure.put(factor, 0.0);
		}

		for (Map.Entry<Security, OptInfo> e : idealPortfolio.getPortfolio().entrySet()) {
			Security sec = e.getKey();
			OptInfo oi = e.getValue();
			Map<AttrType, Attribute> exp = exposures.get(sec);
			if (exp == null)
				continue;
			for (Map.Entry<AttrType, Attribute> p : exp.entrySet()) {
				AttrType factor = p.getKey();
				double fe = p.getValue().asDouble();
				double fd = dollarFactorExposure.get(factor);

				dollarFactorExposure.put(factor, fd + fe * oi.target_position);
			}
		}

		for (AttrType factor : factors) {
			double exp = dollarFactorExposure.get(factor);

			if (exp > MAX_CONSTRAINT_TIGHNESS * maxFactorExposure) {
				sb.append("Factor " + factor.name + " is upper tight : " + df.fformat(exp) + " / " + df.fformat(maxFactorExposure) + "\n");
			}
			if (exp < -MAX_CONSTRAINT_TIGHNESS * maxFactorExposure) {
				sb.append("Factor " + factor.name + " is lower tight : " + df.fformat(exp) + " / " + df.fformat(-maxFactorExposure) + "\n");
			}
		}

		log.info(sb.toString());
	}

	public static void factorExposureReport(IdealTrades idealPortfolio, CalcResults calcres, Logger log) {
		// factor exposures
		Set<AttrType> factors = new TreeSet<AttrType>(calcres.getFactors(true, true));
		Map<Security, Map<AttrType, Attribute>> exposures = calcres.getFactorExposures(true, true);
		Map<AttrType, Double> dollarFactorExposure = new HashMap<AttrType, Double>();
		for (AttrType factor : factors) {
			dollarFactorExposure.put(factor, 0.0);
		}

		for (Map.Entry<Security, OptInfo> e : idealPortfolio.getPortfolio().entrySet()) {
			Security sec = e.getKey();
			OptInfo oi = e.getValue();
			Map<AttrType, Attribute> exp = exposures.get(sec);
			if (exp == null)
				continue;
			for (Map.Entry<AttrType, Attribute> p : exp.entrySet()) {
				AttrType factor = p.getKey();
				double fe = p.getValue().asDouble();
				double fd = dollarFactorExposure.get(factor);

				dollarFactorExposure.put(factor, fd + fe * oi.target_position);
			}
		}

		double notional = idealPortfolio.getNotional();
		String[] header=new String[] {"factor", "notional", "%exp"};
		Report report=new Report(header.length,header.length);
		report.addPreHeader("***** Factor Exposure Report *****");
		report.addHeader(header);
		for (AttrType factor : factors) {
			double exp = dollarFactorExposure.get(factor);
			report.addBody(new String[]{factor.name, df.fformat(exp),df.fformat(100 * exp / notional) });
		}
		
		Sorter sorter=new Sorter();
		sorter.add(1, ReportAttrType.N, ReportSortType.ABS);
		report.sort(sorter);

		log.info(report.generateReport(" | ", true));
	}
}
