package ase.util;

public class Pair<T, S> implements Comparable<Pair<T, S>> {
    public final T first;
    public final S second;

    public Pair(T f, S s) { 
        first = f;
        second = s;   
    }

    public String toString() { 
        return "[Pair:(" + first.toString() + ", " + second.toString() + ")]"; 
    }

    public int hashCode() {
        return first.hashCode() ^ second.hashCode();
    }

    public boolean equals(Object object) {
        if (!(object instanceof Pair) || object == null)
            return false;
        Pair<Object,Object> pair = (Pair<Object,Object>)object;
        return ( first == null ? pair.first == null : first.equals( pair.first ) )
            && ( second == null ? pair.second == null : second.equals( pair.second ) );
    }

    public int compareTo(Pair<T, S> pair) {
        {
            int k = ((Comparable<T>)first).compareTo(pair.first);
            if (k > 0) return 1;
            if (k < 0) return -1;
        }
        {
            int k = ((Comparable<S>)second).compareTo(pair.second);
            if (k > 0) return 1;
            if (k < 0) return -1;
        }
        return 0;
    }

    public static void main( String[] args ) {
        Integer i = new Integer(1);
        Pair<Integer,Integer> p = new Pair<Integer,Integer>(i, i);
        System.out.println("pair is: " + p);
        System.out.println("i is: " + i);
        i++;
        System.out.println("i is: " + i);
        System.out.println("pair is: " + p);
    }
}
