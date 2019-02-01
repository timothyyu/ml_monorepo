package ase.calculator;

import java.util.HashMap;
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

public class GICSCalculator {
	private static final Logger log = LoggerFactory.getLogger(GICSCalculator.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private final UnifiedDataSource uSource;
	private final int days_back;
	private final Exchange.Type primaryExch;
	public static final DbAttrType GIND = new DbAttrType("GINDH", "GIND", 0L, 0L, 3);

	public static final Map<String, String> GICS_INDUSTRIES = new HashMap<String, String>() {
		{
			put("101010", "ENERGY_EQUIP_SVCS");
			put("101020", "OIL_GAS_CONSUMABLE_FUELS");
			put("151010", "CHEMICALS");
			put("151020", "CONSTRUCTION_MATERIALS");
			put("151030", "CONTAINERS_PACKAGING");
			put("151040", "METALS_MINING");
			put("151050", "PAPER_FOREST_PRODS");
			put("201010", "AEROSPACE_DEFENSE");
			put("201020", "BUILDING_PRODS");
			put("201030", "CONSTRUCTION_ENGINEERING");
			put("201040", "ELECTRICAL_EQUIP");
			put("201050", "INDUSTRIAL_CONGLOMERATES");
			put("201060", "MACHINERY");
			put("201070", "TRADING_COMPANIES_DISTRIBUTORS");
			put("202010", "COMMERCIAL_SVCS_SUPP");
			put("203010", "AIR_FREIGHT_LOGISTICS");
			put("203020", "AIRLINES");
			put("203030", "MARINE");
			put("203040", "ROAD_RAIL");
			put("203050", "TRANSPORTATION_INFRASTRUCTURE");
			put("251010", "AUTO_COMP");
			put("251020", "AUTOMOBILES");
			put("252010", "HOUSEHOLD_DURABLES");
			put("252020", "LEISURE_EQUIP_PRODS");
			put("252030", "TEXTILES_APPAREL_LUXURY_GOODS");
			put("253010", "HOTELS_RESTAURANTS_LEISURE");
			put("254010", "MEDIA");
			put("255010", "DISTRIBUTORS");
			put("255020", "INET_CATALOG_RETAIL");
			put("255030", "MULTILINE_RETAIL");
			put("255040", "SPECIALTY_RETAIL");
			put("301010", "FOOD_STAPLES_RETAILING");
			put("302010", "BEVERAGES");
			put("302020", "FOOD_PRODS");
			put("302030", "TOBACCO");
			put("303010", "HOUSEHOLD_PRODS");
			put("303020", "PERSONAL_PRODS");
			put("351010", "HEALTH_EQUIP_SUPP");
			put("351020", "HEALTH_PROV_SVCS");
			put("352010", "BIOTECHNOLOGY");
			put("352020", "PHARMACEUTICALS");
			put("401010", "COMMERCIAL_BANKS");
			put("402010", "DIV_FINL_SVCS");
			put("403010", "INSURANCE");
			put("404010", "REAL_ESTATE");
			put("451010", "INET_SOFTWARE_SVCS");
			put("451020", "IT_SVCS");
			put("451030", "SOFTWARE");
			put("452010", "COMMUNICATIONS_EQUIP");
			put("452020", "COMPUTERS_PERIPHERALS");
			put("452030", "ELEC_EQUIP_INSTRUMENTS_COMP");
			put("452040", "OFFICE_ELECS");
			put("452050", "SEMICONDUCTOR_EQUIP_PRODS");
			put("501010", "DIV_TELCO_SVCS");
			put("501020", "WIRELESS_TELCO_SVCS");
			put("551010", "ELECTRIC_UTILITIES");
			put("551020", "GAS_UTILITIES");
			put("551030", "MULTI-UTILITIES");
			put("551040", "WATER_UTILITIES");
			put("401020", "THRIFTS_MORTGAGE_FINANCE");
			put("402020", "CONSUMER_FINANCE");
			put("402030", "CAPITAL_MARKETS");
			put("453010", "SEMICONDUCTORS_SEMICONDUCTOR_EQUIP");
			put("253020", "DIV_CONSUMER_SVCS");
			put("551050", "INDEPENDENT_POWER_PRODUCERS_ENERGY_TRADERS");
			put("351030", "HEALTH_TECHNOLOGY");
			put("352030", "LIFE_SCIENCES_TOOLS_SVCS");
			put("404020", "REAL_ESTATE_INVESTMENT_TRUSTS_(REITS)");
			put("404030", "REAL_ESTATE_MANAGEMENT_DEVELOPMENT");
			put("202020", "PROFESSIONAL_SVCS");
		}
	};

	public GICSCalculator(UnifiedDataSource uSource, int days_back, Exchange.Type primaryExch) {
		this.uSource = uSource;
		this.days_back = days_back;
		this.primaryExch = primaryExch;
	}

	public Set<AttrType> calculate(FactorLoadings factorLoadings, long asof) throws Exception {
		log.info("Calculating GICS Attributes...");
		Set<Security> secs = factorLoadings.getSecurities();

		long start = Exchange.subtractTradingDays(asof, days_back + 1, primaryExch);
		Map<Security, NavigableMap<Long, Attribute>> gind = uSource.attrSource.getRange(secs, GIND, start, asof);

		Set<AttrType> gicsFactors = new HashSet<AttrType>();

		for (Map.Entry<Security, NavigableMap<Long, Attribute>> e : gind.entrySet()) {
			Security sec = e.getKey();
			for (Map.Entry<Long, Attribute> a : e.getValue().entrySet()) {
				AttrType factor = new CalcAttrType(FactorLoadings.FACTOR_PREFIX + GICS_INDUSTRIES.get(a.getValue().asString()));
				factorLoadings.setFactor(sec, factor, a.getKey(), 1.0);
				gicsFactors.add(factor);
			}
		}

		return gicsFactors;
	}
}
