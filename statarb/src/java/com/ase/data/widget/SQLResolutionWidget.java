package ase.data.widget;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Vector;

import ase.data.AttrType;
import ase.util.Pair;

public class SQLResolutionWidget extends SQLWidget {

	// ///////// SINGLETON /////////////////

	private static SQLResolutionWidget instance = null;

	public static final SQLResolutionWidget instance() {
		if (instance == null) {
			instance = new SQLResolutionWidget();
		}
		return instance;
	}

	private SQLResolutionWidget() {
		super();
		try {
			loadAtt();
		} catch (SQLException e) {
			throw new RuntimeException("Could not init SQLResolutionWidget!");
		}
	}

	// //////////////////////////////////

	@Override
	protected void uponReconnect() {
		// TODO Auto-generated method stub

	}

	// ///////// ATTR RELATED CODE ///////////////
	private static class Att {
		public String name;
		public int code;
		public int source;
		public int datatype;
		public String tableref;

		public Att(String name, int code, int source, int datatype, String tableref) {
			super();
			this.name = name;
			this.code = code;
			this.source = source;
			this.datatype = datatype;
			this.tableref = tableref;
		}
	}

	private HashMap<String, Vector<Att>> name2att = new HashMap<String, Vector<Att>>();

	private HashMap<Pair<String, Integer>, Att> name_source2att = new HashMap<Pair<String, Integer>, SQLResolutionWidget.Att>();

	private void loadAtt() throws SQLException {
		Statement st = c.createStatement();
		ResultSet rs = st.executeQuery("SELECT * FROM attribute_type");

		while (rs.next()) {
			String name = rs.getString(2);
			int source = rs.getInt(3);
			Att att = new Att(rs.getString(2), rs.getInt(1), rs.getInt(3), rs.getInt(4),
					rs.getString(5));

			Vector<Att> vatt = name2att.get(name);
			if (vatt == null) {
				vatt = new Vector<SQLResolutionWidget.Att>();
				name2att.put(name, vatt);
			}
			vatt.add(att);

			name_source2att.put(new Pair<String, Integer>(name, source), att);
		}
		rs.close();
		st.close();
	}

	public boolean existsUniquely(String name) {
		Vector<Att> vatt = name2att.get(name);
		if (vatt == null || vatt.isEmpty() || vatt.size() > 1)
			return false;
		else
			return true;
	}

	public boolean existsUniquely(String name, int source) {
		if (source == 0)
			return existsUniquely(name);

		Att att = name_source2att.get(new Pair<String, Integer>(name, source));
		if (att == null)
			return false;
		else
			return true;
	}

	// Assumes existsUniquely has been called and returned true
	public int getAttributeCode(String name, int source) {
		if (source == 0)
			return getAttributeCode(name);
		else
			return name_source2att.get(new Pair<String, Integer>(name, source)).code;
	}

	// Assumes existsUniquely has been called and returned true
	public int getAttributeSource(String name, int source) {
		if (source == 0)
			return getAttributeSource(name);
		else
			return name_source2att.get(new Pair<String, Integer>(name, source)).source;
	}

	// Assumes existsUniquely has been called and returned true
	public String getAttributeTableRef(String name, int source) {
		if (source == 0)
			return getAttributeTableRef(name);
		else
			return name_source2att.get(new Pair<String, Integer>(name, source)).tableref;
	}

	// Assumes existsUniquely has been called and returned true
	public AttrType.Type getAttributeType(String name, int source) {
		if (source == 0)
			return getAttributeType(name);

		int t = name_source2att.get(new Pair<String, Integer>(name, source)).datatype;
		switch (t) {
		case 1:
			return AttrType.Type.N;
		case 2:
			return AttrType.Type.S;
		case 3:
			return AttrType.Type.D;
		case 4:
			return AttrType.Type.P;
		default:
			return null;
		}
	}

	// Assumes existsUniquely has been called and returned true
	public int getAttributeCode(String name) {
		return name2att.get(name).get(0).code;
	}

	// Assumes existsUniquely has been called and returned true
	public int getAttributeSource(String name) {
		return name2att.get(name).get(0).source;
	}

	// Assumes existsUniquely has been called and returned true
	public String getAttributeTableRef(String name) {
		return name2att.get(name).get(0).tableref;
	}

	// Assumes existsUniquely has been called and returned true
	public AttrType.Type getAttributeType(String name) {
		int t = name2att.get(name).get(0).datatype;
		switch (t) {
		case 1:
			return AttrType.Type.N;
		case 2:
			return AttrType.Type.S;
		case 3:
			return AttrType.Type.D;
		case 4:
			return AttrType.Type.P;
		default:
			return null;
		}
	}
	
	public static void main(String[] args) {
		SQLResolutionWidget w=SQLResolutionWidget.instance();
		System.out.println(w.getAttributeCode("GROWTH", 0));
	}
}
