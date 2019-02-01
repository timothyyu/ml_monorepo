package ase.data;

import java.io.BufferedReader;
import java.io.File;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.Vector;
import java.util.logging.Logger;

import ase.calculator.FactorCalculator;
import ase.data.widget.SQLSecurityWidget;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;

//Need to implement a "dirty data" structure to minimize recalculation
public class CalcResults {
	private static final Logger log = LoggerFactory.getLogger(CalcResults.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private long asof;

	//i don't reall like these partitions here...
	public final Map<AttrType, Map<String, Collection<Security>>> partitions = new HashMap<AttrType, Map<String, Collection<Security>>>();
	// I think Attributes may be better sorted in a TreeSet...
	private final Map<Security, Map<AttrType, Vector<Attribute>>> results = new HashMap<Security, Map<AttrType, Vector<Attribute>>>();
	private final Map<Pair<AttrType, AttrType>, Double> factorCov = new HashMap<Pair<AttrType, AttrType>, Double>();

	public CalcResults(long asof) {
		this.asof = asof;
	}

	public String name() {
		return df.format(asof);
	}

	public long getAsOf() {
		return asof;
	}

	public void setAsOf(long asof) {
		this.asof = asof;
	}

	public boolean add(Security sec, AttrType type, long date, double val) {
		if (Double.isNaN(val))
			return false;
		add(sec, new NumericAttribute(type, sec, date, val, asof));
		return true;
	}

	public void add(Security sec, Attribute attr) {
		if (!results.containsKey(sec)) {
			results.put(sec, new HashMap<AttrType, Vector<Attribute>>());
		}
		Map<AttrType, Vector<Attribute>> types = results.get(sec);
		if (!types.containsKey(attr.type)) {
			types.put(attr.type, new Vector<Attribute>());
		}
		Vector<Attribute> attrs = types.get(attr.type);

		// only insert attr if it differs
		if (attrs.size() == 0 || !attrs.lastElement().equals(attr)) {
			attrs.add(attr);
		}
	}
	
	public void add(Map<Security, Attribute> attrMap) {
	    for (Map.Entry<Security, Attribute> ent : attrMap.entrySet()) {
	        add(ent.getKey(), ent.getValue());
	    }
	}

	public void addPartition(AttrType name, Map<String, Collection<Security>> mapping) {
		partitions.put(name, mapping);
	}

	public void addFactorCov(AttrType name1, AttrType name2, Double val) {
		factorCov.put(new Pair<AttrType, AttrType>(name1, name2), val);
	}

	public void addFactorReturn(AttrType factor, long date, double val) {
		add(Security.FACTOR_SEC, new NumericAttribute(factor, Security.FACTOR_SEC, date, val, asof));
	}

	public Map<Security, Attribute> getResult(AttrType name) {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>(results.size());
		int cnt = 0;
		for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> it : results.entrySet()) {
			Map<AttrType, Vector<Attribute>> mmap = it.getValue();
			if (mmap.containsKey(name)) {
			    Attribute a = it.getValue().get(name).lastElement();
			    res.put(it.getKey(), a);
			    cnt++;
			}
		}
		log.info("Returning " + cnt + " attributes for " + name);
		return res;
	}
	
