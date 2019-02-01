package ase.util.math;

import java.util.Arrays;
import java.util.Vector;
import java.util.Random;

import org.apache.commons.math.stat.descriptive.rank.Percentile;
import org.ujmp.core.Matrix;
import org.ujmp.core.MatrixFactory;
import org.ujmp.core.calculation.Calculation;
import org.ujmp.core.calculation.Calculation.Ret;
import org.ujmp.core.doublematrix.DenseDoubleMatrix2D;
import org.ujmp.core.doublematrix.calculation.general.missingvalues.Impute.ImputationMethod;

import ase.util.Pair;

public class ASEMath {

	private static Random randomGenerator = new Random();
	public static double BPS_MULTIPLIER = 10000.0;

	public static boolean sameSign(double a, double b) {
		if (a >= 0.0 && b >= 0.0)
			return true;
		else if (a <= 0.0 && b <= 0.0)
			return true;
		return false;
	}

	public static Pair<Double, Double> meansig(double[] vec) {
		double n = vec.length;
		double sumsq = 0, sum = 0;
		for (int i = 0; i < n; i++) {
			sum += vec[i];
			sumsq += vec[i] * vec[i];
		}
		Double mean = new Double(sum / n);
		Double sig = new Double(Math.sqrt((sumsq - sum * sum / n) / (n - 1)));
		return new Pair<Double, Double>(mean, sig);
	}

	public static double mean(Vector<Double> v) {
		double tot = 0.0;
		for (int ii = 0; ii < v.size(); ii++) {
			tot += v.get(ii);
		}
		return tot / v.size();
	}

	public static double sigma(double sum, double sumsq, int count) {
		return Math.sqrt(sumsq / count - (sum / count) * (sum / count));
	}

	// if it's ever a problem, we can use the fast median algorithm
	// or find the actual median
	public static double median(double[] vec) {
		Arrays.sort(vec);
		return vec[vec.length / 2];
	}

	public static double[] percentiles(double[] vec, double[] pct) {
		if (pct == null)
			return null;
		double[] result = new double[pct.length];
		Percentile p = new Percentile();
		p.setData(vec);
		for (int i = 0; i != pct.length; i++) {
			result[i] = p.evaluate(pct[i]);
		}
		return result;
	}

	// weighted covariance (doesn't ignore nans)
	public static Matrix wcov(Matrix R, int h) {
		// thanks mr sharpe
		// http://www.stanford.edu/~wfsharpe/mat/wcov.txt
		// but here we make it unbiased (* 1/(1-sum(w^2)) )
		// http://en.wikipedia.org/wiki/Sample_mean_and_sample_covariance
		long[] size = R.getSize();
		long n = size[0];
		long s = size[1];

		Matrix x = MatrixFactory.zeros(1, s);
		if (h != 0) {
			for (int i = 0; i < s; i++) {
				x.setAsDouble(1.0 * (s - i) / h, 0, i);
			}
		}

		Matrix w = MatrixFactory.ones(1, s).times(2.0);
		w.power(Calculation.Ret.ORIG, x);

		double wsum = 0.0;
		for (int j = 0; j < s; j++) {
			wsum += w.getAsDouble(0, j);
		}
		Matrix p = w.divide(wsum);
		double psumsq = 0.0;
		for (int j = 0; j < s; j++) {
			double pval = p.getAsDouble(0, j);
			psumsq += pval * pval;
		}
		Matrix e = R.mtimes(p.transpose());
		Matrix d = R.minus(e.mtimes(MatrixFactory.ones(1, s)));
		Matrix diag = MatrixFactory.zeros(s, s);
		for (int j = 0; j < s; j++)
			diag.setAsDouble(p.getAsDouble(0, j), j, j);
		Matrix C = d.mtimes(diag).mtimes(d.transpose());
		C = C.divide(1.0 - psumsq);
		return C;
	}

	// weighted variance (ignores nans)
	public static Matrix wvar(Matrix R, int h) {
		long[] size = R.getSize();
		long n = size[0];
		long s = size[1];

		Matrix x = MatrixFactory.zeros(1, s);
		if (h != 0) {
			for (int i = 0; i < s; i++) {
				x.setAsDouble(1.0 * (s - i) / h, 0, i);
			}
		}

		Matrix w = MatrixFactory.ones(1, s).times(2.0);
		w.power(Calculation.Ret.ORIG, x);

		Matrix V = MatrixFactory.zeros(n, 1);
		for (int i = 0; i < n; i++) {
			double wsum = 0.0;
			for (int j = 0; j < s; j++) {
				double r = R.getAsDouble(i, j);
				if (!Double.isNaN(r)) {
					wsum += w.getAsDouble(0, j);
				}
			}
			Matrix p = w.divide(wsum);
			double psumsq = 0.0;
			for (int j = 0; j < s; j++) {
				double r = R.getAsDouble(i, j);
				if (!Double.isNaN(r)) {
					double pval = p.getAsDouble(0, j);
					psumsq += pval * pval;
				}
			}
			double mean = 0.0;
			for (int j = 0; j < s; j++) {
				double r = R.getAsDouble(i, j);
				if (!Double.isNaN(r))
					mean += p.getAsDouble(0, j) * r;
			}
			double var = 0.0;
			for (int j = 0; j < s; j++) {
				double r = R.getAsDouble(i, j);
				if (!Double.isNaN(r)) {
					double d = r - mean;
					var += p.getAsDouble(0, j) * d * d;
				}
			}
			V.setAsDouble(var / (1.0 - psumsq), i, 0);
		}
		return V;
	}

