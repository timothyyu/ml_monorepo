package ase.util;

public class Triplet<A, B, C> implements Comparable<Triplet<A, B, C>> {
	public final A first;
	public final B second;
	public final C third;

	public Triplet(A a, B b, C c) {
		first = a;
		second = b;
		third = c;
	}

	public String toString() {
		return "[Triplet:(" + first.toString() + ", " + second.toString() + "," + third.toString() + ")]";
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + ((first == null) ? 0 : first.hashCode());
		result = prime * result + ((second == null) ? 0 : second.hashCode());
		result = prime * result + ((third == null) ? 0 : third.hashCode());
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
		Triplet other = (Triplet) obj;
		if (first == null) {
			if (other.first != null)
				return false;
		}
		else if (!first.equals(other.first))
			return false;
		if (second == null) {
			if (other.second != null)
				return false;
		}
		else if (!second.equals(other.second))
			return false;
		if (third == null) {
			if (other.third != null)
				return false;
		}
		else if (!third.equals(other.third))
			return false;
		return true;
	}

	public int compareTo(Triplet<A, B, C> triplet) {
		{
			int k = ((Comparable<A>) first).compareTo(triplet.first);
			if (k > 0)
				return 1;
			if (k < 0)
				return -1;
		}
		{
			int k = ((Comparable<B>) second).compareTo(triplet.second);
			if (k > 0)
				return 1;
			if (k < 0)
				return -1;
		}
		{
			int k = ((Comparable<C>) third).compareTo(triplet.third);
			if (k > 0)
				return 1;
			if (k < 0)
				return -1;
		}
		return 0;
	}

}
