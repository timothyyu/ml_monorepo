package ase.util;

import ase.util.math.ASEMath;

public class Counter {
    public final String name;
    
    private double sum = 0.0;
    private double sumsq = 0.0;
    private int cnt = 0;
    
    public Counter(String name) {
        this.name = name;
    }
    
    public void add(double d) {
        cnt++;
        sum += d;
        sumsq += d*d;
    }
    
    public String toString() {
        double sigma = ASEMath.sigma(sum, sumsq, cnt);
        return name + " cnt: " + cnt + " mean: " + sum/cnt + " sigma: " + sigma;
    }
}
