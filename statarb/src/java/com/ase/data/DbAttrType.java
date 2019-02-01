package ase.data;

import java.util.logging.Logger;

import ase.data.widget.SQLResolutionWidget;
import ase.util.LoggerFactory;

public class DbAttrType extends AttrType {
	private static final Logger log = LoggerFactory.getLogger(DbAttrType.class.getName());

	public final String dbname;
	public final int source;
	public final int code;
	public final String tableref;
	public final long max_age;
	public final long backfillOffset;

	@Deprecated
	public DbAttrType(String dbname) {
		this(dbname, dbname);
	}

	@Deprecated
	public DbAttrType(String dbname, String name) {
		this(dbname, name, 0L, 0L, 0);
	}

	@Deprecated
	public DbAttrType(String dbname, String name, long max_age) {
		this(dbname, name, max_age, 0L, 0);
	}

	public DbAttrType(String dbname, String name, long max_age, long backfillOffset) {
		this(dbname, name, max_age, backfillOffset, 0);
	}

	public DbAttrType(String dbname, String name, long max_age, long backfillOffset, int source) {
		super(name);
		this.dbname = dbname;
		this.max_age = max_age;
		this.backfillOffset = backfillOffset;

		final SQLResolutionWidget rw = SQLResolutionWidget.instance();
		if (rw.existsUniquely(dbname, source)) {
			code = rw.getAttributeCode(dbname, source);
			this.source = rw.getAttributeSource(dbname, source);
			datatype = rw.getAttributeType(dbname, source);
			tableref = rw.getAttributeTableRef(dbname, source);
		}
		else {
			// throw new RuntimeException("Attribute " +dbname +" is either absent from DB or ambiguous");
			log.severe("Attribute " + dbname + " is either absent from DB or ambiguous");
			code = -1;
			this.source = -1;
			tableref = null;
		}
	}

	@Override
	public String toString() {
		return "DbAttrType [dbname=" + dbname + ", code=" + code + ", source=" + source + ", datatype=" + datatype + ", max_age=" + max_age
				+ ", backfillOffset=" + backfillOffset + "]";
	}
}
