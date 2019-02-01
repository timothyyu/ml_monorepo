package ase.calculator;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.apache.commons.math.linear.EigenDecompositionImpl;
import org.ujmp.core.Matrix;
import org.ujmp.core.calculation.Calculation;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DenseDoubleMatrix2D;
import org.ujmp.core.doublematrix.DoubleMatrix2D;
import org.ujmp.core.doublematrix.SparseDoubleMatrix2D;
import org.ujmp.core.doublematrix.calculation.general.decomposition.Eig;
import org.ujmp.core.doublematrix.calculation.general.missingvalues.Impute.ImputationMethod;
import org.ujmp.core.doublematrix.impl.BlockDenseDoubleMatrix2D;

import ase.data.AttrType;
import ase.data.AttrType.Type;
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

public class FactorCalculator_EXP extends Calculator {
	private static final Logger log = LoggerFactory.getLogger(FactorCalculator_EXP.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static enum ReturnType {
		DAILY, INTRADAY, CLOSE2OPEN
	};

	private static final boolean CAP_WEIGHTED_FACTORS = true;
	private static final boolean USE_INTRADAY = true;

	private static final int SVD_FACTORS = 2;
	private static final int SVD_FACTOR_DAYS = 30;
	private static final boolean SVD_INTRADAY_EXPOSURES = USE_INTRADAY;

	private static final int NUM_HALFLIFE_DAYS = 45;
	private static final int NUM_FACTOR_DAYS_TO_RECORD = 3;

	private static int __REGULAR_MAX_SVD_IDX__ = 81;
	private static int __BARRA_MAX_SVD_IDX__ = 69;
	private static int MAX_SVD_IDX = __REGULAR_MAX_SVD_IDX__;

	private final UnifiedDataSource uSource;
	private final FactorLoadingCalculator pCalc;

	private final int factor_days_lookback;
	private final int num_factor_days;
	private final Exchange.Type primaryExch;

	private Security[] secs;
	private AttrType[] fundamentalFactors;
	private AttrType[] monitorFactors;
	private AttrType[] svdFactors;
	private AttrType[] allFactors;
	private FactorLoadings factorLoadings = new FactorLoadings();
	private final Map<Pair<Long, Long>, Matrix> d2FundmentalFactorRet = new HashMap<Pair<Long, Long>, Matrix>();
	private final Map<Pair<Long, Long>, Matrix> d2FundamentalResidualRet = new HashMap<Pair<Long, Long>, Matrix>();
	private final Map<Pair<Long, Long>, Matrix> d2SvdFactorRet = new HashMap<Pair<Long, Long>, Matrix>();
	private final Map<Pair<Long, Long>, Matrix> d2TotalResidualRet = new HashMap<Pair<Long, Long>, Matrix>();

	private Matrix svdDirectionBootstrap = null;

	private Matrix FCOV;
	private Matrix RVAR;

	private long lastcalc = 0L;

	public static final AttrType RVAR_ATTR = new CalcAttrType("R:RVAR");
	public static final AttrType FRET_ATTR = new CalcAttrType("R:fret");
	public static final AttrType SFRET_ATTR = new CalcAttrType("R:facret");
	public static final AttrType SBFRET_ATTR = new CalcAttrType("R:bfacret");
	public static final AttrType RESIDUAL_RETURN = new CalcAttrType("R:rsd_ret");
	public static final AttrType BARRA_RESIDUAL_RETURN = new CalcAttrType("R:brsd_ret");

	public FactorCalculator_EXP(UnifiedDataSource uSource, int factor_days_lookback, int num_factor_days, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.factor_days_lookback = factor_days_lookback;
		this.num_factor_days = num_factor_days;
		this.primaryExch = primaryExch;
		pCalc = new FactorLoadingCalculator(uSource, factorLoadings, num_factor_days, primaryExch);
	}

	// /XXX Maybe do something more sophisticated and less error prone here...
	public static boolean isBarraFactor(AttrType factor) {
		return factor.name.startsWith("F:B");
	}

	// ///////////////////////////////////////////////////////////////////////////////////////
	// CALCULATING FACTOR LOADINGS
	// //////////////////////////////////////////////////////////////////////////////////////

	private void generateFactors(long asof, boolean barraonly) throws Exception {
		// XXX maybe move this to calculate, where more clearing takes place?
		if (Time.today(asof) != Time.today(lastcalc)) {
			factorLoadings.reset();
		}
		factorLoadings.init(secs);
		Vector<AttrType> fundFactorVec = new Vector<AttrType>();
		Vector<AttrType> monitorFactorVec = new Vector<AttrType>();

		if (!barraonly) {
			fundFactorVec.add(pCalc.calculateUni(asof));
			fundFactorVec.add(pCalc.calculateMom(asof, factor_days_lookback, true));
			fundFactorVec.add(pCalc.calculateVol(asof, factor_days_lookback, true));
			fundFactorVec.addAll(pCalc.calculateSizeFacs(asof));
			fundFactorVec.addAll(pCalc.calculateE2PFac(asof));
			fundFactorVec.addAll(pCalc.calculateEE2PFac(asof));
			fundFactorVec.addAll(pCalc.calculateCredit(asof));
			fundFactorVec.add(pCalc.calculateBeta(asof, 90));
			fundFactorVec.add(pCalc.calculateShortInterestFactor(asof));
			fundFactorVec.addAll(pCalc.calculatePrice(asof));
			// monitorFactorVec.add(pCalc.calculateIntradayBeta(asof, 20));
			// monitorFactorVec.addAll(pCalc.calculateGICS(asof));
			monitorFactorVec.addAll(pCalc.calculateForecastFactors(asof));
		}
		Pair<Set<AttrType>, Set<AttrType>> bf = pCalc.calculateBarra(asof);
		fundFactorVec.addAll(bf.first);
		monitorFactorVec.addAll(bf.second);

		pCalc.setLastCalc(asof);
		if (lastcalc == 0L) {
			fundamentalFactors = fundFactorVec.toArray(new AttrType[0]);
			monitorFactors = monitorFactorVec.toArray(new AttrType[0]);

			// XXX Svd factor loadings have to be computed as part of the application of the svd model
			// XXX note that we have set them as monitor factors
			svdFactors = new AttrType[SVD_FACTORS];
			for (int ii = 0; ii < SVD_FACTORS; ii++)
				svdFactors[ii] = new CalcAttrType(FactorLoadings.MONITOR_FACTOR_PREFIX + "SVD" + (ii + 1), Type.N);

			Vector<AttrType> allFactorVec = new Vector<AttrType>();
			allFactorVec.addAll(fundFactorVec);
			allFactorVec.addAll(Arrays.asList(svdFactors));
			allFactors = allFactorVec.toArray(new AttrType[0]);
		}
	}

	// ///////////////////////////////////////////////////////////////////////////////////////
	// FUNDAMENTAL FACTOR MODEL
	// //////////////////////////////////////////////////////////////////////////////////////

	private void calculateFundamental_GetLoadings(long t1, Matrix X, Matrix M) {
		assert X.getSize()[0] == secs.length && X.getSize()[1] == fundamentalFactors.length;
		assert M.getSize()[0] == secs.length && M.getSize()[1] == 1;

		for (int ii = 0; ii < secs.length; ii++) {
			if (Double.isNaN(M.getAsDouble(ii, 0)))
				continue;
			Security sec = secs[ii];

			boolean have_loadings = false;
			Double loading[] = new Double[fundamentalFactors.length];
			for (int jj = 0; jj < fundamentalFactors.length; jj++) {
				double load = factorLoadings.getLoadingAsOf(sec, fundamentalFactors[jj], t1);
				if (Double.isNaN(load)) {
					// log.finest("Nan loading for " + factors[jj].name + " at " + df.format(t1) + " for " + sec.getSecId());
					continue;
				}
				have_loadings = true;
				loading[jj] = load;
			}
			if (!have_loadings) {
				log.warning("No loadings for sec " + sec.getSecId() + " ts: " + df.format(t1));
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			// data is good, set matrix values for this sec
			for (int jj = 0; jj < fundamentalFactors.length; jj++) {
				if (loading[jj] != null && !Double.isNaN(loading[jj])) {
					X.setAsDouble(loading[jj], ii, jj);
				}
			}
		}
	}

	private void calculateFundamental_GetRegressionWeights(long t1, Map<Security, NavigableMap<Long, Attribute>> capMap, Matrix W, Matrix M) throws Exception {
		Map<Security, Attribute> cm = new HashMap<Security, Attribute>(secs.length);
		for (Map.Entry<Security, NavigableMap<Long, Attribute>> e1 : capMap.entrySet()) {
			Map.Entry<Long, Attribute> e2 = e1.getValue().floorEntry(t1);
			if (e2 != null) {
				cm.put(e1.getKey(), e2.getValue());
			}
		}
		calculateFundamental_GetRegressionWeights(cm, W, M);
	}

	private void calculateFundamental_GetRegressionWeights(long t1, Matrix W, Matrix M) throws Exception {
		log.info("Getting capitalization as of " + df.debugFormat(t1));
		Map<Security, Attribute> capMap = uSource.attrSource.getAttrAsOf(CollectionUtils.toSet(secs), PassThruCalculator.CAP, t1);
		calculateFundamental_GetRegressionWeights(capMap, W, M);
	}

	private void calculateFundamental_GetRegressionWeights(Map<Security, Attribute> cap, Matrix W, Matrix M) {
		assert W.getSize()[0] == secs.length && W.getSize()[1] == secs.length;
		assert M.getSize()[0] == secs.length && M.getSize()[1] == 1;

		double minw = Double.MAX_VALUE;
		for (int ii = 0; ii < secs.length; ii++) {
			if (Double.isNaN(M.getAsDouble(ii, 0)))
				continue;
			Security sec = secs[ii];
			Attribute c = cap.get(sec);
			if (c == null || Double.isNaN(c.asDouble())) {
				log.info("No capitalization info found for secid " + sec.getSecId());
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}
			double weight = Math.log(c.asDouble());
			minw = Math.min(weight, minw);
			W.setAsDouble(weight, ii, ii);
		}

		// normalize weights
		// for (int ii = 0; ii < secs.length; ii++) {
		// if (Double.isNaN(M.getAsDouble(ii, 0)))
		// continue;
		// else
		// W.setAsDouble(W.getAsDouble(ii, ii) - minw + 1, ii, ii);
		// }
	}

	private void calculateFundamental_GetReturns(long t1, long t2, ReturnType rtype, Matrix Y, Matrix M) throws Exception {
		log.info("Getting raw returns for range [" + df.debugFormat(t1) + ", " + df.debugFormat(t2) + "], type = " + rtype);
		assert Y.getSize()[0] == secs.length && Y.getSize()[1] == 1;
		assert M.getSize()[0] == secs.length && M.getSize()[1] == 1;

		Map<Security, BarTimeSeries> pMap = null;
		// /Get intraday bars
		if (rtype == ReturnType.INTRADAY) {
			pMap = uSource.barSource.getTimeSeries(CollectionUtils.toSet(secs), t1, t2, primaryExch);
		}
		// Get daily bars
		else if (rtype == ReturnType.DAILY || rtype == ReturnType.CLOSE2OPEN) {
			pMap = new HashMap<Security, BarTimeSeries>();
			long startdate = Time.today(t1);
			for (Map.Entry<Security, DailyBarTimeSeries> e : uSource.getDailyBarTimeSeries(CollectionUtils.toSet(secs), startdate, t2, primaryExch).entrySet())
				pMap.put(e.getKey(), (BarTimeSeries) e.getValue());
		}
		else
			throw new RuntimeException("We should have never reached this point");

		for (int ii = 0; ii < secs.length; ii++) {
			if (Double.isNaN(M.getAsDouble(ii, 0)))
				continue;

			Security sec = secs[ii];
			BarTimeSeries bts = pMap.get(sec);

			if (bts == null) {
				log.warning("No timeseries for security: " + sec.getSecId());
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			// determine what logrel means in this context
			Double logrel = null;
			if (rtype == ReturnType.CLOSE2OPEN) {
				assert bts.size() == 2;
				logrel = TimeSeriesUtil.c2oLogrel(bts.getLag(0), bts.getLag(1));
			}
			else {
				logrel = bts.getLogrel();
			}

			if (logrel == null || logrel.isNaN()) {
				log.warning("Missing logrel for sec " + sec.getSecId() + " t1 " + df.dformat(t1) + " t2 " + df.format(t2) + " from " + bts.printDateRange());
				M.setAsDouble(Double.NaN, ii, 0);
				continue;
			}

			Y.setAsDouble(logrel, ii, 0);
		}
	}

	private Pair<Matrix, Matrix> calculateFundamental_Regress(Matrix X, Matrix W, Matrix Y, Matrix M) {
		Collection<Integer> badSecs = new HashSet<Integer>();
		for (int ii = 0; ii < secs.length; ii++)
			if (Double.isNaN(M.getAsDouble(ii, 0)))
				badSecs.add(ii);

		// Exclude rows that correspond to bad secs
		Matrix Xt = X.deleteRows(Ret.LINK, badSecs);
		Matrix Wt = W.delete(Ret.LINK, badSecs, badSecs);
		Matrix Yt = Y.deleteRows(Ret.LINK, badSecs);

		log.info("X: " + X.getSize()[0] + "x" + X.getSize()[1] + ", Xt: " + Xt.getSize()[0] + "x" + Xt.getSize()[1]);
		log.info("W: " + W.getSize()[0] + "x" + W.getSize()[1] + ", Wt: " + Wt.getSize()[0] + "x" + Wt.getSize()[1]);
		log.info("Y: " + Y.getSize()[0] + "x" + Y.getSize()[1] + ", Yt: " + Yt.getSize()[0] + "x" + Yt.getSize()[1]);

		// reduce collinearity in factors using truncated svd
		Matrix[] svd = Xt.svd();
		Matrix U = svd[0];
		Matrix S = svd[1];
		Matrix V = svd[2];

		// calculate our truncated factor loadings
		Matrix XPt = U.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).mtimes(S.select(Calculation.Ret.LINK, "0-" + MAX_SVD_IDX + ";0-" + MAX_SVD_IDX));
		if (log.isLoggable(Level.FINEST)) {
			Matrix XSVD = XPt.mtimes(V.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).transpose());
			log.finest("|X-XSVD| " + Xt.minus(XSVD).getAbsoluteValueSum());
		}
		// regress security returns on truncated factor loadings
		// ORIG: Matrix BP = XPt.transpose().mtimes(Wt).mtimes(XPt).pinv().mtimes(XPt.transpose()).mtimes(Wt).mtimes(Yt);
		Matrix temp = XPt.transpose().mtimes(Wt);
		Matrix BP = temp.mtimes(XPt).pinv().mtimes(temp).mtimes(Yt);
		// express truncated factor returns in the original factor space
		Matrix B = V.select(Calculation.Ret.LINK, "*;0-" + MAX_SVD_IDX).mtimes(BP);
		// calculate residual return (note that this is on the full, not truncated matrices. entries for bad secs will get a nan
		Matrix E = Y.minus(X.mtimes(B)).times(M);

		// Output regression statistics here
		double exposureMatrixMass = Math.pow(S.getEuklideanValue(), 2);
		double truncatedExposureMatrixMass = Math.pow(S.select(Calculation.Ret.LINK, "0-" + MAX_SVD_IDX + ";0-" + MAX_SVD_IDX).getEuklideanValue(), 2);
		log.info("SVD on exposure matrix maintained " + df.fformat(100 * truncatedExposureMatrixMass / exposureMatrixMass) + "% of the matrix mass");

		double yvar = Y.times(M).var(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0);
		double evar = E.var(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0);
		double r2 = 1 - evar / yvar;
		log.info("Regression R2 = " + df.fformat(100 * r2) + "%");

		// This is a custom definition
		// XXX Disable this until it can be made faster (took 400ms on last count)
		// Matrix Wdiag = W.sqrt(Ret.NEW).mtimes(DenseDoubleMatrix2D.factory.ones(W.getSize()[0], 1));
		// double wyvar = Y.times(M).minus(Y.mean(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0)).power(Ret.NEW, 2).times(Wdiag).sum(Ret.NEW, Matrix.ALL, true)
		// .getAsDouble(0, 0);
		// double wevar = E.minus(E.mean(Ret.NEW, Matrix.ALL, true).getAsDouble(0, 0)).power(Ret.NEW, 2).times(Wdiag).sum(Ret.NEW, Matrix.ALL, true)
		// .getAsDouble(0, 0);
		// double wr2 = 1 - wevar / wyvar;
		// log.info("Regression WR2 = " + df.fformat(100 * wr2) + "%");

		return new Pair<Matrix, Matrix>(B, E);
	}

	private void calculateFundamentalModel(long t1, long t2, Map<Security, NavigableMap<Long, Attribute>> capMap, ReturnType rtype) throws Exception {
		log.info("Calculating factor and residual returns between " + df.format(t1) + ", " + df.format(t2));

		Matrix X = BlockDenseDoubleMatrix2D.factory.zeros(secs.length, fundamentalFactors.length);
		Matrix W = SparseDoubleMatrix2D.factory.eye(secs.length, secs.length);
		Matrix Y = DenseDoubleMatrix2D.factory.zeros(secs.length, 1);
		Matrix M = DenseDoubleMatrix2D.factory.ones(secs.length, 1);

		calculateFundamental_GetReturns(t1, t2, rtype, Y, M);
		if (CAP_WEIGHTED_FACTORS) {
			if (capMap != null)
				calculateFundamental_GetRegressionWeights(t1, capMap, W, M);
			else
				calculateFundamental_GetRegressionWeights(t1, W, M);
		}
		calculateFundamental_GetLoadings(t1, X, M);
		Pair<Matrix, Matrix> result = calculateFundamental_Regress(X, W, Y, M);

		Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
		d2FundmentalFactorRet.put(tpair, result.first);
		d2FundamentalResidualRet.put(tpair, result.second);
	}

	// ///////////////////////////////////////////////////////////////////////////////////////
	// SVD FACTOR MODEL
	// //////////////////////////////////////////////////////////////////////////////////////

	private void calculateSvdModel(long t1, long t2, int lag, Matrix FRRET) {
		log.info("Applying svd model on lag = " + lag + ", or [" + df.debugFormat(t1) + ", " + df.debugFormat(t2) + "]");
		// First the tricky part determining which is the range that we need to operate on given that lag in [0, num_factor_days].
		int relevantColumn;
		int lagStart;
		int lagEnd;

		if (lag < num_factor_days - SVD_FACTOR_DAYS) {
			relevantColumn = 0;
			lagStart = lag;
			lagEnd = lag + SVD_FACTOR_DAYS - 1;
		}
		else {
			relevantColumn = lag - (num_factor_days - SVD_FACTOR_DAYS);
			lagStart = num_factor_days - SVD_FACTOR_DAYS;
			lagEnd = num_factor_days - 1;
		}

		Matrix subMatrix = FRRET.select(Ret.LINK, "*;" + lagStart + "-" + lagEnd);
		Matrix imputedSubMatrix = subMatrix.impute(Ret.NEW, ImputationMethod.Zero);

		// Since ujmp cannot apply svd to matrices with missing values (NaNs), we substitute them with zero
		log.info("Fundamental residual return submatrix contains " + FRRET.countMissing(Ret.LINK, Matrix.ALL) + "/" + (FRRET.getSize()[0] * FRRET.getSize()[1])
				+ " missing values. Substituting with zeros for svd model.");

		Matrix[] svd = imputedSubMatrix.svd();
		Matrix U = svd[0];
		Matrix S = svd[1];
		Matrix V = svd[2];

		// NxF matrix of exposures (e.g., 1500x2)
		Matrix SecSvdFactorExp = U.select(Ret.NEW, "*;0-" + (SVD_FACTORS - 1));
		// XXX exposures are typically going to be small values. Let w_i be the exposure of sec i. As the exposures vectors are normalized to sum up to 1, we
		// have that the std of the exposures is 1/sqrt(n), where we assume that mean(w_i)=0 and n is the number of securities (var=norm(w)^2/n)=1/n =>
		// std=1/sqrt(n). Hense, we normalize exposures by multiplying with sqrt(secs.length). Similarly we will need to divide the factor returns with the same
		// figure.
		double mult = Math.sqrt(secs.length);
		SecSvdFactorExp = SecSvdFactorExp.times(Ret.NEW, false, mult);

		// Fx1 matrix of factor returns at lag
		Matrix SvdFactorRet = S.select(Ret.LINK, "0-" + (SVD_FACTORS - 1) + ";0-" + (SVD_FACTORS - 1)).mtimes(
				V.transpose().select(Ret.LINK, "0-" + (SVD_FACTORS - 1) + ";" + relevantColumn));
		SvdFactorRet = SvdFactorRet.divide(Ret.NEW, false, mult);

		// Consecutive iterations of the svd algorithm, for different days can give column vectors of U that point to opposite directions. bootstrap using the
		// lag=0 vector
		double[] adj = new double[SVD_FACTORS];
		if (lag == 0 && svdDirectionBootstrap == null) {
			svdDirectionBootstrap = SecSvdFactorExp;
		}
		else {
			for (int ii = 0; ii < SVD_FACTORS; ii++) {
				double phi = svdDirectionBootstrap.selectColumns(Ret.LINK, ii).transpose(Ret.LINK).mtimes(SecSvdFactorExp.selectColumns(Ret.LINK, ii))
						.getAsDouble(0, 0);
				adj[ii] = Math.signum(phi);
				SecSvdFactorExp.selectColumns(Ret.LINK, ii).times(Ret.ORIG, false, adj[ii]);
				SvdFactorRet.selectRows(Ret.LINK, ii).times(Ret.ORIG, false, adj[ii]);
			}
		}

		// Nx1 matrix of residual residual-returns
		// XXX note how we subtract from the non-imputed matrix, so that entries with nan, remain nan
		Matrix ResResReturns = subMatrix.selectColumns(Ret.LINK, relevantColumn).minus(SecSvdFactorExp.mtimes(SvdFactorRet));

		// STATISTICS
		double[] eigenPower = new double[SVD_FACTOR_DAYS];
		double cumEigenPower = 0;
		for (int ii = 0; ii < SVD_FACTOR_DAYS; ii++) {
			double e = S.getAsDouble(ii, ii);
			eigenPower[ii] = e * e;
			cumEigenPower += eigenPower[ii];
		}
		for (int ii = 0; ii < SVD_FACTOR_DAYS; ii++) {
			log.info("Covariance matrix eigen " + ii + ": " + df.fformat(100 * eigenPower[ii] / cumEigenPower) + "%");
		}

		Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);

		d2SvdFactorRet.put(tpair, SvdFactorRet);
		d2TotalResidualRet.put(tpair, ResResReturns);

		// store factor loadings
		if (lag > 0 || SVD_INTRADAY_EXPOSURES) {
			for (int jj = 0; jj < svdFactors.length; jj++) {
				for (int ii = 0; ii < secs.length; ii++)
					factorLoadings.setFactor(secs[ii], svdFactors[jj], t2, SecSvdFactorExp.getAsDouble(ii, jj));
			}
		}
	}

