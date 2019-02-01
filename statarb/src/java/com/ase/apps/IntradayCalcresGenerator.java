package ase.apps;

import java.io.File;
import java.io.Writer;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.calculator.BarraCalculator;
import ase.calculator.DailyPriceCalculator;
import ase.calculator.GroupingCalculator;
import ase.calculator.IntradayBarCalculator;
import ase.calculator.PassThruCalculator;
import ase.calculator.PcaCalculator;
import ase.calculator.ShortTermEventCalculator;
import ase.calculator.CalcMaster.Mode;
import ase.calculator.PcaCalculator_EXP;
import ase.calculator.filter.SecurityFilter;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class IntradayCalcresGenerator {
	protected static final Logger log = LoggerFactory.getLogger(IntradayCalcresGenerator.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();

	public static void main(String[] argv) throws Exception {
		String location = argv[0];
		long interval = Time.fromMinutes(Long.parseLong(argv[1]));
		log.info("Running on " + location + " at interval " + interval);

		Exchange.Type exch = Exchange.Type.valueOf(System.getenv("PRIMARY_EXCHANGE"));

		UnifiedDataSource uSource = new UnifiedDataSource(false);
		GroupingCalculator gCalc = new GroupingCalculator();
		IntradayBarCalculator ibCalc = new IntradayBarCalculator(uSource, exch);
		PcaCalculator pcaCalc = new PcaCalculator(uSource, exch, Time.MILLIS_PER_HOUR, false);
		PcaCalculator_EXP pcaCalcExp = new PcaCalculator_EXP(uSource, exch, Time.MILLIS_PER_HOUR);
		DailyPriceCalculator dpCalc = new DailyPriceCalculator(uSource, 20, exch);
		ShortTermEventCalculator stCalc = new ShortTermEventCalculator();

		for (Map.Entry<Long, File> file : FileUtils.getDumpedFiles(location + "/calcres", FileUtils.CALCRES_PATTERN).entrySet()) {
			CalcResults uni = CalcResults.restore(file.getValue());
			Map<Security, Attribute> pforecastable = uni.getResult(SecurityFilter.PRICE_FORECASTABLE);
			Map<Security, Attribute> advps = uni.getResult(DailyPriceCalculator.ADVP);
			Map<Security, Attribute> sic = uni.getResult(PassThruCalculator.SIC);
			Map<Security, Attribute> ind1 = uni.getResult(BarraCalculator.IND1);
			Map<Security, Attribute> beta = uni.getResult(BarraCalculator.B_BETA);
			Set<Security> secs = pforecastable.keySet();

			// XXX potential bias! make sure the price forecastable was done from data prior to the calcres date!
			long open = Exchange.openTime(file.getKey(), exch);
			for (long asof = open + interval; asof < Exchange.closeTime(asof, exch); asof += interval) {
				log.info("Generating intraday independents at " + df.debugFormat(asof));

				CalcResults cr = new CalcResults(asof);
				cr.add(pforecastable);
				cr.add(sic);
				cr.add(ind1);
				cr.add(beta);
				gCalc.calculate(cr, secs, cr.getAsOf());
				// XXX associate the advp with the timestamp of the calcres, so that we can do weighted fits
				for (Map.Entry<Security, Attribute> e : advps.entrySet()) {
					cr.add(e.getKey(), e.getValue().type, e.getValue().date, e.getValue().asDouble());
				}

//				// recreate calculators at start of day, 10am, 1pm, so as to also put in those intraday calcres files previous day technicals
				if (asof == open || asof == open + 30 * Time.MILLIS_PER_MINUTE || asof == open + 210 * Time.MILLIS_PER_MINUTE
						|| asof % Time.MILLIS_PER_HOUR == 0) {
					ibCalc = new IntradayBarCalculator(uSource, exch);
					pcaCalc = new PcaCalculator(uSource, exch, Time.MILLIS_PER_HOUR, false);
					//pcaCalcExp = new PcaCalculator_EXP(uSource, exch, Time.MILLIS_PER_HOUR);
					dpCalc = new DailyPriceCalculator(uSource, 20, exch);
					// Do intraday technicals only on those instances
					dpCalc.calculate(cr, secs, asof, Mode.SIM);
				}

				ibCalc.calculate(cr, secs, asof);
				pcaCalc.calculate(cr, secs, asof);		
				stCalc.calculate(uni, cr, asof, 1);
//				pcaCalcExp.calculate(cr, secs, asof);

				Pair<String, Writer> resfile = FileUtils.openDataDumpFile(location + "/calcres_intraday", "calcres_intraday", asof);
				Writer writer = resfile.second;
				cr.dump(writer);
				writer.close();
				FileUtils.finalizeFile(resfile.first);

				cr = null;
			}
		}
	}
}
