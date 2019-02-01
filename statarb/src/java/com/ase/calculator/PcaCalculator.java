package ase.calculator;

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
import org.ujmp.core.doublematrix.calculation.general.statistical.StatisticalDoubleCalculations;
import org.ujmp.core.doublematrix.impl.BlockDenseDoubleMatrix2D;

import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.Bar;
import ase.timeseries.BarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class PcaCalculator extends Calculator {
	private static final Logger log = LoggerFactory.getLogger(PcaCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final Exchange.Type primaryExch;
	private UnifiedDataSource uSource;
	private final long interval;
	private long lastcalc = 0L;
	private final boolean daily;

	public static final AttrType PCA_RET = new CalcAttrType("pcaRet", Type.N);
	public static final AttrType PCA_DAILY_RET = new CalcAttrType("pcaDailyRet", Type.N);
	public static final AttrType PCA_DAILY_RETC = new CalcAttrType("pcaDailyRetC", Type.N);
	public static final AttrType PCA_DAILY_RET0 = new CalcAttrType("pcaDailyRet0", Type.N);
	public static final AttrType PCA_DAILY_RET1 = new CalcAttrType("pcaDailyRet1", Type.N);
	public static final AttrType PCA_DAILY_RET2 = new CalcAttrType("pcaDailyRet2", Type.N);
	
	public static final AttrType CORRELATION_DAILY = new CalcAttrType("corrDaily", Type.N);
	public static final AttrType CORRELATION_INTRA = new CalcAttrType("corrIntra", Type.N);

	private int RESIDUAL_SINGULAR_VALUES = 12;// 3;
	private int RESIDUAL_SINGULAR_VALUES_DAILY = 50;
	private int DAYS_BACK = 90;

	private final static boolean MEAN_ADJUST = true;
	private final static boolean NORMAL_ADJUST = false;
	private final static boolean WEIGHTED = false;

	public PcaCalculator(UnifiedDataSource uSource, Exchange.Type primaryExch, long interval, boolean daily) {
		super();
		this.primaryExch = primaryExch;
		this.uSource = uSource;
		this.interval = interval;
		this.daily = daily;
		log.info("Creating PCA Calc with interval " + interval + " millis.");
	}

	public AttrType calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		Map<Security, ? extends BarTimeSeries> bars;
		if (daily) {
			long startdate = Exchange.subtractTradingDays(asof, DAYS_BACK, primaryExch);
			bars = uSource.getDailyBarTimeSeries(secs, Time.today(startdate), asof, primaryExch);
		}
		else {
			long startmillis = asof - interval + 1;
			if (!Exchange.isOpen(startmillis, primaryExch)) {
				log.warning("Not computing " + PCA_RET + " waiting for " + 1.0 * interval / Time.MILLIS_PER_SECOND / 60 + " mins after open.");
				return PCA_RET;
			}
			log.info("Computing intraday return SVD, asof=" + df.debugFormat(asof));
			bars = uSource.barSource.getTimeSeries(secs, startmillis, asof, primaryExch);
		}

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
		DoubleMatrix2D X = BlockDenseDoubleMatrix2D.factory.zeros(N, T);
		// populate matrix
		for (Map.Entry<Security, ? extends BarTimeSeries> e : bars.entrySet()) {
			Security sec = e.getKey();
			BarTimeSeries bts = e.getValue();
			int row = secidToIndex.get(sec);

			// XXX for dailys returns are close2close. For intraday returns are open2close of each bar
			if (daily) {
				double[] r = bts.getLogrelArray(1, 0);
				for (int column = 0; column < T; column++) {
					double logrel = (!Double.isNaN(r[column])) ? r[column] : 0.0;
					X.setDouble(logrel, row, column);
				}
			}
			else {
				ListIterator<Bar> secBars = bts.getBars();
				int column = 0;
				while (secBars.hasNext()) {
					Bar b = secBars.next();
					double logrel = (b != null) ? Math.log(b.close / b.open) : 0.0;
					X.setDouble(logrel, row, column);
					column++;
				}
			}
		}

		//Compute correlation statistics once per day for daily
		if (!daily || Time.today(asof) != Time.today(lastcalc)) {
			// Compute and output correlations for information reasons
			log.info("Computing correlation matrix...");
			Matrix Xnorm = X.clone();
			for (int row = 0; row < N; row++){
				double sum = 0;
				double sum2 = 0;
				double cnt = 0;
				for (int column = 0; column < T; column++) {
					double x = Xnorm.getAsDouble(row, column);
					if (Double.isNaN(x))
						continue;
					sum += x;
					sum2 += x * x;
					cnt++;
				}

				double mean = sum / cnt;
				double std = Math.sqrt(sum2 / cnt - mean * mean);
				for (int column = 0; column < T; column++) {
					double x = Xnorm.getAsDouble(row, column);
					x = (x - mean) / std;
					if (Double.isNaN(x))
						x = 0.0;
					Xnorm.setAsDouble(x, row, column);
				}
			}
			
			Matrix Rho = Xnorm.mtimes(Xnorm.transpose()).divide(Ret.ORIG, false, T);
			log.info("Computed correlation matrix!");
			Map<Security, Attribute> advps = cr.getResult(DailyPriceCalculator.ADVP);
			double rho = 0.0;
			double weightedRho = 0.0;
			double weight = 0;
			int entries = 0;
			for (int row = 0; row < N; row++) {
				Security sec1 = secidToIndex.inverseBidiMap().get(row);
				double w1 = (advps.containsKey(sec1)) ? advps.get(sec1).asDouble() : 0.0;
				for (int column = row + 1; column < N; column++) {
					Security sec2 = secidToIndex.inverseBidiMap().get(column);
					double w2 = (advps.containsKey(sec2)) ? advps.get(sec2).asDouble() : 0.0;
					if (Double.isNaN(Rho.getAsDouble(row, column))) {
						continue; // This can happen if the rets for a sec are all 0. (zero variance)
					}
					rho += Rho.getAsDouble(row, column);
					weightedRho += (w1 / 1e6) * (w2 / 1e6) * Rho.getAsDouble(row, column);
					weight += (w1 / 1e6) * (w2 / 1e6);
					entries++;
				}
			}
			log.info("Computed correlation statistics!");
			Xnorm = null;
			Rho = null;
			advps = null;
			log.info((daily ? "Daily " : "Intraday ") + "average sec correlation: " + df.fformat(rho / entries));
			cr.add(Security.MARKET_SEC, daily ? CORRELATION_DAILY : CORRELATION_INTRA, asof, weightedRho/weight);
			log.info((daily ? "Daily " : "Intraday ") + "weighted average sec correlation: " + df.fformat(weightedRho / weight));
		}

		if (MEAN_ADJUST) {
			log.info("Mean adjusting");
			for (int column = 0; column < T; column++) {
				double sum = 0;
				double sumsq = 0.0;
				for (int row = 0; row < N; row++) {
					double x = X.getDouble(row, column);
					sum += x;
				}
				double mean = sum / N;
				for (int row = 0; row < N; row++) {
					double data = X.getDouble(row, column);
					X.setDouble(data - mean, row, column);
				}
			}
		}

		// if (NORMAL_ADJUST) {
		// log.info("Mean adjusting");
		// for (int row = 0; row < N; row++) {
		// double sum = 0;
		// double sumsq = 0.0;
		// for (int column = 0; column < T; column++) {
		// double x = X.getDouble(row, column);
		// sum += x;
		// sumsq += x * x;
		// }
		// double mean = sum / T;
		// double sd = Math.sqrt((sumsq - sum * sum / T) / T);
		// log.info("SD: " + sd);
		// for (int column = 0; column < T; column++) {
		// double data = X.getDouble(row, column);
		// X.setDouble(sd == 0.0 ? 0.0 : (data - mean)/sd, row, column);
		// }
		// }
		// RESIDUAL_SINGULAR_VALUES=3;
		// }
		//
		// Map<Security, Attribute> advps = null;
		// if (WEIGHTED) {
		// advps = cr.getResult(DailyPriceCalculator.ADVP);
		// log.info("Weighting by advp");
		//
		// for (int row = 0; row < N; row++) {
		// Security sec = secidToIndex.inverseBidiMap().get(row);
		// Attribute attr = advps.get(sec);
		// double advp = (attr != null)? attr.asDouble()/1e6 : 1;
		//
		// for (int column = 0; column < T; column++) {
		// double data = X.getDouble(row, column);
		// X.setDouble(advp * data, row, column);
		// }
		// }
		// }

		log.info("Calculating SVD");
		SVD.SVDMatrix svd = new SVD.SVDMatrix(X);
		double[] svalues = svd.getSingularValues();
		double cummulativeMass = 0;
		double subtractedMass = 0;

		double totalMass = 0;
		for (double sv : svalues) {
			totalMass += sv * sv;
		}

		int resid_vals = daily ? RESIDUAL_SINGULAR_VALUES_DAILY : RESIDUAL_SINGULAR_VALUES;
		
		ii = 1;
		for (double sv : svalues) {
			cummulativeMass += sv * sv;
			if (ii <= (T - resid_vals)) {
				subtractedMass += sv * sv;
			}
			log.info("Singular Value Squared " + (ii++) + ": " + sv * sv + ", Cummulative: " + cummulativeMass + ", Cummulative Pct: "
					+ (100 * cummulativeMass / totalMass));
		}

		Matrix Utr = svd.getU().select(Ret.LINK, "*;" + (T - resid_vals) + "-" + (T - 1));
		Matrix Str = svd.getS().select(Ret.LINK, (T - resid_vals) + "-" + (T - 1) + ";" + (T - resid_vals) + "-" + (T - 1));
		Matrix VTtr = svd.getV().select(Ret.LINK, "*;" + (T - resid_vals) + "-" + (T - 1)).transpose(Ret.LINK);
		Matrix R = Utr.mtimes(Str).mtimes(VTtr);

		log.info(R.getRowCount() + "x" + R.getColumnCount());

		for (int row = 0; row < N; row++) {
			double totalRet = 0;
			for (int column = 0; column < T; column++)
				totalRet += R.getAsDouble(row, column);
			Security sec = secidToIndex.inverseBidiMap().get(row);
			// if (WEIGHTED) {
			// Attribute attr = advps.get(sec);
			// double advp = (attr != null)? attr.asDouble()/1e6 : 1;
			// totalRet /= advp;
			// }
			cr.add(sec, daily ? PCA_DAILY_RET : PCA_RET, asof, totalRet);
			if (daily) {
				assert T > 3;
				cr.add(sec, PCA_DAILY_RETC, asof, R.getAsDouble(row, T - 1));
				cr.add(sec, PCA_DAILY_RET0, asof, R.getAsDouble(row, T - 2));
				cr.add(sec, PCA_DAILY_RET1, asof, R.getAsDouble(row, T - 3));
				cr.add(sec, PCA_DAILY_RET2, asof, R.getAsDouble(row, T - 4));
			}
		}

		double frobenius = X.minus(R).getEuklideanValue();
		log.warning("Sanity check. This should be close to 0: " + (frobenius - Math.sqrt(subtractedMass)));

		lastcalc = asof;
		return daily ? PCA_DAILY_RET : PCA_RET;
	}
}