	// ///////////////////////////////////////////////////////////////////////////////////////
	// PCA FACTOR MODEL
	// //////////////////////////////////////////////////////////////////////////////////////

	private void calculatePcaModel(long t1, long t2, int lag, Matrix FRRET) {
		log.info("Applying pca model on lag = " + lag + ", or [" + df.debugFormat(t1) + ", " + df.debugFormat(t2) + "]");
		// First the tricky part determining which is the range that we need to operate on given that lag in [0, num_factor_days].
		int relevantColumn;
		int lagStart;
		int lagEnd;

		if (lag < num_factor_days - SVD_FACTOR_DAYS) {
			relevantColumn = 0;
			lagStart = lag;
			lagEnd = lag + SVD_FACTOR_DAYS - 1;
		}
		else {
			relevantColumn = lag - (num_factor_days - SVD_FACTOR_DAYS);
			lagStart = num_factor_days - SVD_FACTOR_DAYS;
			lagEnd = num_factor_days - 1;
		}

		Matrix subMatrix = FRRET.select(Ret.NEW, "*;" + lagStart + "-" + lagEnd);
		// standardize and impute
		for (int ii = 0; ii < subMatrix.getSize(0); ii++) {
			double sum = 0;
			double sum2 = 0;
			double cnt = 0;
			for (int jj = 0; jj < subMatrix.getSize(1); jj++) {
				double x = subMatrix.getAsDouble(ii, jj);
				if (Double.isNaN(x))
					continue;
				sum += x;
				sum2 += x * x;
				cnt++;
			}

			double mean = sum / cnt;
			double std = Math.sqrt(sum2 / cnt - mean * mean);

			for (int jj = 0; jj < subMatrix.getSize(1); jj++) {
				double x = subMatrix.getAsDouble(ii, jj);
				x = (x - mean) / std;
				if (Double.isNaN(x))
					x = 0.0;

				subMatrix.setAsDouble(x, ii, jj);
			}
		}

		Matrix corrMatrix = subMatrix.mtimes(subMatrix.transpose()).divide(SVD_FACTOR_DAYS);
		
		double asum = 0;
		double sum = 0;
		double cnt = 0;
		for (int ii = 0; ii < corrMatrix.getSize(0); ii++)
			for (int jj = ii + 1; jj < corrMatrix.getSize(1); jj++) {
				double x = corrMatrix.getAsDouble(ii, jj);
				sum += x;
				asum += Math.abs(x);
				cnt++;
			}

		log.info("Mean correlation: " + sum / cnt);
		log.info("Mean abs correlation: " + asum / cnt);
		
		Matrix[] svd = subMatrix.svd();
		Matrix U = svd[0];
		Matrix S = svd[1];
		Matrix D = S.power(Ret.NEW, 2.0).divide(Ret.ORIG, true, SVD_FACTOR_DAYS);
//		log.info("U: " + U.getSize(0) + "x" + U.getSize(1));
//		log.info("D: " + D.getSize(0) + "x" + D.getSize(1));

		for (int ii = 0; ii < D.getSize(0); ii++)
			log.info("Correlation matrix eig " + ii + " = " + D.getAsDouble(ii, ii));
	}

