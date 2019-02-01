package ase.data;

import java.util.Collections;
import java.util.Vector;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public class Estimate<T> {
	private static final Logger log = LoggerFactory.getLogger(Estimate.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();

	// XXX VERY IMPORTANT: the order is not random: it is used for sorting the flags that fall on the same day (it happens a lot).
	// Note especially the precedence of T over U. In many instances in the db, eg, when inserting reuters historical changes, we get suppresion intervals
	// In such cases, upon termination of the estimate we also mark the end of the suppresion interval with a U. So, T and U will coincide. Based on our
	// sorting T will appear before U.
	public enum FlagType {
		T, N, C, S, U
	};

	public final long orig;
	public final long born;
	public final T value;
	public final Currency currency;
	public Vector<EstimateFlag> flags;

	public Estimate(T value, Currency currency, long orig, long born) {
		this.value = value;
		this.currency = currency;
		this.orig = orig;
		this.born = born;
		this.flags = null;
	}

	public EstimateFlag addFlag(FlagType flag, long orig, long born) {
		if (flags == null) {
			flags = new Vector<EstimateFlag>(5);
		}
		EstimateFlag ef = new EstimateFlag(flag, orig, born);
		flags.add(ef);
		int n = flags.size();
		if (n > 1 && flags.get(n - 2).compareTo(flags.get(n - 1)) > 0) {
			// change the order of the last two elements
			EstimateFlag last = flags.get(n - 1);
			EstimateFlag sec2last = flags.get(n - 2);
			flags.set(n - 1, sec2last);
			flags.set(n - 2, last);
		}
		return ef;
	}

	public void sortAndCompactFlags() {
		Collections.sort(this.flags);
		this.flags.trimToSize();
	}

	public String toString() {
		return "ESTIMATE|" + df.format(orig) + "|" + df.format(mostRecentConfirmation()) + "|" + df.format(born) + "|" + value.toString() + "|" + currency
				+ (isSuppressed() ? "|SUPPRESSED" : "");
	}

	public boolean isSuppressed() {
		if (flags == null) {
			return false;
		}
		boolean suppressed = false;
		for (EstimateFlag f : flags) {
			if (f.flag.equals(FlagType.S)) {
				suppressed = true;
			}
			else if (f.flag.equals(FlagType.U)) {
				suppressed = false;
			}
			else if (f.flag.equals(FlagType.T)) {
				return suppressed;
			}
		}
		return suppressed;
	}

	public long mostRecentConfirmation() {
		if (flags == null) {
			return orig;
		}
		long mostRecent = orig;
		for (EstimateFlag f : flags) {
			if (f.flag.equals(FlagType.C)) {
				mostRecent = f.orig;
			}
		}
		return mostRecent;
	}

	public static class EstimateFlag implements Comparable<EstimateFlag> {
		public final long orig;
		public final long born;
		public final FlagType flag;

		public EstimateFlag(FlagType flag, long orig, long born) {
			this.flag = flag;
			this.orig = orig;
			this.born = born;
		}

		@Override
		public int compareTo(EstimateFlag o) {
			long diff = this.orig - o.orig;
			if (diff < 0) {
				return -1;
			}
			else if (diff > 0) {
				return 1;
			}
			else {
				return flag.compareTo(o.flag);
			}
		}
	}
}
