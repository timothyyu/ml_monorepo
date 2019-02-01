package ase.calculator;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Collection;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.AttrType;
import ase.data.Attribute;
import ase.data.CalcResults;
import ase.data.Exchange;
import ase.data.Security;
import ase.util.CollectionUtils;
import ase.util.LoggerFactory;
import ase.util.Time;

public class Forecast {
    public enum Type { MU, RVAR, NONE };

    public static final double DEFAULT_BOUND = 100.0; //bps
    private static final int HOURS = 7;
    
    public static final Forecast FULL = new Forecast("FULL", Forecast.Type.MU);
    public static final Forecast NONE = new Forecast("NONE", Forecast.Type.NONE);
    
    private static final Logger log = LoggerFactory.getLogger(Forecast.class.getName());

    public final String name;
    public final Type type;
    public final double horizon;
    public final double weight;
    public final double bound;
    private final Map<AttrType, Vector<Double>> components = new HashMap<AttrType, Vector<Double>>();

    public Forecast(String name, Type type, String def) {
        log.info("Initializing " + name + " forecast as " + def);
        this.name = name;
        this.type = type;
        double weight = 0.0;
        double horizon = 0.0;
        double bound = DEFAULT_BOUND;
        
        String[] defs = def.split(" ");
        for ( int ii=0; ii < defs.length; ii++ ) {
            if ( "weight".equals(defs[ii]) ) 
                weight = Double.parseDouble(defs[++ii]);
            else if ( "horizon".equals(defs[ii]) ) 
                horizon = Double.parseDouble(defs[++ii]);
            else if ( "bound".equals(defs[ii]))
                bound = Double.parseDouble(defs[++ii]);
            else
                components.put(new AttrType(defs[ii]), loadCoefs(defs[++ii]));
        }
        
        this.weight = weight;
        this.horizon = horizon;
        this.bound = bound / 10000.0;
    }
    
    public Forecast(String name, Type type) {
        this.name = name;
        this.type = type;
        this.horizon = 0.0;
        this.weight = 0.0;
        this.bound = DEFAULT_BOUND / 10000.0;
    }
    
    private static Vector<Double> loadCoefs(String defs) {
        Vector<Double> res = new Vector<Double>(6);
        if (defs.contains(",")) {
            String[] coefs = defs.split(",");
            assert coefs.length == HOURS;
            for (int ii =0; ii < coefs.length; ii++) {
                res.add(new Double(coefs[ii]));
            }
        }
        else {
            for (int ii = 0; ii < HOURS; ii++) {
                res.add(new Double(defs));
            }
        }
        return res;
    }
    
    public boolean isFull() {
        return this.equals(FULL);
    }

    //returns scaled and weighted forecast
    public Map<Security,Double> calculate(CalcResults calcres, double calchorizon) {
        //XXX hack for now...
        int hour = Time.millis2hour(calcres.getAsOf(), Exchange.Type.NYSE);
        if (hour < 0) {
            log.info("Before open, not calculating forecast");
            return null;
        }
        return calculate(calcres, calchorizon, hour);
    }
    
    public Map<Security,Double> calculate(CalcResults calcres, double calchorizon, int hour) {
        assert hour <= HOURS;
        double horizon_mult = calchorizon/Math.max(calchorizon,horizon);
        Map<Security,Double> res = new HashMap<Security,Double>();
        for (Map.Entry<AttrType,Vector<Double>> comp : components.entrySet()) {
            AttrType component = comp.getKey();
            double coef = comp.getValue().get(hour);
            log.info("Calculating " + component + " at hour " + hour + " with " + coef);
            Map<Security,Attribute> attrMap = calcres.getResult(component);
            if ( attrMap.size() == 0 ) {
                log.severe("Error calculating " + name + ", missing component " + component);
            }
            for (Map.Entry<Security,Attribute> attribute : attrMap.entrySet()) {
                double term = attribute.getValue().asDouble() * coef * horizon_mult * weight;
                Security sec = attribute.getKey();
                Double dbl = res.get(sec);
                if (Double.isNaN(term)) {
                    log.severe("Computed NaN forecast for " + sec.getSecId() + " with " + attribute.getValue());
                    term = 0.0;
                }
                if (dbl == null) {
                    res.put(sec, term);
                }
                else {
                    res.put(sec, dbl + term);
                }
            }
        }
        //bound that shit
        for (Security sec : res.keySet()) {
            Double val = res.get(sec);
            if (val > bound) {
                log.severe("Bounding forecast " + name + " on " + sec.getSecId() + " of " + val);
                res.put(sec, bound);
            }
            else if (val < -bound) {
                log.severe("Bounding forecast " + name + " on " + sec.getSecId() + " of " + val);
                res.put(sec, -bound);
            }
        }
        return res;
    }
    
