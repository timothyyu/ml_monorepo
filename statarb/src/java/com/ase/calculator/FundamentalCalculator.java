package ase.calculator;

import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.CalcResults;
import ase.data.DbAttrType;
import ase.data.Security;
import ase.data.StringAttribute;
import ase.data.UnifiedDataSource;
import ase.util.ASEFormatter;
import ase.util.LoggerFactory;
import ase.util.Time;

public class FundamentalCalculator {
	private static final Logger log = LoggerFactory.getLogger(FundamentalCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private static final int FUND_LOOKBACK_DAYS = 200;

	private static final long CS_BF_OFFSET = Time.fromDays(30);
	public static final DbAttrType QUARTER = new DbAttrType("FQTR", "FQTR", 0L, CS_BF_OFFSET, 3);
	public static final DbAttrType ASSETS = new DbAttrType("ATQ", "ATQ", Time.fromDays(FUND_LOOKBACK_DAYS), CS_BF_OFFSET, 3);
	public static final DbAttrType INCOME = new DbAttrType("IBQ", "IBQ", Time.fromDays(FUND_LOOKBACK_DAYS), CS_BF_OFFSET, 3);
	public static final DbAttrType SALES = new DbAttrType("SALEQ", "SALEQ", Time.fromDays(FUND_LOOKBACK_DAYS), CS_BF_OFFSET, 3);
	public static final DbAttrType CASHFLOW = new DbAttrType("OANCFY", "OANCFY", Time.fromDays(FUND_LOOKBACK_DAYS), CS_BF_OFFSET, 3);

	public static final AttrType E2P = new CalcAttrType("e2p");
	public static final AttrType S2P = new CalcAttrType("s2p");
	public static final AttrType C2A = new CalcAttrType("c2a");

	private final UnifiedDataSource uSource;

	public FundamentalCalculator(UnifiedDataSource uSource) {
		this.uSource = uSource;
	}

	public void calculate(CalcResults cr, Set<Security> secs, long asof) throws Exception {
		log.info("Calculating Fundamental attributes");
		Map<Security, Attribute> sec2ass = uSource.attrSource.getAttrAsOf(secs, ASSETS, asof);
		Map<Security, Attribute> sec2sales = uSource.attrSource.getAttrAsOf(secs, SALES, asof);
		Map<Security, Attribute> sec2inc = uSource.attrSource.getAttrAsOf(secs, INCOME, asof);
		Map<Security, NavigableMap<Long, Attribute>> sec2cf = uSource.attrSource.getRange(secs, CASHFLOW, asof - Time.fromDays(FUND_LOOKBACK_DAYS), asof);
		Map<Security, NavigableMap<Long, Attribute>> sec2qtrs = uSource.attrSource.getRange(secs, QUARTER, asof - Time.fromDays(FUND_LOOKBACK_DAYS), asof);
		Map<Security, NavigableMap<Long, Attribute>> sec2cap = uSource.attrSource.getRange(secs, PassThruCalculator.CAP,
				asof - Time.fromDays(FUND_LOOKBACK_DAYS), asof);

		for (Security sec : secs) {
			Attribute incAttr = sec2inc.get(sec);
			if (incAttr == null) {
				log.warning("No Income for: " + sec.getSecId() + ", date: " + df.format(asof));
			}
			double income = (incAttr == null) ? Double.NaN : incAttr.asDouble();
			long incomeDate = (incAttr == null) ? Long.MIN_VALUE : incAttr.date;

			// double capAtIncomeDate = Double.NaN;
			double capNow = Double.NaN;
			if (incAttr != null) {
				// Map.Entry<Long, Attribute> incCapAttr = sec2cap.get(sec).floorEntry(incomeDate);
				// if (incCapAttr == null) {
				// log.warning("No MktCap for: " + sec + ", date: " + df.format(incomeDate));
				// }
				// capAtIncomeDate = (incCapAttr == null) ? Double.NaN : incCapAttr.getValue().asDouble() / 1e6;

				Map.Entry<Long, Attribute> incCapAttr = sec2cap.get(sec).floorEntry(asof);
				if (incCapAttr == null) {
					log.warning("No MktCap for: " + sec + ", date: " + df.format(incomeDate));
				}
				capNow = (incCapAttr == null) ? Double.NaN : incCapAttr.getValue().asDouble() / 1e6;
			}
			cr.add(sec, E2P, asof, income / capNow);
			// XXX switch to this one...
			// cr.add(sec, E2P, incomeDate, income / capAtIncomeDate);

			// /////////////////////////////////////////////////

			Attribute salesAttr = sec2sales.get(sec);
			if (salesAttr == null) {
				log.warning("No Sales for: " + sec.getSecId() + ", date: " + df.debugFormat(asof));
			}
			double sales = (salesAttr == null) ? Double.NaN : salesAttr.asDouble();
			// long salesDate = (salesAttr == null) ? Long.MIN_VALUE : salesAttr.date;

			// double capAtSalesDate = Double.NaN;

			// if (salesAttr != null) {
			// Map.Entry<Long, Attribute> salesCapAttr = sec2cap.get(sec).floorEntry(salesDate);
			// if (salesCapAttr == null) {
			// log.warning("No MktCap for: " + sec + ", date: " + df.format(salesDate));
			// }
			// capAtSalesDate = (salesCapAttr == null) ? Double.NaN : salesCapAttr.getValue().asDouble() / 1e6;
			// }
			cr.add(sec, S2P, asof, sales / capNow);
			// cr.add(sec, S2P, salesDate, sales / capAtSalesDate);

			// /////////////////////////////////////////////////
			// /XXX Nikos: a bit farfetched but perhaps we need to check whether the dates involves match

			NavigableMap<Long, Attribute> qtrMap = sec2qtrs.get(sec);
			if (qtrMap == null) {
				log.warning("No FQTR for: " + sec + ", date: " + df.format(asof));
			}

			Attribute assAttr = sec2ass.get(sec);
			if (assAttr == null) {
				log.warning("No Assets for: " + sec.getSecId() + ", date: " + df.debugFormat(asof));
			}
			double assets = (assAttr == null) ? Double.NaN : assAttr.asDouble();

			Map.Entry<Long, Attribute> ent = sec2cf.get(sec).pollLastEntry();
			if (ent == null)
				continue;
			Attribute cf2 = ent.getValue();

			ent = sec2cf.get(sec).pollLastEntry();
			if (ent == null)
				continue;
			Attribute cf1 = ent.getValue();

			ent = sec2qtrs.get(sec).floorEntry(cf2.date);
			if (ent == null)
				continue;
			int d2 = Integer.parseInt(((StringAttribute) ent.getValue()).value);

			ent = sec2qtrs.get(sec).floorEntry(cf1.date);
			if (ent == null)
				continue;
			int d1 = Integer.parseInt(((StringAttribute) ent.getValue()).value);

			// if we're diffing in the same fiscal year. not sure this is right
			if (d2 > d1) {
				cr.add(sec, C2A, cf2.date, (cf2.asDouble() - cf1.asDouble()) / assets);
			}
			else {
				cr.add(sec, C2A, cf2.date, cf2.asDouble() / assets);
			}
		}

		AttrType e2p_GA = GaussianAdjustCalculator.calculate(cr, E2P, 0.0, 1.0, 5.0);
		AttrType s2p_GA = GaussianAdjustCalculator.calculate(cr, S2P, 0.0, 1.0, 5.0);
		AttrType c2a_GA = GaussianAdjustCalculator.calculate(cr, C2A, 0.0, 1.0, 5.0);
		AttrType e2p_GA_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, e2p_GA);
		AttrType s2p_GA_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, s2p_GA);
		AttrType c2a_GA_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, c2a_GA);
		AttrType e2p_GA_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, e2p_GA);
		AttrType s2p_GA_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, s2p_GA);
		AttrType c2a_GA_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, c2a_GA);

		BoundingCalculator bcalc = new BoundingCalculator(BoundingCalculator.Mode.SIGMA);
		AttrType e2p_B = bcalc.calculate(cr, E2P, 5.0);
		AttrType s2p_B = bcalc.calculate(cr, S2P, 5.0);
		AttrType c2a_B = bcalc.calculate(cr, C2A, 5.0);
		AttrType e2p_B_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, e2p_B);
		AttrType s2p_B_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, s2p_B);
		AttrType c2a_B_MAB = GroupMeanAdjustCalculator.calculate(cr, BarraCalculator.IND1, c2a_B);
		AttrType e2p_B_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, e2p_B);
		AttrType s2p_B_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, s2p_B);
		AttrType c2a_B_MAS = GroupMeanAdjustCalculator.calculate(cr, PassThruCalculator.SIC, c2a_B);
	}
}
