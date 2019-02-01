package ase.portfolio;

import java.io.File;
import java.io.Writer;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.apps.DailyManager.OutputType;
import ase.data.Security;
import ase.data.XRef;
import ase.data.widget.SQLDailyPriceWidget;
import ase.data.widget.SQLSecurityWidget;
import ase.portfolio.CapAdjustment.SizeRefType;
import ase.portfolio.CapAdjustment.Type;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Triplet;

public class CapAdjustmentGenerator {
	protected static final Logger log = LoggerFactory.getLogger(CapAdjustmentGenerator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	protected static SQLDailyPriceWidget pw = SQLDailyPriceWidget.instance();
	protected static SQLSecurityWidget sw = SQLSecurityWidget.instance();

	protected static Vector<CapAdjustment> dividendsAndSplits(Set<Security> secs, long date) throws Exception {
		Vector<CapAdjustment> adjs = new Vector<CapAdjustment>();
		Map<Security, Triplet<Double, Double, Double>> dp = pw.getAdjustments(secs, date);

		for (Map.Entry<Security, Triplet<Double, Double, Double>> e : dp.entrySet()) {
			if (e.getValue().first != 0) {
				adjs.add(new CapAdjustment(e.getKey(), Type.DIV, e.getValue().first, 0, SizeRefType.SELF, sw.getXrefMap(CollectionUtils.toSet(e.getKey()),
						date, XRef.TIC).get(e.getKey())
						+ ", DIV=" + e.getValue().first));
			}
			if (e.getValue().second !=0 ) {
				adjs.add(new CapAdjustment(e.getKey(), Type.CASHEQ, e.getValue().second, 0, SizeRefType.SELF, sw.getXrefMap(CollectionUtils.toSet(e.getKey()),
						date, XRef.TIC).get(e.getKey())
						+ ", CASHEQ=" + e.getValue().second));
			}
			if (e.getValue().third != 1) {
				adjs.add(new CapAdjustment(e.getKey(), Type.SPLIT, e.getValue().third, 0, SizeRefType.SELF, sw.getXrefMap(CollectionUtils.toSet(e.getKey()),
						date, XRef.TIC).get(e.getKey())
						+ ", SPLIT=" + e.getValue().third));
			}
		}
		return adjs;
	}

	// get the set as from the current sod portfolio. do not use the universe
	// for this one/
	protected static Set<Security> getSecurities(String location, long date) throws Exception {
		String sodfile = location + "/" + df.toYYYYMMDD(date) + "/" + Portfolio.SOD_PORTFOLIO;
		Portfolio portfolio = new Portfolio();
		portfolio.restore(new File(sodfile));
		return portfolio.getSecurities();
	}

	public static Vector<CapAdjustment> getAdjustments(Set<Security> secs, long date) throws Exception {
		Vector<CapAdjustment> adjs = new Vector<CapAdjustment>();
		adjs.addAll(dividendsAndSplits(secs, date));
		return adjs;
	}

	public static void generateAdjustmentFile(String location, long date, Set<OutputType> output) throws Exception {
		log.info("Creating cap adjustments for date " + date);

		int cnt = 0;
		Set<Security> secs = getSecurities(location, date);
		Vector<CapAdjustment> adjs = getAdjustments(secs, date);

		// create files
		StringBuilder sb = new StringBuilder();
		sb.append(CapAdjustment.dumpHeader());
		sb.append('\n');
		for (CapAdjustment adj : adjs) {
			cnt++;
			sb.append(adj.toString());
			sb.append('\n');
		}
		String report = sb.toString();

		// create file by default
		Writer writer = FileUtils.makeWriter(location + "/" + df.toYYYYMMDD(date) + "/" + Portfolio.DAY_CAPADJUSTMENTS);
		writer.append(report);
		writer.close();

		if (output.contains(OutputType.EMAIL)) {
			Email.email("Cap Adjustments for " + df.toYYYYMMDD(date), report);
		}

		if (output.contains(OutputType.SCREEN)) {
			System.out.println(report);
		}

		log.info("Created " + cnt + " adjustments");
	}
}