	public static boolean randomChance(double prob) {
		assert prob >= 0.0 && prob <= 1.0;
		return randomGenerator.nextDouble() <= prob;
	}

	// create a matrix X, so that XX^T=wcov(R). This way we can identify its eigendecomposition by operating on lower rank matrix X (this is our assumption)
	// As part of the process, impute values of R that are nan
	public static Matrix preWcov(Matrix R, int h) {
		// thanks mr sharpe
		// http://www.stanford.edu/~wfsharpe/mat/wcov.txt
		// but here we make it unbiased (* 1/(1-sum(w^2)) )
		// http://en.wikipedia.org/wiki/Sample_mean_and_sample_covariance
		long N = R.getSize(0);
		long T = R.getSize(1);

		Matrix x = DenseDoubleMatrix2D.factory.zeros(1, T);
		if (h != 0) {
			for (int ii = 0; ii < T; ii++) {
				x.setAsDouble(1.0 * (T - ii) / h, 0, ii);
			}
		}

		Matrix w = DenseDoubleMatrix2D.factory.ones(1, T).times(Ret.ORIG, false, 2.0);
		w.power(Calculation.Ret.ORIG, x);

		double wsum = w.getValueSum();
		w.divide(Ret.ORIG, false, wsum);
		double wsum2 = Math.pow(w.getEuklideanValue(), 2);

		Matrix X = R.clone();
		X.impute(Ret.ORIG, ImputationMethod.RowMean);
		X.impute(Ret.ORIG, ImputationMethod.Zero);

		Matrix m = R.mtimes(w.transpose(Ret.LINK)); // weighted mean of each row
		Matrix wsq = w.sqrt(Ret.NEW); // sqrt of weights (for each column)
		for (int ii = 0; ii < N; ii++) {
			// get a view to the row
			Matrix row = X.selectRows(Ret.LINK, ii);
			row.minus(Ret.ORIG, false, m.getAsDouble(ii, 0));
			row.times(Ret.ORIG, false, wsq);
			row.times(Ret.ORIG, false, Math.sqrt(1 / (1 - wsum2)));
		}
		return X;
	}

	// create a matrix X, so that XX^T=wcorr(R). This way we can identify its eigendecomposition by operating on lower rank matrix X (this is our assumption)
	// As part of the process, impute values of R that are nan
	///XXX check this for correctness
	//http://en.wikipedia.org/wiki/Pearson_product-moment_correlation_coefficient#Calculating_a_weighted_correlation
	public static Matrix preWcorr(Matrix R, int h) {
		long N = R.getSize(0);
		long T = R.getSize(1);

		Matrix x = DenseDoubleMatrix2D.factory.zeros(1, T);
		if (h != 0) {
			for (int ii = 0; ii < T; ii++) {
				x.setAsDouble(1.0 * (T - ii) / h, 0, ii);
			}
		}

		Matrix w = DenseDoubleMatrix2D.factory.ones(1, T).times(Ret.ORIG, false, 2.0);
		w.power(Calculation.Ret.ORIG, x);

		double wsum = w.getValueSum();
		w.divide(Ret.ORIG, false, wsum);
		double wsum2 = Math.pow(w.getEuklideanValue(), 2);
		Matrix wsq = w.sqrt(Ret.NEW); // sqrt of weights (for each column)

		Matrix X = R.clone();
		X.impute(Ret.ORIG, ImputationMethod.RowMean);
		X.impute(Ret.ORIG, ImputationMethod.Zero);

		Matrix m = R.mtimes(w.transpose(Ret.LINK)); // weighted mean of each row (remember that weights sum up to 1: no division by sum{w_i} is needed)
		Matrix s = DenseDoubleMatrix2D.factory.zeros(N, 1); // weighted variance of each row (remember that weights sum up to 1)
		for (int ii = 0; ii < N; ii++) {
			// copy row
			Matrix row = X.selectRows(Ret.NEW, ii);
			row.minus(Ret.ORIG, false, m.getAsDouble(ii, 0));
			row.times(Ret.ORIG, false, wsq);
			row.power(Ret.ORIG, 2.0);
			double var = row.getValueSum();
			s.setAsDouble(Math.sqrt(var), ii, 0);
		}

		// now adjust
		for (int ii = 0; ii < N; ii++) {
			// get a view to the row
			Matrix row = X.selectRows(Ret.LINK, ii);
			row.minus(Ret.ORIG, false, m.getAsDouble(ii, 0));
			row.divide(Ret.ORIG, false, s.getAsDouble(ii, 0));
			row.times(Ret.ORIG, false, wsq);
		}
		return X;
	}
}
