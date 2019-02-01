package ase.portfolio;

import java.io.IOException;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;

import ase.calculator.Forecast;
import ase.data.Exchange;
import ase.data.Quote;
import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;
import ase.util.math.ASEMath;

public class IdealTrades {
    private static final Logger log = LoggerFactory.getLogger(IdealTrades.class.getName()); 
    private static final ASEFormatter df = ASEFormatter.getInstance();
    
    public final static double DEFAULT_AGGRESSION = 1.0;
    public final static double HIGH_AGGRESSION = 2.0;
    public final static double VERY_HIGH_AGGRESSION = 3.0;
    
    private final Map<Security,OptInfo> portfolio;
    private final Map<Security, Order> orders;
    private Map<Security, Map<Forecast,Double>> mus;
    
    private final Exchange.Type primaryExch;
    
    public final long ts;
    
    public IdealTrades(long ts, int seccnt, Exchange.Type exch) {
        log.info("Creating Ideal Trades for: " + df.format(ts));
        this.ts = ts;
        portfolio = new HashMap<Security,OptInfo>(seccnt);
        orders = new HashMap<Security, Order>(seccnt);
        this.primaryExch = exch;
    }    
        
    public void add(Security sec, OptInfo oi) {
        portfolio.put(sec, oi);
    }
    
    public Map<Security, OptInfo> getPortfolio() {
        return portfolio;
    }
        
    public Collection<Order> getOrders() {
        return orders.values();
    }
    
    public Order getOrder(Security sec) {
        return orders.get(sec);
    }
    
    public double getNotional() {
        double tot = 0.0;
        for ( OptInfo oi : portfolio.values()) {
            tot += Math.abs(oi.target_position);
        }
        return tot;
    }
    
    public void calculateOrders(Portfolio port, Map<Security, Map<Forecast,Double>> mus, Map<Security, Quote> qMap) {
        calculateOrders(port, mus, qMap, 0.0);
    }
    
    public void calculateOrders(Portfolio port, Map<Security, Map<Forecast,Double>> mus, Map<Security, Quote> qMap, double chance_of_high_aggression) {
        this.mus = mus;
        orders.clear();
        
        double totdutil = 0.0, totlong = 0.0, totshort = 0.0, totmu = 0.0, totrisk = 0.0;
        int highAggCnt = 0;
        int vHighAggCnt = 0;
        
        long millisPastMidnight = Time.now() % Time.MILLIS_PER_DAY, orderid = 0;
        
        for(Map.Entry<Security, OptInfo> ent : portfolio.entrySet()) {
            Security sec = ent.getKey();
            OptInfo oi = ent.getValue();
            Position pos = port.getPosition(sec);
            
            int rawShares = (int)(oi.target_position / pos.getLatestPrice() - pos.getIntShares());
            int lotsize = port.getSecurityTradeInfo(sec).lotsize;
            int tradeShares = (int)Math.floor(rawShares / lotsize) * lotsize;
            if ( tradeShares == 0 ) {
                continue;
            }
            
            totdutil += oi.dutil;
            totmu += oi.dmu;
            totrisk += oi.drisk;
            if ( tradeShares > 0 ) {
                totlong += tradeShares;
            }
            else {
                totshort += tradeShares;
            }
            
            Quote q = qMap.get(sec);
            orderid = Order.getUniqOrderid(millisPastMidnight, sec.getSecId());
            double st_mu = ASEMath.BPS_MULTIPLIER * Math.abs(mus.get(sec).get(Forecast.FULL));
//            log.info("STMU: " + sec.getSecId() + "|" + st_mu);
            
            double aggression = DEFAULT_AGGRESSION;
            if (st_mu > 11) {
                highAggCnt++;                
                aggression = HIGH_AGGRESSION;
            } 
            if (st_mu > 35) {
                vHighAggCnt++;
                aggression = VERY_HIGH_AGGRESSION;
            }
            Order order = new Order(orderid, sec, ts, tradeShares, mus.get(sec), oi.dutil, oi.dmu, oi.drisk, oi.eslip, oi.costs, aggression, (q == null ? Double.NaN : q.getPrice()));
            orders.put(sec, order);
        }
        String msg = "Buy dollars: " + df.fformat(totlong) +
              " Sell dollars: " + df.fformat(totshort) +
              " Dutil: " + df.fformat(totdutil) +
              " DMu: " + df.fformat(totmu) +
              " Drisk: " + df.fformat(totrisk) +
              " HighAgg: " + highAggCnt + 
              " VHighAgg: " + vHighAggCnt;  
        log.info(msg);
    }   

    public void dumpIdealPortfolio(String dir, long asof, String name) throws IOException {
        Pair<String,Writer> wr = FileUtils.openDataDumpFile(dir, name, asof, false);
        log.info("Dumping ideal portfolio to: " + wr.first);
        Writer writer = wr.second;
        writer.write("secid|"+OptInfo.dumpHeader()+"\n");
        for ( Map.Entry<Security,OptInfo> ent : getPortfolio().entrySet()) {
            Security sec = ent.getKey();
            writer.write(sec.getSecId()+"|"+ent.getValue()+"\n");
        }
        writer.close();
        FileUtils.finalizeFile(wr.first);
    }
    
    public void dumpOrders(String dir, String name) throws IOException {
        Pair<String,Writer> wr = FileUtils.openDataDumpFile(dir, name, ts, false);
        log.info("Dumping orders to: " + wr.first);
        Writer writer = wr.second;
        writer.write(Order.dumpHeader()+"\n");
        for (Order o : getOrders() ) {
            writer.write(o.dumpOutput());
        }
        writer.close();
        FileUtils.finalizeFile(wr.first);
    }
    
    public void dumpMus(String dir, String name) throws IOException {
        Pair<String,Writer> wr = FileUtils.openDataDumpFile(dir, name, ts, false);
        log.info("Dumping mus to: " + wr.first);
        Writer writer =  wr.second;
        for( Map.Entry<Security, Map<Forecast,Double>> secs : mus.entrySet()) {
            for ( Map.Entry<Forecast, Double> mus : secs.getValue().entrySet() ) {
                writer.write(secs.getKey().getSecId() + "|" + mus.getKey().name + "|" + mus.getValue() + "\n");
            }
        }
        writer.close();
        FileUtils.finalizeFile(wr.first);
    }
}