	//clear attributes and return current values
	public Map<Security, Attribute> clearResult(AttrType name) {
		Map<Security, Attribute> res = new HashMap<Security, Attribute>(results.size());
		int cnt = 0;
		for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> it : results.entrySet()) {
			Map<AttrType, Vector<Attribute>> mmap = it.getValue();
			Vector<Attribute> values = mmap.remove(name);
			if (values != null) {
			    Attribute a = values.lastElement();
			    res.put(it.getKey(), a);
			    cnt++;
			}
		}
		log.info("Cleared " + cnt + " attributes for " + name);
		return res;
	}
	
	public Map<Security, Vector<Attribute>> getResultHist(AttrType name) {
	    Map<Security, Vector<Attribute>> res = new HashMap<Security, Vector<Attribute>>(results.size());
        int cnt = 0;
        for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> it : results.entrySet()) {
            Map<AttrType, Vector<Attribute>> mmap = it.getValue();
            if (mmap.containsKey(name)) {
                Vector<Attribute> a = it.getValue().get(name);                
                res.put(it.getKey(), a);
                cnt += a.size();
            }
        }
        log.info("Returning " + cnt + " attributes for " + name);
        return res;
	}

	public Collection<Attribute> getSecurityAttributes(Security sec) {
		Collection<Attribute> res = new Vector<Attribute>();
		results.get(sec);
		return res;
	}

	public Map<Security, Map<AttrType, Attribute>> getFactorExposures(boolean includeRegularFactors, boolean includeMonitorFactors) {
		assert includeRegularFactors || includeMonitorFactors;
		Map<Security, Map<AttrType, Attribute>> res = new HashMap<Security, Map<AttrType, Attribute>>(results.size());
		for (Security sec : results.keySet()) {
			res.put(sec, new HashMap<AttrType, Attribute>());
		}
		for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> secMap : results.entrySet()) {
			for (Map.Entry<AttrType, Vector<Attribute>> fMap : secMap.getValue().entrySet()) {
				if (includeRegularFactors && fMap.getKey().name.startsWith(FactorLoadings.FACTOR_PREFIX) ) {
					res.get(secMap.getKey()).put(fMap.getKey(), fMap.getValue().lastElement());
				}
				else if (includeMonitorFactors && fMap.getKey().name.startsWith(FactorLoadings.MONITOR_FACTOR_PREFIX)){
					res.get(secMap.getKey()).put(fMap.getKey(), fMap.getValue().lastElement());
				}
			}
		}
		return res;
	}

	public Map<Security, Map<AttrType, Attribute>> getAllExposures() {
	    Map<Security, Map<AttrType, Attribute>> res = new HashMap<Security, Map<AttrType, Attribute>>(results.size());
	    for (Security sec : results.keySet()) {
	        res.put(sec, new HashMap<AttrType, Attribute>());
	    }
	    for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> secMap : results.entrySet()) {
	        for (Map.Entry<AttrType, Vector<Attribute>> fMap : secMap.getValue().entrySet()) {
	            if (fMap.getKey().datatype == AttrType.Type.N ) {
	                res.get(secMap.getKey()).put(fMap.getKey(), fMap.getValue().lastElement());
	            }
	        }
	    }
	    return res;
	}
	
	@Deprecated
	public int getFactorCount() {
		int n = factorCov.size();
		return (-1+(int)Math.sqrt(1+8*n))/2;
	}
	
	public int getFactorCount(boolean includeRegularFactors,boolean includeMonitorFactors) {
		assert includeRegularFactors || includeMonitorFactors;
		return getFactors(includeRegularFactors, includeMonitorFactors).size();
	}

	public Set<AttrType> getFactors(boolean includeRegularFactors, boolean includeMonitorFactors) {
		assert includeRegularFactors || includeMonitorFactors;
		TreeSet<AttrType> factors = new TreeSet<AttrType>();
		
		for (Map<AttrType, Vector<Attribute>> sa : results.values()) {
			for (AttrType a : sa.keySet()) {
				if ((includeRegularFactors && a.name.startsWith(FactorLoadings.FACTOR_PREFIX)) || (includeMonitorFactors && a.name.startsWith(FactorLoadings.MONITOR_FACTOR_PREFIX))) {
					factors.add(a);
				}
			}
		}
		return factors;
	}

	public Iterator<Map.Entry<Pair<AttrType, AttrType>, Double>> getFactorCov() {
		return factorCov.entrySet().iterator();
	}

	public Set<Security> getSecurities() {
		Set<Security> res = new HashSet<Security>(results.size());
		res.addAll(results.keySet());
		res.remove(Security.FACTOR_SEC);
		return res;
	}

	public void dump(Writer writer) throws Exception {
		for (Map.Entry<Security, Map<AttrType, Vector<Attribute>>> aa : results.entrySet()) {
			for (Map.Entry<AttrType, Vector<Attribute>> bb : aa.getValue().entrySet()) {
				writer.write(bb.getValue().lastElement() + "\n");
				// XXX why do I even keep these vectors around?????
				// for( Attribute attr : bb.getValue() ) {
				// writer.write(attr+"\n");
				// }
			}
		}
		for (Map.Entry<Pair<AttrType, AttrType>, Double> ent : factorCov.entrySet()) {
			writer.write("FCOV|" + ent.getKey().first + "|" + ent.getKey().second + "|" + ent.getValue() + "\n");
		}
	}

	public static CalcResults restore(File file, long asof) throws Exception {
		CalcResults res = new CalcResults(asof);
		BufferedReader reader = FileUtils.openZipReader(file);
		int cnt = 0;
		for (String line = ""; line != null; line = reader.readLine()) {
			if (line.length() <= 0)
				continue;
			if (line.startsWith("FCOV")) {
				String[] fields = line.split("\\|");
				res.addFactorCov(new AttrType(fields[1]), new AttrType(fields[2]), Double.parseDouble(fields[3]));
			}
			else {
				int pos = line.indexOf("|");
				Security sec = new Security(Integer.parseInt(line.substring(0, pos)));
				Attribute attr = Attribute.restore(line);
				res.add(sec, attr);
			}
			cnt++;
		}
		log.info("Loaded " + cnt + " lines at " + df.format(asof));
		return res;
	}

	public static CalcResults restore(File file) throws Exception {
		long asof = FileUtils.getFileTs(file.getName(), FileUtils.CALCRES_PATTERN);
		return CalcResults.restore(file, asof);
	}

	@Deprecated
	public static CalcResults restoreOld(String filename, long calcts) throws Exception {
		CalcResults res = new CalcResults(calcts);
		BufferedReader reader = FileUtils.openZipReader(filename);
		Map<String, Security> cache = new HashMap<String, Security>();
		SQLSecurityWidget sql = SQLSecurityWidget.instance();

		for (String line = ""; line != null; line = reader.readLine()) {
			String[] fields = line.split("\\|");
			long calctime = Long.parseLong(fields[0]);
			Security sec = cache.get(fields[1] + fields[2]);
			if (sec == null) {
				try {
					Vector<Security> secs = sql.getStock(Integer.parseInt(fields[1]), fields[2], calctime);
					if (secs.size() > 1)
						log.warning("More than one security found for: " + line);
					cache.put(fields[1] + fields[2], sec = secs.firstElement());
				}
				catch (Exception e) {
					log.warning("Unable to look up security: " + line);
					continue;
				}
			}
			res.add(sec, new NumericAttribute(new AttrType(fields[3]), sec, Long.parseLong(fields[4]), Double.parseDouble(fields[5]), -1L));
		}
		return res;
	}
}
