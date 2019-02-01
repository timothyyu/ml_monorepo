package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.io.Writer;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Vector;
import java.util.logging.Logger;

import org.apache.commons.lang.StringUtils;

import ase.data.Security;
import ase.portfolio.CapAdjustment.SizeRefType;
import ase.portfolio.CapAdjustment.Type;
import ase.util.ASEFormatter;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;

public class OldSystemUtils {
	protected static final Logger log = LoggerFactory.getLogger(OldSystemUtils.class.getName());
	private static final ASEFormatter df = ASEFormatter.getInstance();
	
	protected static Map<Pair<Integer, Integer>, Integer> old2new = null;
	
	public static final String OLD_DAY_FAKE_FILLS = "old.fake_fills.txt";
	public static final String OLD_DAY_FILLS = "old.fills.txt";

	public static Map<Pair<Integer, Integer>, Integer> loadOld2New() throws Exception {
		File mapFile = new File("/apps/ase/run/useq-live/old.secids.txt");
		Map<Pair<Integer, Integer>, Integer> old2new = new HashMap<Pair<Integer, Integer>, Integer>();

		BufferedReader reader = FileUtils.openFileReader(mapFile);
		String line;
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			old2new.put(new Pair<Integer, Integer>(Integer.parseInt(tokens[0]), Integer.parseInt(tokens[1])), Integer.parseInt(tokens[2]));
		}
		reader.close();
		return old2new;
	}

	public static List<Fill> loadOldFillsFile(File fillsfile) throws Exception {
		log.info("Loading old fills file: " + fillsfile.getAbsolutePath());
		Vector<Fill> fills = new Vector<Fill>();
		BufferedReader reader = FileUtils.openFileReader(fillsfile);
		int cnt = 0;

		String line;
		reader.readLine();// get rid of the header
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			int date = Integer.parseInt(tokens[0]);
			int seqnum = Integer.parseInt(tokens[1]);
			long ts = (long) Math.floor(Double.parseDouble(tokens[8]) * 1000);
			int coid = Integer.parseInt(tokens[3]);
			int issueid = Integer.parseInt(tokens[4]);
			int size = (int) Double.parseDouble(tokens[5]);
			double price = Double.parseDouble(tokens[6]);

			if (old2new == null)
				old2new = loadOld2New();

			Integer secid = old2new.get(new Pair<Integer, Integer>(coid, issueid));
			if (secid == null) {
				throw new RuntimeException("Could not map old system id to secid");
			}

			long id = Long.parseLong(Integer.toString(date) + StringUtils.leftPad(Integer.toString(seqnum), 8, "0"));
			Fill fill = new Fill(new Security(secid), ts > 0? ts : 1, size, price, null, id);
			fills.add(fill);
			cnt++;
		}
		reader.close();
		log.info("Loaded " + cnt + " fills.");
		return fills;
	}

	public static void loadOldFillsFile(Portfolio portfolio, File fillsfile) throws Exception {
		for (Fill fill : loadOldFillsFile(fillsfile))
			portfolio.handleFill(fill);
	}

	public static void convertToNewFillsFile(File o, File n) throws Exception {
		Writer writer = FileUtils.makeWriter(n);
		writer.write(Fill.dumpHeader() + "\n");
		for (Fill fill : loadOldFillsFile(o))
			writer.write(fill.toString() + "\n");
		writer.close();
	}

	public static List<CapAdjustment> loadOldFakeFillsFile(File fillsfile) throws Exception {
		log.info("Loading old fake fills file: " + fillsfile.getAbsolutePath());
		Vector<CapAdjustment> adjs = new Vector<CapAdjustment>();
		BufferedReader reader = FileUtils.openFileReader(fillsfile);
		int cnt = 0;

		String line;
		reader.readLine();// get rid of the header
		while ((line = reader.readLine()) != null) {
			if (line.equals(""))
				continue;
			String[] tokens = line.split("\\|");
			int coid = Integer.parseInt(tokens[3]);
			int issueid = Integer.parseInt(tokens[4]);
			int size = (int) Double.parseDouble(tokens[5]);
			double price = Double.parseDouble(tokens[6]);
			String comment = tokens[8];

			if (old2new == null)
				old2new = loadOld2New();

			Integer secid = old2new.get(new Pair<Integer, Integer>(coid, issueid));
			if (secid == null) {
				throw new RuntimeException("Could not map old system id to secid");
			}

			CapAdjustment adj;
			if (size == 0)
				adj = new CapAdjustment(new Security(secid), CapAdjustment.Type.CORP_CASH, Math.abs(price), (int)Math.signum(price), CapAdjustment.SizeRefType.ABSOLUTE, comment);
			else if (price==0)
				adj=new CapAdjustment(new Security(secid),CapAdjustment.Type.CORP_SHARES,1,size,CapAdjustment.SizeRefType.ABSOLUTE, comment);
			else
				adj = new CapAdjustment(new Security(secid), CapAdjustment.Type.FILL, price, size, CapAdjustment.SizeRefType.ABSOLUTE, comment);

			adjs.add(adj);
			cnt++;
		}
		reader.close();
		log.info("Loaded " + cnt + " fills.");
		return adjs;
	}

	public static void loadOldFakeFillsFile(Portfolio portfolio, File fillsfile) throws Exception {
		for (CapAdjustment adj : loadOldFakeFillsFile(fillsfile))
			portfolio.handleAdjustment(adj);
	}

	public static void convertToNewAdjustmentsFile(File o, File n) throws Exception {
		Writer writer = FileUtils.makeWriter(n);
		writer.write(CapAdjustment.dumpHeader() + "\n");
		for (CapAdjustment adj : loadOldFakeFillsFile(o))
			writer.write(adj.toString() + "\n");
		writer.close();
	}

	public static Portfolio loadOldSystemPortfolio(File pfile) throws Exception {
		Portfolio portfolio = new Portfolio();
		BufferedReader reader = FileUtils.openFileReader(pfile);

		// read header
		reader.readLine();
		String line;
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			String[] idtokens=tokens[1].split("[\\(\\)\\, ]");
			int coid = Integer.parseInt(idtokens[1]);
			int issueid = Integer.parseInt(idtokens[3]);
			double cash = Double.parseDouble(tokens[2]);
			int shares = Integer.parseInt(tokens[3]);
			// double price=Double.parseDouble(tokens[5]);

			if (old2new == null)
				old2new = loadOld2New();

			Integer secid = old2new.get(new Pair<Integer, Integer>(coid, issueid));
			if (secid == null) {
				throw new RuntimeException("Could not map old system id to secid");
			}

			// add the position as adjustments
			Security sec = new Security(secid);
			CapAdjustment adj1 = new CapAdjustment(sec, Type.CORP_SHARES, 1, shares, SizeRefType.ABSOLUTE, "");
			CapAdjustment adj2 = new CapAdjustment(sec, Type.CORP_CASH, cash, 1, SizeRefType.ABSOLUTE, "");

			portfolio.handleAdjustment(adj1);
			portfolio.handleAdjustment(adj2);
		}

		reader.close();
		return portfolio;
	}
	
	public static void convertOldSystemFiles(String location, long date) throws Exception {
        File dir = new File(location);
        File dateDir = new File(dir, df.toYYYYMMDD(date));

        File oldFills = new File(dateDir, OldSystemUtils.OLD_DAY_FILLS);
        File newFills = new File(dateDir, Portfolio.dayFillsFilename(dateDir));
        File oldAdjustments = new File(dateDir, OldSystemUtils.OLD_DAY_FAKE_FILLS);
        File newAdjustments = new File(dateDir, Portfolio.DAY_CAPADJUSTMENTS);

        if (oldFills.exists())
            OldSystemUtils.convertToNewFillsFile(oldFills, newFills);

        if (oldAdjustments.exists())
            OldSystemUtils.convertToNewAdjustmentsFile(oldAdjustments, newAdjustments);
    }

	public static void comparePortfolios(Portfolio p1, Portfolio p2) {
		// orphan positions
		Collection<Position> c1 = p1.getPositions();
		Collection<Position> c2 = p2.getPositions();

		for (Position t1 : c1) {
			if (p2.getPosition(t1.sec) == null) {
				System.out.println("P1 orphan position: " + t1.toString());
			}
		}
		for (Position t2 : c2) {
			if (p1.getPosition(t2.sec) == null) {
				System.out.println("P2 orphan position: " + t2.toString());
			}
		}
		for (Position t1 : c1) {
			Position t2 = p2.getPosition(t1.sec);
			if (t2 == null)
				continue;
			if (t1.getIntShares() != t2.getIntShares()) {
				System.out.println("Size discrepancy: " + t1.sec.getSecId() + ", " + t1.getIntShares() + " vs " + t2.getIntShares());
			}
			if (Math.abs(t1.getCash() - t2.getCash()) >= 0.01) {
				System.out.println("Cash discrepancy: " + t1.sec.getSecId() + ", " + t1.getCash() + " vs " + t2.getCash());
			}
		}
	}
}
