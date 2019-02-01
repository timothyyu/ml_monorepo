package ase.data.widget;

import java.io.FileReader;
import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Properties;
import java.util.logging.Logger;

import ase.util.LoggerFactory;

public class AseDBConn {
	private static final Logger log = LoggerFactory.getLogger(AseDBConn.class.getName());
	private static Connection conn = null;
	private static String configFile = null;

	public static Connection getConnection(String configFile) throws SQLException, IOException {
		if (conn == null) {
			AseDBConn.configFile = configFile;
			log.fine("reading db configuration file " + AseDBConn.configFile);
			Properties p = new Properties();
			p.load(new FileReader(AseDBConn.configFile));
			if (p.getProperty("host").startsWith("asetrade1.newark")) log.severe("Connecting to SECONDARY DATABASE!");
			// Class.forName("com.mysql.jdbc.Driver");
			log.fine("Connecting to database");
			conn = DriverManager.getConnection("jdbc:mysql://"
					+ p.getProperty("host")
					+ ":"
					+ p.getProperty("port")
					+ "/"
					+ p.getProperty("database")
					+ "?user="
					+ p.getProperty("username")
					+ "&password="
					+ p.getProperty("password"));
		}		
		return conn;
	}

	public static Connection getConnection() throws SQLException, IOException {
		if (conn == null) {
			if (AseDBConn.configFile == null)
				AseDBConn.configFile = System.getenv("DB_CONFIG_FILE");
			log.fine("reading db configuration file " + AseDBConn.configFile);
			Properties p = new Properties();
			p.load(new FileReader(AseDBConn.configFile));
			log.fine("Connecting to database");
			conn = DriverManager.getConnection("jdbc:mysql://"
					+ p.getProperty("host")
					+ ":"
					+ p.getProperty("port")
					+ "/"
					+ p.getProperty("database")
					+ "?user="
					+ p.getProperty("username")
					+ "&password="
					+ p.getProperty("password"));

			conn.setReadOnly(true);
			conn.setTransactionIsolation(Connection.TRANSACTION_REPEATABLE_READ);
		}

		return conn;
	}

	public static Connection reconnect() throws SQLException, IOException {
		if (!conn.isClosed()) {
			log.severe("Database already connected!  Are you using an old connection that was already closed?");
			return conn;
		}

		log.info("Reconnecting to database");
		conn = null;
		return getConnection();
	}

	public static void closeConnection() throws SQLException {
		log.info("Disconnecting from database");
		conn.close();
		conn = null;
	}

	public static void getSnapshot() throws SQLException {
		Statement st = conn.createStatement();
		st.executeQuery("START TRANSACTION WITH CONSISTENT SNAPSHOT");
		st.close();
	}

	public static void releaseSnapshot() throws SQLException {
		Statement st = conn.createStatement();
		st.executeQuery("COMMIT");
		st.close();
	}

	public static void main(String[] argv) {
		try {
			Connection c = getConnection();
			getSnapshot();
			int count = 0;

			while (count < 100) {
				try {
					Statement stmt = c.createStatement();
					ResultSet rs = stmt.executeQuery("select count(*) from dummy");
					while (rs.next()) {
						System.out.println("count(*) from dummy: " + rs.getInt(1));
					}
					stmt.close();
				}
				catch (SQLException e) {
					e.printStackTrace();
				}

				try {
					Thread.currentThread().sleep(1000);
				}
				catch (InterruptedException e) {

				}
			}
			
			releaseSnapshot();
		}
		catch (Exception e) {
			e.printStackTrace();
		}
	}
}
