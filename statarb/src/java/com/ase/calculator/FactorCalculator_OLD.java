package ase.calculator;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.ujmp.core.Matrix;
import org.ujmp.core.MatrixFactory;
import org.ujmp.core.calculation.Calculation;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DenseDoubleMatrix2D;
import org.ujmp.core.doublematrix.DoubleMatrix2D;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.FactorLoadings;
import ase.data.NumericAttribute;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.BarTimeSeries;
import ase.timeseries.DailyBarTimeSeries;
import ase.timeseries.TimeSeriesUtil;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class FactorCalculator_OLD extends Calculator {
	private static final Logger log = LoggerFactory.getLogger(FactorCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	
	public static enum ReturnType {DAILY, INTRADAY, CLOSE2OPEN};

	private static final boolean CAP_WEIGHTED_FACTORS = true;
	private static final boolean USE_INTRADAY = false;

	private static final int NUM_HALFLIFE_DAYS = 0;
	private static final int NUM_FACTOR_DAYS_TO_RECORD = 3;

	private static int MAX_SVD_IDX = 81;

	private final UnifiedDataSource uSource;
	private final FactorLoadingCalculator pCalc;

	private final int factor_days_lookback;
	private final int num_factor_days;
	private final Exchange.Type primaryExch;

	private Security[] secs;
	private AttrType[] factors;
	private AttrType[] monitorFactors;
	private FactorLoadings factorLoadings = new FactorLoadings();
	private final Map<Pair<Long, Long>, Matrix> d2FRET = new HashMap<Pair<Long, Long>, Matrix>();
	private final Map<Pair<Long, Long>, Matrix> d2RRET = new HashMap<Pair<Long, Long>, Matrix>();
	private Matrix FCOV;
	private Matrix RVAR;

	private long lastcalc = 0L;

	public static final AttrType RVAR_ATTR = new CalcAttrType("R:RVAR");
	public static final AttrType FRET = new CalcAttrType("R:fret");
	public static final AttrType SFRET = new CalcAttrType("R:facret");
	public static final AttrType SBFRET = new CalcAttrType("R:bfacret");
	public static final AttrType RESIDUAL_RETURN = new CalcAttrType("R:rsd_ret");
	public static final AttrType BARRA_RESIDUAL_RETURN = new CalcAttrType("R:brsd_ret");

	public FactorCalculator_OLD(UnifiedDataSource uSource, int factor_days_lookback, int num_factor_days, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.factor_days_lookback = factor_days_lookback;
		this.num_factor_days = num_factor_days;
		this.primaryExch = primaryExch;
		pCalc = new FactorLoadingCalculator(uSource, factorLoadings, num_factor_days, primaryExch);
	}

	public Set<AttrType> getFactors() {
		return CollectionUtils.toSet(factors);
	}

	// /XXX Maybe do something more sophisticated and less error prone here...
	public static boolean isBarraFactor(AttrType factor) {
		return factor.name.startsWith("F:B");
	}

	private void generateFactors(long asof, boolean barraonly) throws Exception {
		factorLoadings.init(secs);
		Vector<AttrType> factorVec = new Vector<AttrType>();
		Vector<AttrType> monitorFactorVec = new Vector<AttrType>();

		if (!barraonly) {
			factorVec.add(pCalc.calculateUni(asof));
			factorVec.add(pCalc.calculateMom(asof, factor_days_lookback, true));
			factorVec.add(pCalc.calculateVol(asof, factor_days_lookback, true));
			factorVec.addAll(pCalc.calculateSizeFacs(asof));
			factorVec.addAll(pCalc.calculateE2PFac(asof));
			factorVec.addAll(pCalc.calculateEE2PFac(asof));
			factorVec.addAll(pCalc.calculateCredit(asof));
			factorVec.add(pCalc.calculateBeta(asof, 90));
			factorVec.add(pCalc.calculateShortInterestFactor(asof));
			factorVec.addAll(pCalc.calculatePrice(asof));
			// monitorFactorVec.add(pCalc.calculateIntradayBeta(asof, 20));
			// monitorFactorVec.addAll(pCalc.calculateGICS(asof));
		}
		Pair<Set<AttrType>, Set<AttrType>> bf = pCalc.calculateBarra(asof);
		factorVec.addAll(bf.first);
		monitorFactorVec.addAll(bf.second);

		pCalc.setLastCalc(asof);
		if (lastcalc == 0L) {
			factors = factorVec.toArray(new AttrType[0]);
			monitorFactors = monitorFactorVec.toArray(new AttrType[0]);
		}
	}
	
	//XXX there is a lot functionality pushed in here, like getting returns and capitatlizations, that might be better done out of here
	private void calculateFactorAndResidualReturns(long t1, long t2, Map<Security, NavigableMap<Long, Attribute>> capMap, ReturnType rtype) throws Exception {
		log.info("Calculating factor and residual returns between " + df.format(t1) + ", " + df.format(t2));

		Matrix X = MatrixFactory.zeros(secs.length, factors.length);
		Matrix W = MatrixFactory.zeros(secs.length, secs.length);
		Matrix Y = MatrixFactory.zeros(secs.length, 1);
		Matrix M = MatrixFactory.fill(1.0, secs.length, 1);

		Set<Security> secSet = factorLoadings.getSecurities();
		Map<Security, BarTimeSeries> pMap = null;
		
		///Get intraday bars
		if (rtype == ReturnType.INTRADAY) {
			pMap = uSource.barSource.getTimeSeries(secSet, t1, t2, primaryExch);
		}
		//Get daily bars
		else if (rtype == ReturnType.DAILY || rtype == ReturnType.CLOSE2OPEN) {
			pMap = new HashMap<Security, BarTimeSeries>();
			long startdate = Time.today(t1);
			for (Map.Entry<Security, DailyBarTimeSeries> e : uSource.getDailyBarTimeSeries(secSet, startdate, t2, primaryExch).entrySet())
				pMap.put(e.getKey(), (BarTimeSeries) e.getValue());
		}
		else
			throw new RuntimeException("We should have never reached this point");

		//If needed, get a capitalization map
		Map<Security, Attribute> secondaryCapMap = null;
		if (capMap == null) {
			secondaryCapMap = uSource.attrSource.getAttrAsOf(secSet, PassThruCalculator.CAP, t1);
		}

		for (int ii = 0; ii < secs.length; ii++) {
			Security sec = secs[ii];
			BarTimeSeries dbts = pMap.get(sec);

			if (dbts == null) {
				log.warning("No timeseries for security: " + sec.getSecId());
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			//determine what logrel means in this context
			Double logrel = null;
			if (rtype == ReturnType.CLOSE2OPEN) {
				assert dbts.size() == 2;
				logrel = TimeSeriesUtil.c2oLogrel(dbts.getLag(0), dbts.getLag(1));
			}
			else {
				logrel = dbts.getLogrel();
			}
			
			if (logrel == null || logrel.isNaN()) {
				log.warning("Missing logrel for sec " + sec.getSecId() + " t1 " + df.dformat(t1) + " t2 " + df.format(t2) + " from " + dbts.printDateRange());
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			boolean have_loadings = false;
			Double loading[] = new Double[factors.length];
			for (int jj = 0; jj < factors.length; jj++) {
				double load = factorLoadings.getLoadingAsOf(sec, factors[jj], t1);
				if (Double.isNaN(load)) {
					// log.finest("Nan loading for " + factors[jj].name + " at " + df.format(t1) + " for " + sec.getSecId());
					continue;
				}
				have_loadings = true;
				loading[jj] = load;
			}
			if (!have_loadings) {
				log.warning("no loadings for sec " + sec.getSecId() + " ts: " + df.format(t1));
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			double mktcap = 1.0;
			if (CAP_WEIGHTED_FACTORS) {
				Attribute capAttr = null;
				if (capMap != null) {
					NavigableMap<Long, Attribute> secCapSeries = capMap.get(sec);
					if (secCapSeries != null) {
						Map.Entry<Long, Attribute> e = secCapSeries.floorEntry(t1);
						capAttr = e != null ? e.getValue() : null;
					}
				}
				else {
					capAttr = secondaryCapMap.get(sec);
				}

				if (capAttr != null && !Double.isNaN(capAttr.asDouble())) {
					mktcap = Math.log(capAttr.asDouble());
				}
				if (mktcap == 1.0) {
					M.setAsDouble(Double.NaN, ii, 0);
					continue;
				}
			}

			// data is good, set matrix values for this sec
			for (int jj = 0; jj < factors.length; jj++) {
				if (loading[jj] != null && !Double.isNaN(loading[jj])) {
					X.setAsDouble(loading[jj], ii, jj);
				}
			}
			Y.setAsDouble(logrel, ii, 0);
			W.setAsDouble(mktcap, ii, ii);
		}

		log.info("X " + X.getSize()[0] + " " + X.getSize()[1]);
		log.info("W " + W.getSize()[0] + " " + W.getSize()[1]);
		log.info("Y " + Y.getSize()[0] + " " + Y.getSize()[1]);
		// log.info("X: " + X.toString());
		// log.info("W: " + W.toString());
		// log.info("Y: " + Y.toString());
		// log.finest(X.transpose().mtimes(W).toString());
		// log.finest("test");
		// log.finest(X.transpose().mtimes(W).mtimes(X).toString());

		// reduce collinearity in factors using truncated svd
		Matrix[] svd = X.svd();
		Matrix U = svd[0];
		Matrix S = svd[1];
		Matrix V = svd[2];

		// log.info("U " + U.getSize()[0] + " " + U.getSize()[1]);
		// log.info("S " + S.getSize()[0] + " " + S.getSize()[1]);
		// log.info("V " + V.getSize()[0] + " " + V.getSize()[1]);

		// calculate our truncated factor loadings
		Matrix XP = U.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).mtimes(S.select(Calculation.Ret.LINK, "0-" + MAX_SVD_IDX + ";0-" + MAX_SVD_IDX));
		if (log.isLoggable(Level.FINEST)) {
			Matrix XSVD = XP.mtimes(V.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).transpose());
			log.finest("|X-XSVD| " + X.minus(XSVD).getAbsoluteValueSum());
		}
		// regress security returns on truncated factor loadings
		Matrix BP = XP.transpose().mtimes(W).mtimes(XP).pinv().mtimes(XP.transpose()).mtimes(W).mtimes(Y);
		// express truncated factor returns in the original factor space
		Matrix B = V.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).mtimes(BP);
		// calculate residual return
		Matrix E = Y.minus(X.mtimes(B)).times(M);

		// log.info("B: " + B.toString());
		// log.info("E: " + B.toString());

		
		// Output regression statistics here
		double exposureMatrixMass = Math.pow(S.getEuklideanValue(), 2);
		double truncatedExposureMatrixMass = Math.pow(S.select(Calculation.Ret.LINK, "0-" + MAX_SVD_IDX + ";0-" + MAX_SVD_IDX).getEuklideanValue(), 2);
		log.info("SVD on exposure matrix maintained " + df.fformat(100 * truncatedExposureMatrixMass / exposureMatrixMass) + "% of the matrix mass");

		double yvar = Y.times(M).var(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0);
		double evar = E.var(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0);
		double r2 = 1 - evar / yvar;
		log.info("Regression R2 = " + df.fformat(100 * r2) + "%");

		// This is a custom definition
		Matrix Wdiag = W.sqrt(Ret.LINK).mtimes(DenseDoubleMatrix2D.factory.ones(W.getSize()[0], 1));
		double wyvar = Y.times(M).minus(Y.mean(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0)).power(Ret.NEW, 2).times(Wdiag).sum(Ret.NEW, Matrix.ALL, true)
				.getAsDouble(0, 0);
		double wevar = E.minus(E.mean(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0)).power(Ret.NEW, 2).times(Wdiag).sum(Ret.NEW, Matrix.ALL, true)
				.getAsDouble(0, 0);
		double wr2 = 1 - wevar / wyvar;
		log.info("Regression WR2 = " + df.fformat(100 * wr2) + "%");
		
		Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
		d2FRET.put(tpair, B);
		d2RRET.put(tpair, E);
	}

	private static void check_fcov(Matrix FCOV) {
		log.info("FCOV Dim: " + FCOV.getRowCount() + " " + FCOV.getColumnCount());
		double mean = FCOV.getMeanValue();
		double absmean = FCOV.getAbsoluteValueMean();
		double sum = FCOV.getValueSum();
		double abssum = FCOV.getAbsoluteValueSum();
		double std = FCOV.getStdValue();
		double min = FCOV.getMinValue();
		double max = FCOV.getMaxValue();
		boolean valid = true;
		/*
		 * if (mean < 0.005 || mean > 0.015) valid = false; if (absmean < 0.010 || absmean > 0.020) valid = false; if (sum < 50 || sum > 90) valid = false;
		 */
		if (abssum > 0.40)
			valid = false;
		/*
		 * if (std < 0.02 || std > 0.04) valid = false;
		 */
		if (min < -3e-2 || max > 3e-2)
			valid = false;
		log.info("FCOV mean: " + mean + " absmean: " + absmean + " sum: " + sum + " abssum: " + abssum + " std: " + std + " min: " + min + " max: " + max);
		if (!valid) {
			log.severe("FCOV matrix with values outside of preset range, check before using/widening the bounds");
			log.severe(FCOV.toString());
			System.exit(1);
		}
	}

	private void calculateMatrices(long asof) throws Exception {
		Matrix FRET = DenseDoubleMatrix2D.factory.zeros(factors.length, num_factor_days);
		Matrix RRET = DenseDoubleMatrix2D.factory.zeros(secs.length, num_factor_days);

		// get capitalization for the entire interval
		Map<Security, NavigableMap<Long, Attribute>> capMap = uSource.attrSource.getRange(factorLoadings.getSecurities(), PassThruCalculator.CAP,
				Exchange.subtractTradingDays(asof, num_factor_days + 1, primaryExch), asof);

		// start by looking at the return to yesteday's close
		long t2 = asof;
		long t1 = Exchange.prevClose(t2, primaryExch);
		// /XXX <=num_factor_days?
		for (int lag = 0; lag < num_factor_days; lag++, t2 = t1, t1 = Exchange.prevClose(t1, primaryExch)) {
			if (lag == 0 && !Exchange.isOpen(t2, primaryExch))
				continue;

			Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
			// (lag==0 (intraday) redo it
			if (!d2FRET.containsKey(tpair) || lag == 0) {
				calculateFactorAndResidualReturns(t1, t2, capMap, ReturnType.DAILY);
			}
			
			int column = lag;
			Matrix fret = d2FRET.get(tpair);
			for (int row = 0; row < factors.length; row++) {
				FRET.setAsDouble(fret.getAsDouble(row, 0), row, column);
			}
			Matrix rret = d2RRET.get(tpair);
			for (int row = 0; row < secs.length; row++) {
				RRET.setAsDouble(rret.getAsDouble(row, 0), row, column);
			}
		}
		log.fine("FRET: " + FRET.toString());

		FCOV = ASEMath.wcov(USE_INTRADAY? FRET : FRET.deleteColumns(Ret.LINK, 0), NUM_HALFLIFE_DAYS);
		check_fcov(FCOV);

		RVAR = ASEMath.wvar(USE_INTRADAY? RRET : RRET.deleteColumns(Ret.LINK, 0), NUM_HALFLIFE_DAYS);
		//RVAR = garchRvar(RRET);

		if (log.isLoggable(Level.FINE)) {
			log.fine("factor cov for " + df.format(asof));
			for (int ii = 0; ii < factors.length; ii++) {
				log.fine(factors[ii] + " " + FCOV.getAsDouble(ii, ii));
			}
			log.fine("residual var for " + df.format(asof));
			for (int ii = 0; ii < secs.length; ii++) {
				log.fine("sec " + secs[ii] + " " + RVAR.getAsDouble(ii, 0));
			}
		}


	}

	private Matrix garchRvar(Matrix rret) {
		int n = (int) rret.getRowCount();
		int t = (int) rret.getColumnCount();
		Matrix rvar = DoubleMatrix2D.factory.zeros(n, 5);
		double alpha = 0.35;
		double beta = 0.10;
		
		for (int row = 0; row < n; row++) {
			// get mean variance
			double sum = 0;
			int count = 0;
			for (int column = 0; column < t; column++) {
				double r = rret.getAsDouble(row, column);
				if (!Double.isNaN(r)) {
					sum += r * r;
					count++;
				}
			}

			double mean = sum / count;
			double mu = mean * (1 - alpha - beta);
			double sigma2 = Double.NaN;
			double sigma2_prev = mean;
			double r_prev = Double.NaN;
			for (int column = t - 1; column >= 0; column--) {
				double r = rret.getAsDouble(row, column);
				if (Double.isNaN(r))
					continue;
				//if (Double.isNaN(r_prev)) {
				//	r_prev = r;
				//	continue;
				//}

				//sigma2 = mu + alpha * sigma2_prev + beta * r_prev * r_prev;
				sigma2 = mu + alpha * sigma2_prev + beta * r * r;
				sigma2_prev = sigma2;
				//r_prev = r;
			}

			log.info("GARCH for security " + secs[row] +", mean="+mean+", sigma2="+sigma2);
			
			double[] sigma2forecast = new double[5];
			for (int ii = 0; ii < 5; ii++) {
				sigma2forecast[ii] = mean + Math.pow(alpha + beta, ii) * (sigma2 - mean);
			}
			for (int ii = 0; ii < 5; ii++) {
				rvar.setAsDouble(sigma2forecast[ii], row, ii);
			}
		}

		return rvar;
	}
	private void calculateAndRecordSecurityFactorReturns(CalcResults cr, long asof) {
		long t2 = asof;
		long t1 = Exchange.prevClose(t2, primaryExch);
		for (int lag = 0; lag < NUM_FACTOR_DAYS_TO_RECORD; lag++, t2 = t1, t1 = Exchange.prevClose(t1, primaryExch)) {
			if (lag == 0 && !Exchange.isOpen(t2, primaryExch))
				continue;

			AttrType attr = lattr(SFRET, lag - 1);
			AttrType battr = lattr(SBFRET, lag - 1);
			log.info("Calculating attributes: " + attr);

			Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
			int nofaccnt = 0;
			for (Security sec : factorLoadings.getSecurities()) {
				double facret = 0.0;
				double bfacret = 0.0;

				for (int ii = 0; ii < factors.length; ii++) {
					double latestloading = factorLoadings.getLoadingAsOf(sec, factors[ii], t2);
					if (Double.isNaN(latestloading)) {
						// log.finest("No factor loading for " + sec.getSecId() + " " + factors[ii].name + " as of " + df.format(t2));
						continue;
					}
					if (d2FRET.get(tpair) == null) {
						log.warning("No factor return found for between " + df.format(tpair.first) + " / " + df.format(tpair.second));
						continue;
					}
					double v = latestloading * d2FRET.get(tpair).getAsDouble(ii, 0);
					facret += v;
					if (isBarraFactor(factors[ii])) {
						bfacret += v;
					}

				}
				if (!(Math.abs(facret) > 0.0)) {
					log.severe("No factor returns (" + facret + ") calculated for " + sec + " between " + df.format(tpair.first) + " / "
							+ df.format(tpair.second));
					nofaccnt++;
					continue;
				}
				cr.add(sec, attr, asof, facret);
				cr.add(sec, battr, asof, bfacret);
			}
			if (nofaccnt > 0)
				log.warning("Missing " + attr.name + " on " + nofaccnt + " securities!");
		}
	}

	private void recordSecurityResidualReturns(CalcResults cr, long asof) {
		log.info("Calculating attributes: " + RESIDUAL_RETURN.name + " and " + BARRA_RESIDUAL_RETURN.name);

		for (int lag = 0; lag < NUM_FACTOR_DAYS_TO_RECORD; lag++) {
			Map<Security, Attribute> secRet = cr.getResult(DailyPriceCalculator.lattr(DailyPriceCalculator.C2C, lag - 1));
			Map<Security, Attribute> secFacret = cr.getResult(lattr(SFRET, lag - 1));
			Map<Security, Attribute> secBarraFacret = cr.getResult(lattr(SBFRET, lag - 1));

			for (Security sec : secFacret.keySet()) {
				Attribute ret = secRet.get(sec);
				Attribute facret = secFacret.get(sec);
				Attribute barraFacret = secBarraFacret.get(sec);

				if (ret == null) {
					log.warning("No return in calcres file for sec " + sec.getSecId() + " and lag=" + lag);
					continue;
				}

				if (facret != null) {
					cr.add(sec, lattr(RESIDUAL_RETURN, lag - 1), asof, ret.asDouble() - facret.asDouble());
				}
				else {
					log.warning("No factor return in calcres file for sec " + sec.getSecId() + " and lag=" + lag);
				}

				if (facret != null) {
					cr.add(sec, lattr(BARRA_RESIDUAL_RETURN, lag - 1), asof, ret.asDouble() - barraFacret.asDouble());
				}
				else {
					log.warning("No factor return in calcres file for sec " + sec.getSecId() + " and lag=" + lag);
				}
			}
		}
	}

	private void recordFCOV(Matrix FCOV, CalcResults cr) {
		for (int ii = 0; ii < factors.length; ii++) {
			for (int jj = ii; jj < factors.length; jj++) {
				cr.addFactorCov(factors[ii], factors[jj], FCOV.getAsDouble(ii, jj));
			}
		}
	}

	private void recordFactorReturns(CalcResults cr) {
		//Get the last day
		Vector<Pair<Long, Long>> intervals = new Vector<Pair<Long,Long>>();
		intervals.addAll(d2FRET.keySet());
		Collections.sort(intervals);
		Pair<Long, Long> lastP = intervals.lastElement();
		Matrix lastM = d2FRET.get(lastP);
		
		for (int ii = 0; ii < factors.length; ii++) {
			AttrType attr = new CalcAttrType(FRET.name + "_" + factors[ii], FRET.datatype);
			cr.addFactorReturn(attr, lastP.second, lastM.getAsDouble(ii, 0));
		}
	}

	private void recordResidualVars(CalcResults cr, long asof) {
		for (int ii = 0; ii < secs.length; ii++) {
			Double value = RVAR.getAsDouble(ii, 0);
			if (!Double.isNaN(value) && value != 0.0) {
				cr.add(secs[ii], RVAR_ATTR, asof, value);
			}
		}
	}

	public double getResidualReturn(Security sec, long t1, long t2) {
		Matrix RRET = d2RRET.get(new Pair<Long, Long>(t1, t2));
		if (RRET == null) {
			return Double.NaN;
		}
		return RRET.getAsDouble(Arrays.binarySearch(secs, sec), 0);
	}

	public void calculate(CalcResults cr, Set<Security> secset, long asof) throws Exception {
		log.info("Calculating Factors on " + secset.size() + " securitites as of " + df.format(asof));
		secs = (Security[]) secset.toArray(new Security[0]);
		Arrays.sort(secs);

		// XXX should think of a way to cache this information across days given the changing universe
		if (Time.midnight(asof) != Time.midnight(lastcalc)) {
			d2FRET.clear();
			d2RRET.clear();
		}

		generateFactors(asof, false);
		calculateMatrices(asof);

		factorLoadings.record(cr, asof);
		recordFCOV(FCOV, cr);
		calculateAndRecordSecurityFactorReturns(cr, asof);
		recordFactorReturns(cr);
		recordResidualVars(cr, asof);
		recordSecurityResidualReturns(cr, asof);

		FCOV = null;
		RVAR = null;

		lastcalc = asof;
	}

	//XXX if you want cap map computed internally, pass a null
	public Map<Security, Attribute> calculateFitResults(Set<Security> secset, long t1, long t2, AttrType attrType, boolean barraonly,
			ReturnType rtype, Map<Security, NavigableMap<Long, Attribute>> capMap) throws Exception {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>(secset.size());
		secs = (Security[]) secset.toArray(new Security[0]);
		Arrays.sort(secs);

		if (barraonly)
			MAX_SVD_IDX = 69;
		else
			MAX_SVD_IDX = 79;

		// XXX should think of a way to cache this information across days given the changing universe
		d2FRET.clear();
		d2RRET.clear();

		//XXX If this was run the first time with barraOnly = false, rerunning again with barraOnly = true will still keep around the non-barra factors
		//XXX To fix we need to follow this function and repopulate the factor vector every time rather only when lastCalc = 0.
		//XXX Not so fast! Bacause many calculators for factorLoadings return a null if they didn't recompute
		generateFactors(t1, barraonly);
		calculateFactorAndResidualReturns(t1, t2, capMap, rtype);

		for (Security sec : secset) {
			double ret = getResidualReturn(sec, t1, t2);
			if (Double.isNaN(ret)) {
				log.warning("Could not calculate residual return on: " + sec);
				continue;
			}
			res.put(sec, new NumericAttribute(attrType, sec, t1, ret, t1));
		}

		FCOV = null;
		RVAR = null;

		lastcalc = t1;

		return res;
	}

	public static AttrType lattr(AttrType attr, int lag) {
		if (lag == -1) {
			return new CalcAttrType(attr.name + "C");
		}
		return new CalcAttrType(attr.name + lag);
	}
}
