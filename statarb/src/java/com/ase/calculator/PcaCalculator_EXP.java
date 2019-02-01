package ase.calculator;

import java.util.HashSet;
import java.util.ListIterator;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import org.apache.commons.collections15.BidiMap;
import org.apache.commons.collections15.bidimap.DualHashBidiMap;
import org.ujmp.core.Matrix;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DoubleMatrix2D;
import org.ujmp.core.doublematrix.calculation.general.decomposition.SVD;

import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class PcaCalculator_EXP extends Calculator {
	private static final Logger log = LoggerFactory.getLogger(PcaCalculator_EXP.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	public static enum PcaType {
		PLAIN1, PLAIN2, MEAN_ADJ, CORR
	}

	private final Exchange.Type primaryExch;
	private UnifiedDataSource uSource;
	private final long interval;
	private long lastcalc = 0L;

	public static final AttrType getAttr(int type, int svs) {
		return new CalcAttrType("pcaRet_" + type + "_" + svs);
	}

	public static final AttrType PCA_RET1 = new CalcAttrType("pcaRet1", Type.N);
	public static final AttrType PCA_RET2 = new CalcAttrType("pcaRet2", Type.N);
	public static final AttrType PCA_RET3 = new CalcAttrType("pcaRet3", Type.N);
	public static final AttrType PCA_RET4 = new CalcAttrType("pcaRet4", Type.N);
	private static int RESIDUAL_SINGULAR_VALUES = 3;

	public PcaCalculator_EXP(UnifiedDataSource uSource, Exchange.Type primaryExch, long interval) {
		super();
		this.primaryExch = primaryExch;
		this.uSource = uSource;
		this.interval = interval;
		log.info("Creating PCA Calc with interval " + interval + " millis.");
	}

	public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		Set<AttrType> attrs = new HashSet<AttrType>();
		PcaCalculator_EXP.RESIDUAL_SINGULAR_VALUES = 3;
		attrs.add(calculate(cr, secs, asof, false, false, false, getAttr(1, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, false, true, getAttr(2, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, true, false, true, getAttr(3, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, true, true, getAttr(4, RESIDUAL_SINGULAR_VALUES)));

		PcaCalculator_EXP.RESIDUAL_SINGULAR_VALUES = 4;
		attrs.add(calculate(cr, secs, asof, false, false, false, getAttr(1, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, false, true, getAttr(2, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, true, false, true, getAttr(3, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, true, true, getAttr(4, RESIDUAL_SINGULAR_VALUES)));

		PcaCalculator_EXP.RESIDUAL_SINGULAR_VALUES = 5;
		attrs.add(calculate(cr, secs, asof, false, false, false, getAttr(1, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, false, true, getAttr(2, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, true, false, true, getAttr(3, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, true, true, getAttr(4, RESIDUAL_SINGULAR_VALUES)));

		PcaCalculator_EXP.RESIDUAL_SINGULAR_VALUES = 6;
		attrs.add(calculate(cr, secs, asof, false, false, false, getAttr(1, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, false, true, getAttr(2, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, true, false, true, getAttr(3, RESIDUAL_SINGULAR_VALUES)));
		attrs.add(calculate(cr, secs, asof, false, true, true, getAttr(4, RESIDUAL_SINGULAR_VALUES)));
		return attrs;
	}

	public AttrType calculate(CalcResults cr, Set<Security> secs, long asof, boolean meanAdj, boolean corr, boolean fullRet, AttrType pcaAttr) throws Exception {
		// int svdValues = (meanAdj || corr)? RESIDUAL_SINGULAR_VALUES + 1 : RESIDUAL_SINGULAR_VALUES;
		int svdValues = RESIDUAL_SINGULAR_VALUES;
		long startmillis = asof - interval + 1;

		if (!Exchange.isOpen(startmillis, primaryExch)) {
			log.warning("Not computing " + pcaAttr + " waiting for " + 1.0 * interval / Time.MILLIS_PER_SECOND / 60 + " mins after open.");
			return pcaAttr;
		}

		log.info("Computing intraday return SVD, attribute " + pcaAttr.name + ", asof=" + df.debugFormat(asof));

		Map<Security, BarTimeSeries> bars = uSource.barSource.getTimeSeries(secs, startmillis, asof, primaryExch);

		// Let N be the number of secs, let T be the number of bar
		int N = bars.size();
		int T = 0;
		for (BarTimeSeries bts : bars.values()) {
			T = bts.size();
			break;
		}
		log.info(N + " securities and " + T + " bars");

		// create correspondence between secids and an int 0..N-1
		int ii = 0;
		BidiMap<Security, Integer> secidToIndex = new DualHashBidiMap<Security, Integer>();
		for (Security sec : secs) {
			secidToIndex.put(sec, ii++);
		}

		// NxT matrix
		DoubleMatrix2D X = DoubleMatrix2D.factory.zeros(N, T);
		// populate matrix
		for (Map.Entry<Security, BarTimeSeries> e : bars.entrySet()) {
			Security sec = e.getKey();
			BarTimeSeries bts = e.getValue();
			int row = secidToIndex.get(sec);

			ListIterator<Bar> secBars = bts.getBars();
			int column = 0;
			while (secBars.hasNext()) {
				Bar b = secBars.next();
				double logrel = (b != null) ? Math.log(b.close / b.open) : 0.0;
				X.setDouble(logrel, row, column);
				column++;
			}
		}
		Matrix Xclone = X.clone();

		double[] means = null;
		double[] sigmas = null;
		if (meanAdj || corr) {
			means = new double[N];
			sigmas = new double[N];

			for (int row = 0; row < N; row++) {
				double sum = 0;
				double sum2 = 0;
				for (int column = 0; column < T; column++) {
					double x = X.getAsDouble(row, column);
					sum += x;
					sum2 += x * x;
				}
				means[row] = sum / T;
				sigmas[row] = Math.sqrt(sum2 / T - means[row] * means[row]);

				double mean = (meanAdj || corr) ? means[row] : 0;
				double sigma = 1;

				if (corr && !Double.isNaN(sigmas[row]) && sigmas[row] != 0)
					sigma = sigmas[row];
				else if (corr)
					sigma = Double.MAX_VALUE;
				else
					sigma = 1;

				for (int column = 0; column < T; column++) {
					double x = X.getAsDouble(row, column);
					X.setAsDouble((x - mean) / sigma, row, column);
				}
			}
		}

		log.info("Calculating SVD");
		SVD.SVDMatrix svd = new SVD.SVDMatrix(X);
		double[] svalues = svd.getSingularValues();
		int lastPrincipal = T - svdValues - 1;
		int firstTruncated = T - svdValues;
		double cummulativeMass = 0;
		double subtractedMass = 0;

		double totalMass = 0;
		for (double sv : svalues) {
			totalMass += sv * sv;
		}

		ii = 0;
		for (double sv : svalues) {
			cummulativeMass += sv * sv;
			if (ii <= lastPrincipal) {
				subtractedMass += sv * sv;
			}
			log.info("Singular Value Squared " + (ii + 1) + ": " + sv * sv + ", Cummulative: " + cummulativeMass + ", Cummulative Pct: "
					+ (100 * cummulativeMass / totalMass));
			ii++;
		}

		Matrix Uprin = svd.getU().select(Ret.LINK, "*;" + "0-" + lastPrincipal);
		Matrix Sprin = svd.getS().select(Ret.LINK, "0-" + lastPrincipal + ";" + "0-" + lastPrincipal);
		Matrix Vprin = svd.getV().select(Ret.LINK, "*;" + "0-" + lastPrincipal);

		Matrix Utr = svd.getU().select(Ret.LINK, "*;" + firstTruncated + "-" + (T - 1));
		Matrix Str = svd.getS().select(Ret.LINK, firstTruncated + "-" + (T - 1) + ";" + firstTruncated + "-" + (T - 1));
		Matrix Vtr = svd.getV().select(Ret.LINK, "*;" + firstTruncated + "-" + (T - 1));

		Matrix P = Uprin.mtimes(Sprin).mtimes(Vprin.transpose(Ret.LINK));
		Matrix R = Utr.mtimes(Str).mtimes(Vtr.transpose(Ret.LINK));
		double principalFrobenius = Math.pow(X.minus(R).getEuklideanValue(), 2);
		double residualFrobenius = Math.pow(X.minus(P).getEuklideanValue(), 2);
		double dataFrobenius = Math.pow(X.getEuklideanValue(), 2);
		log.info("Sanity check. This should be close to 0: " + (dataFrobenius - totalMass));
		log.info("Sanity check. This should be close to 0: " + (residualFrobenius - totalMass + subtractedMass));
		log.info("Sanity check. This should be close to 0: " + (principalFrobenius - subtractedMass));

		Matrix rsd = null;
		if (fullRet) {
			// total return vector
			Matrix r = Xclone.sum(Ret.NEW, 1, false);
			// factor loadings
			Matrix B = Uprin;
			// factor returns
			Matrix f = B.pinv().mtimes(r);
			// residual returns
			rsd = r.minus(B.mtimes(f));
		}
		else {
			// sum logrels across residual matrix
			rsd = R.sum(Ret.NEW, 1, false);
		}

		double[] rsds = new double[N];
		for (int row = 0; row < N; row++) {
			Security sec = secidToIndex.inverseBidiMap().get(row);
			double x = rsd.getAsDouble(row, 0);
			cr.add(sec, pcaAttr, asof, x);
			rsds[row] = x;
		}

		Pair<Double, Double> p = ASEMath.meansig(rsds);
		log.info("Residual return distribution: " + p.first + "/" + p.second);

		lastcalc = asof;
		return pcaAttr;
	}
}