    public static Collection<Forecast> loadDefs(String configfile) throws IOException {
        Properties config = new Properties();
        config.load(new FileReader(configfile));
        return loadDefs(config);
    }
    
    public static Collection<Forecast> loadDefs(Properties config) {
        Collection<Forecast> res = new Vector<Forecast>();
        for( Enumeration e = config.propertyNames(); e.hasMoreElements(); ) {
            String prop = (String)e.nextElement();
            if (prop.startsWith("fc_")) {
                res.add(new Forecast(prop, Type.MU, config.getProperty(prop)));
            }
            else if (prop.startsWith("rvar_")) {
                res.add(new Forecast(prop, Type.RVAR, config.getProperty(prop)));
            }
        }
        return res;
    }
    
    public static Map<Security, Map<Forecast, Double>> calculateMus(CalcResults calcres, Collection<Forecast> forecasts, Collection<Forecast> disabledForecasts, double horizon, int hour) {
        Map<Security, Map<Forecast, Double>> mus = new HashMap<Security, Map<Forecast, Double>>(calcres.getSecurities().size());

        // init the totat mus
        for (Security sec : calcres.getSecurities()) {
            Map<Forecast, Double> fc = new HashMap<Forecast, Double>(forecasts.size());
            fc.put(Forecast.FULL, new Double(0.0));
            mus.put(sec, fc);
        }

        for (Forecast forecast : forecasts) {
            if (disabledForecasts != null && disabledForecasts.contains(forecast))
                continue;
            if (forecast.type == Forecast.Type.MU) {
                log.info("Calculating model: " + forecast.name);

                Map<Security, Double> aforecast = forecast.calculate(calcres, horizon, hour);
                for (Map.Entry<Security, Double> sf : aforecast.entrySet()) {
                    Map<Forecast, Double> secmus = mus.get(sf.getKey());
                    Double dbl = sf.getValue();
                    if (dbl != null && !dbl.isNaN()) {
                        secmus.put(forecast, dbl);
                        Double tot = secmus.get(Forecast.FULL);
                        secmus.put(Forecast.FULL, tot + dbl);
                    }
                }
            }
        }
        return mus;
    }
    
    public static Map<Security, Double> calculateRvars(CalcResults calcres, Collection<Forecast> forecasts, Collection<Forecast> disabledForecasts, double horizon) {
        Map<Security, Double> res = new HashMap<Security, Double>(calcres.getSecurities().size());
        for (Forecast forecast : forecasts) {
            if (disabledForecasts.contains(forecast))
                continue;
            if (forecast.type == Forecast.Type.RVAR) {
                log.info("Calculating model: " + forecast.name);
                Map<Security, Double> aforecast = forecast.calculate(calcres, horizon, 0);
                CollectionUtils.addDoubleMap(res, aforecast);
            }
        }
        return res;
    }
    
    public String toString() {
        return name+"|"+type+"|"+CollectionUtils.toString(components);
    }
    
    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((name == null) ? 0 : name.hashCode());
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        Forecast other = (Forecast) obj;
        if (name == null) {
            if (other.name != null)
                return false;
        } else if (!name.equals(other.name))
            return false;
        return true;
    }
    
    public static void main(String[] argv) throws Exception {
        String calcresFile = argv[0];
        Collection<Forecast> forecasts = Forecast.loadDefs(argv[1]);
        double horizon = Double.parseDouble(argv[2]);
        CalcResults cr = CalcResults.restore(new File(calcresFile));
         
        int hour = 0;
        Map<Security, Map<Forecast, Double>> mus = Forecast.calculateMus(cr, forecasts, null, horizon, hour); 
        for (Security sec : mus.keySet()) {
            Map<Forecast,Double> map = mus.get(sec);
            for(Map.Entry<Forecast, Double> ent : map.entrySet()) {
                System.out.println(sec.getSecId()+"|"+ent.getKey().name+"|"+ent.getValue().toString());
            }
        }
    }

}
