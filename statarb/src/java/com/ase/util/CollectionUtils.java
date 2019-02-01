package ase.util;

import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.Vector;

import ase.calculator.Forecast;

public class CollectionUtils {
    
    public static String toString(Object[] a) {
        int i = 0;
        String str = "{ARRAY: [ ";
        while ( i < a.length ) {
            str = str + a[i++] + ",";
        }
        return str.substring(0, str.length()-1) + "]}";
    }

    public static <K,V> String toString(Map<K,V> map) {
        String res = "";
        for( Map.Entry<K,V> ent : map.entrySet() ) {
            res+=ent.getKey()+":"+ent.getValue();
        }
        return res;
    }

    public static <K,V> Map<V, Collection<K>> partition(Map<K, V> map) {
        Map<V, Collection<K>> res = new HashMap<V,Collection<K>>();
        for( Map.Entry<K, V> ent : map.entrySet() ) {
            Collection<K> set =  res.get(ent.getValue());
            if ( set == null ) {
                res.put(ent.getValue(), set = new HashSet<K>());
            }
            set.add(ent.getKey());
        }
        return res;
    }

    public static <T> Set<T> toSet(T a) {
        Set<T> s = new HashSet<T>();
        s.add(a);
        return s;
    }
    
    public static <T> Set<T> toSet(T[] a) {
        Set<T> s = new HashSet<T>(a.length+1);
        for (int ii=0; ii<a.length; ii++) {
            s.add(a[ii]);
        }
        return s;
    }
    
    public static double[] toDoubleArray(Collection<? extends INumber> dbls) {
        double[] res = new double[dbls.size()];
        int ii = 0;
        for (INumber num : dbls) {
            res[ii++] = num.asDouble(); 
        }
        return res;
    }
    
    public static <K,V> Pair<K,V>[] mapToArray(Map<K, V> aMap) {
        Vector<Pair<K,V>> res = new Vector<Pair<K,V>>(aMap.size());
        for( Map.Entry<K, V> ent : aMap.entrySet()) {
            res.add(new Pair<K,V>(ent.getKey(), ent.getValue()));
        }
        return res.toArray(new Pair[0]);
    }
    
    public static Pair<String,Forecast>[] mapToArray2(Map<String, Forecast> aMap) {
        Vector<Pair<String,Forecast>> res = new Vector<Pair<String,Forecast>>(aMap.size());
        for( Map.Entry<String, Forecast> ent : aMap.entrySet()) {
            res.add(new Pair<String,Forecast>(ent.getKey(), ent.getValue()));
        }
        return res.toArray(new Pair[0]);
    }
    
    public static <T> void addDoubleMap(Map<T,Double> to, Map<T,Double> from) {
        for (Map.Entry<T, Double> ent : from.entrySet()) {
            Double dbl = to.get(ent.getKey());
            if ( dbl == null) {
                to.put(ent.getKey(), new Double(ent.getValue()));
            }
            else {
                to.put(ent.getKey(), new Double(dbl.doubleValue() + ent.getValue()));
            }
        }
    }
}