	// ///////////////////////////////////////////////////////////////////////////////////////
	// CALCULATING AND ORGANIZING THE WORKFLOW
	// //////////////////////////////////////////////////////////////////////////////////////

	private void calculateMatrices(long asof) throws Exception {
		// Residual returns to the fundamental model
		Matrix FRRET = DenseDoubleMatrix2D.factory.zeros(secs.length, num_factor_days);
		// fundemental factor returns
		Matrix FFRET = DenseDoubleMatrix2D.factory.zeros(fundamentalFactors.length, num_factor_days);
		// total residual returns, after applying the svd model
		Matrix TRRET = DenseDoubleMatrix2D.factory.zeros(secs.length, num_factor_days);
		// total factor returns, including both fundamental factors (rows 0..fund_factors-1) and svd factors (rows fund_factors..fund_factors+svd_factors)
		Matrix TFRET = DenseDoubleMatrix2D.factory.zeros(allFactors.length, num_factor_days);

		// get capitalization for the entire interval
		Map<Security, NavigableMap<Long, Attribute>> capMap = uSource.attrSource.getRange(factorLoadings.getSecurities(), PassThruCalculator.CAP,
				Exchange.subtractTradingDays(asof, num_factor_days + 1, primaryExch), asof);

		// STEP1: APPLY THE FUNDAMENTAL FACTOR MODEL

		// start by looking at the return to yesteday's close
		long t2 = asof;
		long t1 = Exchange.prevClose(t2, primaryExch);
		for (int lag = 0; lag < num_factor_days; lag++, t2 = t1, t1 = Exchange.prevClose(t1, primaryExch)) {
			if (lag == 0 && !Exchange.isOpen(t2, primaryExch))
				continue;

			Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
			// (lag==0 (intraday) redo it
			if (!d2FundmentalFactorRet.containsKey(tpair) || lag == 0) {
				calculateFundamentalModel(t1, t2, capMap, ReturnType.DAILY);
			}

			int column = lag;
			Matrix ffret = d2FundmentalFactorRet.get(tpair);
			for (int row = 0; row < fundamentalFactors.length; row++) {
				TFRET.setAsDouble(ffret.getAsDouble(row, 0), row, column);
				FFRET.setAsDouble(ffret.getAsDouble(row, 0), row, column);
			}
			Matrix frret = d2FundamentalResidualRet.get(tpair);
			for (int row = 0; row < secs.length; row++) {
				FRRET.setAsDouble(frret.getAsDouble(row, 0), row, column);
			}
		}

		// covarianceStats(FRRET, "Fundamental Residual Return Matrix");

		// STEP2: APPLY THE PCA MODEL
		if (SVD_FACTORS > 0) {
			// start by looking at the return to yesteday's close
			t2 = asof;
			t1 = Exchange.prevClose(t2, primaryExch);
			for (int lag = 0; lag < num_factor_days; lag++, t2 = t1, t1 = Exchange.prevClose(t1, primaryExch)) {
				if (lag == 0 && !Exchange.isOpen(t2, primaryExch))
					continue;

				Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
				// (lag==0 (intraday) redo it
				if (!d2SvdFactorRet.containsKey(tpair) || lag == 0) {
					calculateSvdModel(t1, t2, lag, FRRET);
					calculatePcaModel(t1, t2, lag, FRRET);
				}

				int column = lag;
				Matrix fret = d2SvdFactorRet.get(tpair);
				for (int row = 0; row < SVD_FACTORS; row++) {
					TFRET.setAsDouble(fret.getAsDouble(row, 0), fundamentalFactors.length + row, column);
				}
				Matrix rret = d2TotalResidualRet.get(tpair);
				for (int row = 0; row < secs.length; row++) {
					TRRET.setAsDouble(rret.getAsDouble(row, 0), row, column);
				}
			}
		}
		 else {
			TRRET = FRRET;
			d2TotalResidualRet.putAll(d2FundamentalResidualRet);
		 }

		// covarianceStats(TRRET, "Total Residual Return Matrix");

		// now calculate the factor covariance and residual variance
		// XXX NOTE HOW WE ONLY OPERATE ON THE FUNDAMENTAL FACTORS
		FCOV = ASEMath.wcov(USE_INTRADAY ? FFRET : FFRET.deleteColumns(Ret.LINK, 0), NUM_HALFLIFE_DAYS);
		check_fcov(FCOV);

		RVAR = ASEMath.wvar(USE_INTRADAY ? FRRET : FRRET.deleteColumns(Ret.LINK, 0), NUM_HALFLIFE_DAYS);
	}

