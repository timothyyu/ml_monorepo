package ase.calculator;

import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.BarSource;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.timeseries.DailyBarTimeSeries;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Time;

public class TrendingCalculator {
	public static enum Mode {
		C2C, D2C, RSDC2C
	}

	private static final Logger log = LoggerFactory.getLogger(TrendingCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	
	private final FactorCalculator fCalc;
	private final UnifiedDataSource uSource;

	private static final Map<Mode, String> modeNames = new HashMap<Mode, String>() {
		{
			put(Mode.C2C, "C");
			put(Mode.D2C, "D"); // Date of the attribute to current
			put(Mode.RSDC2C, "R");
		}
	};

	public TrendingCalculator(UnifiedDataSource uSource, FactorCalculator fCalc) {
		this.uSource = uSource;
		this.fCalc = fCalc;
	}

	public AttrType calculate(CalcResults cr, AttrType attrType, long asof, Mode mode) throws Exception {
		AttrType retType = getResName(attrType, mode);
		log.info("TrendCalculator calculating " + attrType.name + " into " + retType.name);

		Map<Security, Attribute> unadjAttrs = cr.getResult(attrType);
		if (unadjAttrs == null) {
			log.severe("can't trend calc " + attrType + " because no attrs found");
			return null;
		}

		//long latest = asof - Time.fromDays(5);
		//uSource.barSource.preload(unadjAttrs.keySet(), latest, asof);
		for (Map.Entry<Security, Attribute> ent : unadjAttrs.entrySet()) {
			Security sec = ent.getKey();
			Attribute attr = ent.getValue();
			// needs to be rethought here. not sure how efficient/correct it is to figure out all the date ranges independently
			boolean midday = Exchange.isOpen(attr.date - BarSource.BAR_SPAN, sec.primaryExchange);

			long t1;
			if (mode == Mode.D2C && midday)
				t1 = attr.date;
			else if (attr.date == Exchange.closeTime(attr.date, sec.primaryExchange))
				t1 = attr.date;
			else
				t1 = Exchange.prevClose(attr.date, sec.primaryExchange);

			long t2 = Math.min(asof, Exchange.nextClose(attr.date, sec.primaryExchange));
			if (t2 == asof && !Exchange.isOpen(asof, sec.primaryExchange)) {
				continue;
			}

			Double logrel = null;
			if (mode == Mode.RSDC2C) {
				//logrel = Double.NaN; // FactorCalculator.getRsdRet(attr.sec, date1, date2)
				logrel = fCalc.getResidualReturn(sec, t1, t2);
			}
			else if (mode == Mode.C2C) {
				DailyBarTimeSeries dbts = uSource.getDailyBarTimeSeries(CollectionUtils.toSet(sec), Time.today(t1), t2, sec.primaryExchange).get(sec);
				if (dbts.size() != 2) {
					log.severe("Found " + dbts.size() + " points in compute logrel: " + sec.getSecId() + " t1:" + df.debugFormat(t1) + " t2: "
							+ df.debugFormat(t2) + " attr: " + attr + ". Used attr.date=" + df.debugFormat(attr.date) + " and asof=" + df.debugFormat(asof));
				}
				logrel = dbts.getLogrel();
			}
			if (logrel == null) {
				log.finest("missing logrel, cant trend " + attr + " t1 " + t1 + " t2 " + t2);
				continue;
			}
			// /XXX Revisit this and decide if we want to adjust logrel by the attribute value (e.g. multiply it with abs, straight multiply, etc)
			cr.add(sec, retType, attr.date, logrel);
		}
		return retType;
	}

	public static AttrType getResName(AttrType attr, Mode mode) {
		return new CalcAttrType(attr.name + "_T-" + modeNames.get(mode));
	}

	public static void tests() throws Exception {
		Security sec = new Security(5334);
		AttrType att = new AttrType("test");
		long date = ASEFormatter.getInstance().parseHumanShort("20110401 16:40:00").getTime();
		long asof = ASEFormatter.getInstance().parseHumanShort("20110401 16:50:00").getTime();
		CalcResults cr = new CalcResults(0);
		cr.add(sec, att, date, 1.0);
		TrendingCalculator calc = new TrendingCalculator(new UnifiedDataSource(true), null);
		calc.calculate(cr, att, asof, Mode.C2C);
		System.out.println(cr.getResult(calc.getResName(att, Mode.C2C)).get(sec));
	}

	public static void main(String[] args) throws Exception {
		tests();
	}
}
