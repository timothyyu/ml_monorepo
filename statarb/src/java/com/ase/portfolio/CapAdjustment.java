package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.util.List;
import java.util.Vector;
import java.util.logging.Logger;

import ase.data.Security;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;

public class CapAdjustment {
	public enum Type {
		DIV, SPLIT, FILL, LIQ, CORP_CASH, CORP_SHARES, CASHEQ
	};

	public enum SizeRefType {
		SELF, SECID, ABSOLUTE
	};

	private static final ASEFormatter df = ASEFormatter.getInstance();
	private static final Logger log = LoggerFactory.getLogger(CapAdjustment.class.getName());

	public final Security sec;
	public final Type type;
	public final double adj;
	public final int sizeRef;
	public final SizeRefType sizeRefType;
	public final String description;

	public CapAdjustment(Security sec, Type type, double adj, int sizeRef, SizeRefType sizeRefType, String description) {
//	    assert adj >= 0.0;
	    
		this.sec = sec;
		this.type = type;
		this.adj = adj;
		this.sizeRef = sizeRef;
		this.sizeRefType = sizeRefType;
		this.description = description;
	}

	public static String dumpHeader() {
		return "type|secid|multiplier|sizeref|reftype|description";
	}

	public String toString() {
		return type + "|" + sec.getSecId() + "|" + adj + "|" + sizeRef + "|" + sizeRefType + "|" + description;
	}

	public static CapAdjustment restore(String line) throws Exception {
		String[] fields = line.split("\\|");
		return new CapAdjustment(new Security(Integer.parseInt(fields[1])), Type.valueOf(fields[0]), Double.parseDouble(fields[2]),
				Integer.parseInt(fields[3]), SizeRefType.valueOf(fields[4]), fields[5]);
	}

	public static List<CapAdjustment> loadCapAdjustmentsFile(File adjfile) throws Exception {
		log.info("Loading adjustments file: " + adjfile.getAbsolutePath());
		Vector<CapAdjustment> adjs = new Vector<CapAdjustment>();
		BufferedReader reader = FileUtils.openFileReader(adjfile);
		int cnt = 0;
		// skip header
		reader.readLine();
		for (String line = ""; line != null; line = reader.readLine()) {
			if (line.length() <= 0) continue;
			adjs.add(CapAdjustment.restore(line));
			cnt++;
		}
		log.info("Loaded " + cnt + " adjustments.");
		reader.close();
		return adjs;
	}
}