	private void calculateAndRecordSecurityFactorReturns(CalcResults cr, long asof) {
		long t2 = asof;
		long t1 = Exchange.prevClose(t2, primaryExch);
		for (int lag = 0; lag < NUM_FACTOR_DAYS_TO_RECORD; lag++, t2 = t1, t1 = Exchange.prevClose(t1, primaryExch)) {
			if (lag == 0 && !Exchange.isOpen(t2, primaryExch))
				continue;

			AttrType attr = lattr(SFRET_ATTR, lag - 1);
			AttrType battr = lattr(SBFRET_ATTR, lag - 1);
			log.info("Calculating attributes: " + attr);

			Pair<Long, Long> tpair = new Pair<Long, Long>(t1, t2);
			Matrix FFRET = d2FundmentalFactorRet.get(tpair);
			// Matrix SFRET = d2SvdFactorRet.get(tpair);

			if (FFRET == null) {
				log.warning("No factor return found for between " + df.format(tpair.first) + " / " + df.format(tpair.second));
				continue;
			}

			// if (SVD_FACTORS > 0 && SFRET == null) {
			// log.warning("No factor return found for between " + df.format(tpair.first) + " / " + df.format(tpair.second));
			// continue;
			// }

			int nofaccnt = 0;
			for (Security sec : factorLoadings.getSecurities()) {
				double facret = 0.0;
				double bfacret = 0.0;

				for (int ii = 0; ii < fundamentalFactors.length; ii++) {
					double latestloading = factorLoadings.getLoadingAsOf(sec, fundamentalFactors[ii], t2);
					if (Double.isNaN(latestloading))
						continue;

					double v = latestloading * FFRET.getAsDouble(ii, 0);
					facret += v;
					if (isBarraFactor(fundamentalFactors[ii])) {
						bfacret += v;
					}
				}

				// for (int ii = 0; ii < svdFactors.length; ii++) {
				// double latestloading = factorLoadings.getLoadingAsOf(sec, svdFactors[ii], t2);
				// if (Double.isNaN(latestloading))
				// continue;
				//
				// double v = latestloading * d2SvdFactorRet.get(tpair).getAsDouble(ii, 0);
				// facret += v;
				// }

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
			Map<Security, Attribute> secFacret = cr.getResult(lattr(SFRET_ATTR, lag - 1));
			Map<Security, Attribute> secBarraFacret = cr.getResult(lattr(SBFRET_ATTR, lag - 1));

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

	// XXX Note that we take for granted that the FCOV is only based on fundamental factors
	private void recordFCOV(Matrix FCOV, CalcResults cr) {
		for (int ii = 0; ii < fundamentalFactors.length; ii++) {
			for (int jj = ii; jj < fundamentalFactors.length; jj++) {
				cr.addFactorCov(fundamentalFactors[ii], fundamentalFactors[jj], FCOV.getAsDouble(ii, jj));
			}
		}
	}

	private void recordResidualVars(Matrix RVAR, CalcResults cr, long asof) {
		for (int ii = 0; ii < secs.length; ii++) {
			Double value = RVAR.getAsDouble(ii, 0);
			if (!Double.isNaN(value) && value != 0.0) {
				cr.add(secs[ii], RVAR_ATTR, asof, value);
			}
		}
	}

	private void recordFactorReturns(CalcResults cr) {
		// Get the last day
		Vector<Pair<Long, Long>> intervals = new Vector<Pair<Long, Long>>();
		intervals.addAll(d2FundmentalFactorRet.keySet());
		Collections.sort(intervals);
		Pair<Long, Long> lastP = intervals.lastElement();

		Matrix lastFundM = d2FundmentalFactorRet.get(lastP);
		Matrix lastSvdM = d2SvdFactorRet.get(lastP);

		for (int ii = 0; ii < fundamentalFactors.length; ii++) {
			AttrType attr = new CalcAttrType(FRET_ATTR.name + "_" + fundamentalFactors[ii], FRET_ATTR.datatype);
			cr.addFactorReturn(attr, lastP.second, lastFundM.getAsDouble(ii, 0));
		}
		for (int ii = 0; ii < svdFactors.length; ii++) {
			AttrType attr = new CalcAttrType(FRET_ATTR.name + "_" + svdFactors[ii], FRET_ATTR.datatype);
			cr.addFactorReturn(attr, lastP.second, lastSvdM.getAsDouble(ii, 0));
		}
	}

	public double getFundamentalResidualReturn(Security sec, long t1, long t2) {
		Matrix FRRET = d2FundamentalResidualRet.get(new Pair<Long, Long>(t1, t2));
		if (FRRET == null) {
			return Double.NaN;
		}
		return FRRET.getAsDouble(Arrays.binarySearch(secs, sec), 0);
	}

	// XXX for now return the fundamental by default.
	public double getResidualReturn(Security sec, long t1, long t2) {
		return getFundamentalResidualReturn(sec, t1, t2);
		// Matrix TRRET = d2TotalResidualRet.get(new Pair<Long, Long>(t1, t2));
		// if (TRRET == null) {
		// return Double.NaN;
		// }
		// return TRRET.getAsDouble(Arrays.binarySearch(secs, sec), 0);
	}

	public void calculate(CalcResults cr, Set<Security> secset, long asof) throws Exception {
		log.info("Calculating Factors on " + secset.size() + " securitites as of " + df.format(asof));
		secs = (Security[]) secset.toArray(new Security[0]);
		Arrays.sort(secs);

		// XXX should think of a way to cache this information across days given the changing universe
		if (Time.midnight(asof) != Time.midnight(lastcalc)) {
			d2FundmentalFactorRet.clear();
			d2FundamentalResidualRet.clear();
			d2SvdFactorRet.clear();
			d2TotalResidualRet.clear();
			svdDirectionBootstrap = null;
		}

		generateFactors(asof, false);
		calculateMatrices(asof);

		factorLoadings.record(cr, asof);
		recordFCOV(FCOV, cr);
		calculateAndRecordSecurityFactorReturns(cr, asof);
		recordFactorReturns(cr);
		recordResidualVars(RVAR, cr, asof);
		recordSecurityResidualReturns(cr, asof);

		FCOV = null;
		RVAR = null;

		lastcalc = asof;
	}

	// XXX if you want cap map computed internally, pass a null
	public Map<Security, Attribute> calculateFitResults(Set<Security> secset, long t1, long t2, AttrType attrType, boolean barraonly, ReturnType rtype,
			Map<Security, NavigableMap<Long, Attribute>> capMap) throws Exception {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>(secset.size());
		secs = (Security[]) secset.toArray(new Security[0]);
		Arrays.sort(secs);

		if (barraonly)
			MAX_SVD_IDX = __BARRA_MAX_SVD_IDX__;
		else
			MAX_SVD_IDX = __REGULAR_MAX_SVD_IDX__;

		// XXX should think of a way to cache this information across days given the changing universe
		d2FundmentalFactorRet.clear();
		d2FundamentalResidualRet.clear();
		d2SvdFactorRet.clear();
		d2TotalResidualRet.clear();

		// XXX If this was run the first time with barraOnly = false, rerunning again with barraOnly = true will still keep around the non-barra factors
		// XXX To fix we need to follow this function and repopulate the factor vector every time rather only when lastCalc = 0.
		// XXX Not so fast! Bacause many calculators for factorLoadings return a null if they didn't recompute
		generateFactors(t1, barraonly);
		calculateFundamentalModel(t1, t2, capMap, rtype);

		for (Security sec : secset) {
			double ret = getFundamentalResidualReturn(sec, t1, t2);
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

	// ///////////////////////////////////////////////////////////////////////////////////////
	// VARIOUS
	// //////////////////////////////////////////////////////////////////////////////////////

	public static AttrType lattr(AttrType attr, int lag) {
		if (lag == -1) {
			return new CalcAttrType(attr.name + "C");
		}
		return new CalcAttrType(attr.name + lag);
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
				// if (Double.isNaN(r_prev)) {
				// r_prev = r;
				// continue;
				// }

				// sigma2 = mu + alpha * sigma2_prev + beta * r_prev * r_prev;
				sigma2 = mu + alpha * sigma2_prev + beta * r * r;
				sigma2_prev = sigma2;
				// r_prev = r;
			}

			log.info("GARCH for security " + secs[row] + ", mean=" + mean + ", sigma2=" + sigma2);

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

	private void covarianceStats(Matrix RRET, String name) {
		Matrix C = RRET.transpose().cov(Ret.NEW, true);

		double variance = 0;
		double covariance = 0;

		for (int ii = 0; ii < C.getSize(0); ii++)
			for (int jj = 0; jj < C.getSize(1); jj++) {
				double v = C.getAsDouble(ii, jj);
				if (Double.isNaN(v))
					continue;
				if (ii == jj)
					variance += v;
				else
					covariance += v;
			}

		log.info(name + ": Ratio of covariance to (variance+covariance) is " + covariance / (variance + covariance));
	}

}
