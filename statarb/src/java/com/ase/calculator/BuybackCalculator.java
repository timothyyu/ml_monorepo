package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.Time;
import ase.util.LoggerFactory;

public class BuybackCalculator {
	private static final Logger log = LoggerFactory.getLogger(BuybackCalculator.class.getName());

	//XXX assume that backfilled data where learnt the next day
	public static final DbAttrType BUYBACK = new DbAttrType("BUYBACK", "BUYBACK", Time.fromDays(365), Time.fromDays(1));
	public static final CalcAttrType bbAttr = new CalcAttrType("Buyback");

	private final UnifiedDataSource uSource;

	public BuybackCalculator(UnifiedDataSource uSource) {
		this.uSource = uSource;
	}

	public Set<AttrType> calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		Set<AttrType> res = new HashSet<AttrType>();
		Map<Security, Attribute> bbMap = uSource.attrSource.getAttrAsOf(secs, BUYBACK, asof);
		int cnt = 0;
		for (Security sec : bbMap.keySet()) {
			Attribute bb = bbMap.get(sec);

			// XXX need to parse string value in the future...
			cr.add(sec, bbAttr, bb.date, 1.0);
			cnt++;
		}
		log.info("Calculated " + cnt + " of " + bbAttr.name);
		
		AttrType bb_d10 = DecayCalculator.calculate(cr, bbAttr, asof, Time.fromDays(10), 3);
		AttrType bb_d5 = DecayCalculator.calculate(cr, bbAttr, asof, Time.fromDays(5), 3);
		
		return res;
	}
}
