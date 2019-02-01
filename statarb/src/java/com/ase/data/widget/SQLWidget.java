package ase.data.widget;

import java.io.IOException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.logging.Logger;

import ase.util.ASEFormatter;
import ase.util.LoggerFactory;

public abstract class SQLWidget {
	protected static final Logger log = LoggerFactory.getLogger(SQLWidget.class.getName());
    protected static final ASEFormatter df = ASEFormatter.getInstance();
    protected Connection c;
    protected PreparedStatement stm;

    //XXXLet's make and abstract instance() method to make all these guys singletons
    
    public SQLWidget() {
        try {
            c = AseDBConn.getConnection();
        }
        catch(Exception e) {
            throw new RuntimeException("Failed to open DB connection!");
        }
        stm = null;
    }

    // if the connection goes down, we can reconnect
    // but we need to clear our state
    protected void checkConnection() throws SQLException, IOException {
        boolean wasdown = false;
        if ( c == null ) {
            log.info("no db conn.  getting one.");
            c = AseDBConn.getConnection();
            wasdown = true;
        }
        if ( c.isClosed() ) {
            log.warning("db conn was closed.  reconnecting.");
            c = AseDBConn.reconnect();
            wasdown = true;
        }
        if ( wasdown ) {
            if ( stm != null ) stm.close();
            stm = null;
            uponReconnect();
        }
    }
    
    // if the db connection is reset, child is notified
    protected abstract void uponReconnect();         

    protected PreparedStatement prepare(String query) throws SQLException {
        //log.finest(query);
        return c.prepareStatement(query);
    }
}

