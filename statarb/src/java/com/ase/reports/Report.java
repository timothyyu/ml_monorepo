package ase.reports;

import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Vector;

import org.apache.commons.lang.StringUtils;

import ase.util.Triplet;

public class Report {
	public enum ReportAttrType {
		S, N
	};

	public enum ReportSortType {
		ASC, DESC, ABS
	};

	public static class Sorter implements Comparator<Vector<String>> {
		private Vector<Triplet<Integer, ReportAttrType, ReportSortType>> order = new Vector<Triplet<Integer, ReportAttrType, ReportSortType>>();

		public void add(Integer column, ReportAttrType type, ReportSortType sortType) {
			order.add(new Triplet<Integer, Report.ReportAttrType, Report.ReportSortType>(column, type, sortType));
		}

		@Override
		public int compare(Vector<String> o1, Vector<String> o2) {
			for (int xx = 0; xx != order.size(); xx++) {
				int comp = 0;
				switch (order.get(xx).second) {
				case S:
					String s1 = o1.get(order.get(xx).first);
					String s2 = o2.get(order.get(xx).first);

					switch (order.get(xx).third) {
					case ASC:
						comp = s1.compareTo(s2);
						break;
					case DESC:
						comp = -s1.compareTo(s2);
						break;
					default:
						comp = 0;
						break;
					}
					break; // S
				case N:
					Double d1 = Double.parseDouble(o1.get(order.get(xx).first));
					Double d2 = Double.parseDouble(o2.get(order.get(xx).first));

					switch (order.get(xx).third) {
					case ASC:
						comp = d1.compareTo(d2);
						break;
					case DESC:
						comp = -d1.compareTo(d2);
						break;
					case ABS:
						Double dd1 = Math.abs(d1);
						Double dd2 = Math.abs(d2);
						comp = -dd1.compareTo(dd2);
						break;
					default:
						comp = 0;
						break;
					}
					break; // N
				default:
					break;
				}

				if (comp != 0)
					return comp;
			}

			return 0;
		}
	}

	public Vector<String> preheader = new Vector<String>();
	public Vector<Vector<String>> header = new Vector<Vector<String>>();
	public Vector<Vector<String>> body = new Vector<Vector<String>>();
	public final int columns;
	public final int visibleColumns;

	public Report(int visibleColumns, int columns) {
		if (columns < 1 || visibleColumns < 1) {
			throw new RuntimeException("<1 columns in a report? Really?");
		}
		this.visibleColumns = visibleColumns;
		this.columns = columns;
	}

	public void addPreHeader(String line) {
		preheader.add(line);
	}

	public void addHeader(String[] line) {
		addHeader(new Vector<String>(Arrays.asList(line)));
	}

	public void addBody(String[] line) {
		addBody(new Vector<String>(Arrays.asList(line)));
	}

	public void addBody(Object[] line) {
		Vector<String> nl = new Vector<String>();
		for (Object o : line) {
			String s = "null";
			if (o != null) {
				s = o.toString();
			}
			nl.add(s);
		}

		addBody(nl);
	}

	public void addHeader(Vector<String> line) {
		if (line.size() != columns) {
			throw new RuntimeException("Added header with unexpected number of columns");
		}
		header.add(line);
	}

	public void addBody(Vector<String> line) {
		if (line.size() != columns) {
			throw new RuntimeException("Added header with unexpected number of columns");
		}
		body.add(line);
	}

	public void sort(Sorter sorter) {
		Collections.sort(body, sorter);
	}

	public String generateReport(String separator, boolean align) {
		StringBuilder sb = new StringBuilder();
		for (String s : preheader) {
			sb.append(s);
			sb.append('\n');
		}

		Vector<Vector<String>> allLines = new Vector<Vector<String>>();
		allLines.addAll(header);
		allLines.addAll(body);

		int[] widths = null;

		if (align) {
			widths = new int[visibleColumns];
			Arrays.fill(widths, 0);
			for (Vector<String> line : allLines) {
				for (int xx = 0; xx != visibleColumns; xx++) {
					widths[xx] = Math.max(widths[xx], (line.get(xx)!=null)? line.get(xx).length() : 4);
				}
			}
		}

		for (Vector<String> line : allLines) {
			String token = line.get(0);
			if (align) {
				token = StringUtils.rightPad(token, widths[0]);
			}
			sb.append(token);
			if (visibleColumns > 1) {
				sb.append(separator);
			}

			for (int xx = 1; xx != visibleColumns; xx++) {
				token = line.get(xx);
				if (align) {
					token = StringUtils.leftPad(token, widths[xx]);
				}
				sb.append(token);
				if (xx != visibleColumns - 1) {
					sb.append(separator);
				}
			}
			sb.append('\n');
		}

		return sb.toString();
	}
}
