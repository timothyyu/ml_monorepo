package ase.calculator;

import java.util.HashSet;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcAttrType;
import ase.data.DbAttrType;
import ase.data.Exchange;
import ase.data.FactorLoadings;
import ase.data.Security;
import ase.data.UnifiedDataSource;
import ase.util.LoggerFactory;
import ase.util.ASEFormatter;
import ase.util.Pair;
import ase.util.Time;

public class BarraCalculator {
	private static final Logger log = LoggerFactory.getLogger(BarraCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final int days_back;
	private final Exchange.Type primaryExch;

	public static final double BARRA_NO_DATA = -999.0;

	// XXX no need to additionally backfill barra data. Born times for backfills are already pushed into the future.
	private static final long B_MAX_AGE = Time.fromDays(360);
	private static final long B_BACKFILL_OFFSET = 0;

	public static final DbAttrType IND1 = new DbAttrType("INDNAME1", "BINDNAME1", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType IND2 = new DbAttrType("INDNAME2", "BINDNAME2", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType IND3 = new DbAttrType("INDNAME3", "BINDNAME3", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType IND4 = new DbAttrType("INDNAME4", "BINDNAME4", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType IND5 = new DbAttrType("INDNAME5", "BINDNAME5", B_MAX_AGE, B_BACKFILL_OFFSET);

	public static final DbAttrType WT1 = new DbAttrType("WGT1%", "BWGT1%", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType WT2 = new DbAttrType("WGT2%", "BWGT2%", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType WT3 = new DbAttrType("WGT3%", "BWGT3%", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType WT4 = new DbAttrType("WGT4%", "BWGT4%", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType WT5 = new DbAttrType("WGT5%", "BWGT5%", B_MAX_AGE, B_BACKFILL_OFFSET);

	public static final DbAttrType B_GROWTH = new DbAttrType("GROWTH", "BGROWTH", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_VALUE = new DbAttrType("VALUE", "BVALUE", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_VOLTILTY = new DbAttrType("VOLTILTY", "BVOLTILTY", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_MOMENTUM = new DbAttrType("MOMENTUM", "BMOMENTUM", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SIZE = new DbAttrType("SIZE", "BSIZE", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SIZENONL = new DbAttrType("SIZENONL", "BSIZENONL", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_TRADEACT = new DbAttrType("TRADEACT", "BTRADEACT", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_EARNYLD = new DbAttrType("EARNYLD", "BEARNYLD", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_EARNVAR = new DbAttrType("EARNVAR", "BEARNVAR", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_LEVERAGE = new DbAttrType("LEVERAGE", "BLEVERAGE", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_CURRSEN = new DbAttrType("CURRSEN", "BCURRSEN", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_YIELD = new DbAttrType("YIELD", "BYIELD", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_NONESTU = new DbAttrType("NONESTU", "BNONESTU", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SAP500 = new DbAttrType("SAP500", "BSAP500", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SAPVAL = new DbAttrType("SAPVAL", "BSAPVAL", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SAPGRO = new DbAttrType("SAPGRO", "BSAPGRO", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_MIDCAP = new DbAttrType("MIDCAP", "BMIDCAP", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_MIDVAL = new DbAttrType("MIDVAL", "BMIDVAL", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_MIDGRO = new DbAttrType("MIDGRO", "BMIDGRO", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SC600 = new DbAttrType("SC600", "BSC600", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SCVAL = new DbAttrType("SCVAL", "BSCVAL", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_SCGRO = new DbAttrType("SCGRO", "BSCGRO", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_HBTA = new DbAttrType("HBTA", "BHBTA", B_MAX_AGE, B_BACKFILL_OFFSET);
	public static final DbAttrType B_BETA = new DbAttrType("BETA", "BBETA", B_MAX_AGE, B_BACKFILL_OFFSET);

	private static final Set<DbAttrType> barraAttrs = new HashSet<DbAttrType>() {
		{
			add(B_GROWTH);
			add(B_VALUE);
			add(B_VOLTILTY);
			add(B_MOMENTUM);
			add(B_SIZE);
			add(B_SIZENONL);
			add(B_TRADEACT);
			add(B_EARNYLD);
			add(B_EARNVAR);
			add(B_LEVERAGE);
			add(B_CURRSEN);
			add(B_YIELD);
			// add(B_NONESTU);
			add(B_SAP500);
			add(B_SAPVAL);
			add(B_SAPGRO);
			add(B_MIDCAP);
			add(B_MIDVAL);
			add(B_MIDGRO);
			add(B_SC600);
			add(B_SCVAL);
			add(B_SCGRO);
			add(B_HBTA);
			add(B_BETA);
		}
	};

	private static final Set<DbAttrType> barraMonitors = new HashSet<DbAttrType>() {
		{
			add(B_NONESTU);
		}
	};

	public static final Set<String> BARRA_INDUSTRIES = new HashSet<String>() {
		{
			add("MINING");
			add("GOLD");
			add("FOREST");
			add("CHEMICAL");
			add("ENGYRES");
			add("OILREF");
			add("OILSVCS");
			add("FOODBEV");
			add("ALCOHOL");
			add("TOBACCO");
			add("HOMEPROD");
			add("GROCERY");
			add("CONSDUR");
			add("MOTORVEH");
			add("APPAREL");
			add("CLOTHING");
			add("SPLTYRET");
			add("DEPTSTOR");
			add("CONSTRUC");
			add("PUBLISH");
			add("MEDIA");
			add("HOTELS");
			add("RESTRNTS");
			add("ENTRTAIN");
			add("LEISURE");
			add("ENVSVCS");
			add("HEAVYELC");
			add("HEAVYMCH");
			add("INDPART");
			add("ELECUTIL");
			add("GASUTIL");
			add("RAILROAD");
			add("AIRLINES");
			add("TRUCKFRT");
			add("MEDPROVR");
			add("MEDPRODS");
			add("DRUGS");
			add("ELECEQP");
			add("SEMICOND");
			add("CMPTRHW");
			add("CMPTRSW");
			add("DEFAERO");
			add("TELEPHON");
			add("WIRELESS");
			add("INFOSVCS");
			add("INDSVCS");
			add("LIFEINS");
			add("PRPTYINS");
			add("BANKS");
			add("THRIFTS");
			add("SECASSET");
			add("FINSVCS");
			add("INTERNET");
			add("EQTYREIT");
			add("BIOTECH");
		}
	};

	public BarraCalculator(UnifiedDataSource uSource, int days_back, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.days_back = days_back;
		this.primaryExch = primaryExch;
	}

	public Pair<Set<AttrType>, Set<AttrType>> calculate(FactorLoadings factorLoadings, long asof) throws Exception {
		log.info("Calculating Barra Attributes...");
		Set<Security> secs = factorLoadings.getSecurities();
		Set<AttrType> barraFactors = new HashSet<AttrType>();
		Set<AttrType> barraMonitorFactors = new HashSet<AttrType>();
		long t1 = Exchange.subtractTradingDays(asof, days_back + 1, primaryExch);

		Map<Security, NavigableMap<Long, Attribute>> ind1 = uSource.attrSource.getRange(secs, IND1, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> ind2 = uSource.attrSource.getRange(secs, IND2, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> ind3 = uSource.attrSource.getRange(secs, IND3, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> ind4 = uSource.attrSource.getRange(secs, IND4, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> ind5 = uSource.attrSource.getRange(secs, IND5, t1, asof);

		Map<Security, NavigableMap<Long, Attribute>> wt1 = uSource.attrSource.getRange(secs, WT1, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> wt2 = uSource.attrSource.getRange(secs, WT2, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> wt3 = uSource.attrSource.getRange(secs, WT3, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> wt4 = uSource.attrSource.getRange(secs, WT4, t1, asof);
		Map<Security, NavigableMap<Long, Attribute>> wt5 = uSource.attrSource.getRange(secs, WT5, t1, asof);

		for (Security sec : secs) {
			if (ind1.get(sec) == null) {
				log.warning("Could not find primary industry for " + sec.getSecId() + " on " + df.format(t1));
				continue;
			}
			putBarraIndFac(factorLoadings, sec, ind1.get(sec), wt1.get(sec), barraFactors);
			putBarraIndFac(factorLoadings, sec, ind2.get(sec), wt2.get(sec), barraFactors);
			putBarraIndFac(factorLoadings, sec, ind3.get(sec), wt3.get(sec), barraFactors);
			putBarraIndFac(factorLoadings, sec, ind4.get(sec), wt4.get(sec), barraFactors);
			putBarraIndFac(factorLoadings, sec, ind5.get(sec), wt5.get(sec), barraFactors);
		}

		for (DbAttrType barraAttr : barraAttrs) {
			Map<Security, NavigableMap<Long, Attribute>> bMap = uSource.attrSource.getRange(secs, barraAttr, t1, asof);
			CalcAttrType facAttr = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + barraAttr.name);
			for (Security sec : secs) {
				NavigableMap<Long, Attribute> attrMap = bMap.get(sec);
				for (Attribute attr : attrMap.values()) {
					if (attr != null && attr.asDouble() != BARRA_NO_DATA) {
						factorLoadings.setFactor(sec, facAttr, attr.date, attr.asDouble());
					}
				}
			}
			barraFactors.add(facAttr);
		}

		for (DbAttrType barraAttr : barraMonitors) {
			Map<Security, NavigableMap<Long, Attribute>> bMap = uSource.attrSource.getRange(secs, barraAttr, t1, asof);
			CalcAttrType facAttr = new CalcAttrType(FactorLoadings.MONITOR_FACTOR_PREFIX + barraAttr.name);
			for (Security sec : secs) {
				NavigableMap<Long, Attribute> attrMap = bMap.get(sec);
				for (Attribute attr : attrMap.values()) {
					if (attr != null && attr.asDouble() != BARRA_NO_DATA) {
						factorLoadings.setFactor(sec, facAttr, attr.date, attr.asDouble());
					}
				}
			}
			barraMonitorFactors.add(facAttr);
		}

		return new Pair<Set<AttrType>, Set<AttrType>>(barraFactors, barraMonitorFactors);
	}

	private void putBarraIndFac(FactorLoadings factorLoadings, Security sec, NavigableMap<Long, Attribute> indMap, NavigableMap<Long, Attribute> wtMap,
			Set<AttrType> barraGroups) {
		for (Attribute ind : indMap.values()) {
			if (ind == null || ind.asString().length() < 1) {
				return;
			}
			Attribute wt = wtMap.get(ind.date);
			if (wt == null) {
				log.warning("Could not look up ind weighting for " + sec.getSecId() + " on " + ind);
			}
			AttrType type1 = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + ind.asString());
			factorLoadings.setFactor(sec, type1, ind.date, wt.asDouble() / 100.0);
			barraGroups.add(type1);
		}
	}
}
