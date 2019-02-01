package ase.portfolio;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.logging.Logger;

import ase.apps.LiveOpt;
import ase.data.ExecPosition;
import ase.data.Security;
import ase.data.Universe;
import ase.data.XRef;
import ase.data.widget.LiveQuoteWidget;
import ase.data.widget.SQLSecurityWidget;
import ase.util.ASEFormatter;
import ase.util.CollectionUtils;
import ase.util.Email;
import ase.util.FileUtils;
import ase.util.LoggerFactory;
import ase.util.Pair;
import ase.util.Time;

public class OverrideGenerator {
	protected static final Logger log = LoggerFactory.getLogger(OverrideGenerator.class.getName());
	protected static final ASEFormatter df = ASEFormatter.getInstance();
	protected static final LiveQuoteWidget lqw = LiveQuoteWidget.instance();
	protected static final SQLSecurityWidget sw = SQLSecurityWidget.instance();

	public static Map<Security, Pair<Integer, Integer>> positionDiffs(String location, long date, boolean oldSystem) throws Exception {
		Map<Security, Pair<Integer, Integer>> result = new HashMap<Security, Pair<Integer, Integer>>();

		//Exec server positions
		Map<Security, ExecPosition> execPositions = lqw.getPositions();

		// Load sod portfolio and load adjustments
		Portfolio sodPortfolio = new Portfolio();
		File dateDir = new File(location + "/" + df.toYYYYMMDD(date));
		File sodFile = new File(dateDir, Portfolio.SOD_PORTFOLIO);
		File adjsFile = oldSystem ? new File(dateDir, OldSystemUtils.OLD_DAY_FAKE_FILLS) : new File(dateDir, Portfolio.DAY_CAPADJUSTMENTS);
		File fillsFile = oldSystem ? new File(dateDir, OldSystemUtils.OLD_DAY_FILLS) : new File(dateDir, Portfolio.dayFillsFilename(dateDir));

		sodPortfolio.restore(sodFile);
		if (adjsFile.exists()) {
			List<CapAdjustment> adjs = null;
			if (oldSystem) {
				adjs = OldSystemUtils.loadOldFakeFillsFile(adjsFile);
			}
			else {
				adjs = CapAdjustment.loadCapAdjustmentsFile(adjsFile);
			}
			for (CapAdjustment adj : adjs) {
				sodPortfolio.handleAdjustment(adj);
			}
		}
		else {
			log.severe("No cap adjustment file found: " + adjsFile.toString());
		}

		if (fillsFile.exists()) {
			List<Fill> fills = null;
			if (oldSystem) {
				fills = OldSystemUtils.loadOldFillsFile(fillsFile);
			}
			else {
				fills = PortfolioUtils.loadFillsFile(fillsFile);
			}
			for (Fill fill : fills) {
				// /XXX only apply fills that happened before the position
				// timestamp
				ExecPosition ep = execPositions.get(fill.sec);
				if (ep != null && fill.ts <= ep.getTs()) {
					sodPortfolio.handleFill(fill);
				}
			}
		}
		else {
			log.warning("No fills file found: " + fillsFile.toString());
		}
		
		//Portfolio positions
		assert !sodPortfolio.allowFracPos;
		Map<Security, ExecPosition> portfolioPositions = new HashMap<Security, ExecPosition>();
		for (Position p : sodPortfolio.getPositions()) {
			portfolioPositions.put(p.sec, new ExecPosition(p.getIntShares(), Time.now()));
		}
		
		//The candidates for overrides are the current active securities
		File tickersFile = new File(System.getenv("RUN_DIR")+"/"+Universe.TICKER_FILE);
		Set<Security> candidates = null;
		if (tickersFile.exists()) { 
			candidates = Universe.loadFromTickersFile(tickersFile.toString());
		}
		else {
			log.severe("Failed to load tickers file "+tickersFile.toString()+". Aborting...");
			return new HashMap<Security, Pair<Integer,Integer>>();
		}

		for (Security sec : candidates) {
			if (!sec.isAlive()) {
				log.warning("Skipping dead security "+sec.getSecId());
				continue;
			}
			Integer portfolioPosition = portfolioPositions.containsKey(sec) ? portfolioPositions.get(sec).getPosition() : null;
			Integer serverPosition = execPositions.containsKey(sec) ? execPositions.get(sec).getPosition() : null;
			
			if (portfolioPosition == null && serverPosition == null)
				continue;
			else if (portfolioPosition == null && serverPosition == 0)
				continue;
			else if (portfolioPosition != null && serverPosition != null && portfolioPosition.equals(serverPosition))
				continue;
			else 
				result.put(sec, new Pair<Integer, Integer>(portfolioPosition, serverPosition));
		}
		return result;
	}

	public static void ammendOverrideFile(String location, long date, boolean oldSystem) throws Exception {
		Map<Security, Pair<Integer, Integer>> overrides = positionDiffs(location, date, oldSystem);

		log.info("Creating overrides for date " + date);
		File overridesFile = new File(location + "/" + LiveOpt.OVERRIDE_FILE);
		// read the notrades in the current override file
		Set<Integer> currentNoTrades = new HashSet<Integer>();
		BufferedReader reader = FileUtils.openFileReader(overridesFile);
		String line;
		while ((line = reader.readLine()) != null) {
			String[] tokens = line.split("\\|");
			if (tokens[2].equals("noTrade"))
				currentNoTrades.add(Integer.parseInt(tokens[0]));
		}
		reader.close();

		// amend file
		StringBuilder sb = new StringBuilder();
		int cnt = 0;
		for (Map.Entry<Security, Pair<Integer, Integer>> e : overrides.entrySet()) {
			Security sec = e.getKey();
			if (currentNoTrades.contains(sec.getSecId()))
				continue;
			cnt++;
			sb.append(sec.getSecId() + "|" + df.toYYYYMMDD(date) + "|" + "noTrade" + "|" + "1" + "|"
					+ sw.getXrefMap(CollectionUtils.toSet(sec), Time.now(), XRef.TIC).get(sec) + ", portfolio: " + e.getValue().first + ", exec: "
					+ e.getValue().second + " as of " + df.formatHumanShort(Time.now()));
			sb.append('\n');
		}

		if (cnt > 0) {
			PrintWriter writer = new PrintWriter(new FileWriter(overridesFile, true));
			writer.append(sb.toString());
			writer.close();

			Email.email("New overrides for date " + df.toYYYYMMDD(date), sb.toString());
		}
		else {
			Email.email("No overrides for date " + df.toYYYYMMDD(date), "Nothing to see here");
		}

		log.info("Inserted " + cnt + " new overrides");
	}
}
