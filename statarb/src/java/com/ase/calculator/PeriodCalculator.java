package ase.calculator;

import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.AttrType.Type;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DateAttribute;
import ase.data.DbAttrType;
import ase.data.ReutersAnnDate;
import ase.data.Security;
import ase.data.widget.SQLEstimateWidget;
import ase.data.widget.SQLEstimateWidget.DateType;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class PeriodCalculator extends Calculator {
	private static final Logger log = LoggerFactory.getLogger(PeriodCalculator.class.getName());
	private static final SQLEstimateWidget widget = SQLEstimateWidget.instance();

	//XXX born dates for backfilled data are screwed up. Ignore them for now
	public static final DbAttrType PERIOD_QUARTERS = new DbAttrType("PERIOD_Q", "PERIOD_Q", 0L, 0L);
	public static final DbAttrType PERIOD_YEARS = new DbAttrType("PERIOD_A", "PERIOD_A", 0L, 0L);
	public static final int NUM_OF_PERIODS = 4;

	public static final CalcAttrType quarterlyEstimatesPeriod = new CalcAttrType("futureQtrEstPeriod", Type.D);
	public static final CalcAttrType annualEstimatesPeriod = new CalcAttrType("futureAnnEstPeriod", Type.D);
	public static final CalcAttrType futureQtrAnnDate = new CalcAttrType("futureQtrAnnDate", Type.D);
	public static final CalcAttrType pastQtrAnnDate = new CalcAttrType("pastQtrAnnDate", Type.D);

	public PeriodCalculator() {
		super(true);
	}

	public void calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
	    log.info("Calculating Period Dates...");
		Map<Security, Vector<ReutersAnnDate>> futureQtrs = widget.getEstimatePeriods(secs, PERIOD_QUARTERS, DateType.FUTURE, NUM_OF_PERIODS, asof);
		for (Security sec : secs) {
			Vector<ReutersAnnDate> q = futureQtrs.get(sec);
			for (int i = 0; i < q.size(); i++) {
				cr.add(sec, new DateAttribute(getResName(quarterlyEstimatesPeriod, i), sec, Time.fromYYYYMMDD(q.get(i).period), Time.fromYYYYMMDD(q.get(i).period), asof));
			}
		}

		Map<Security, Vector<ReutersAnnDate>> futureYrs = widget.getEstimatePeriods(secs, PERIOD_YEARS, DateType.FUTURE, NUM_OF_PERIODS, asof);
		for (Security sec : secs) {
			Vector<ReutersAnnDate> a = futureYrs.get(sec);
			for (int i = 0; i < a.size(); i++) {
				cr.add(sec, new DateAttribute(getResName(annualEstimatesPeriod, i), sec, Time.fromYYYYMMDD(a.get(i).period), Time.fromYYYYMMDD(a.get(i).period), asof));
			}
		}
	}

	public static AttrType getResName(AttrType attr, int num) {
		return new CalcAttrType(attr.name + num,Type.D);
	}
}
