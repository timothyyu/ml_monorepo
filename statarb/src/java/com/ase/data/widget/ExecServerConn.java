package ase.data.widget;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.logging.Logger;

import ase.util.LoggerFactory;

public class ExecServerConn {
    
    private static final Logger log = LoggerFactory.getLogger(ExecServerConn.class.getName());
    private static final int MAX_CONN_ATTEMPTS = 10;
    private static final int INIT_SOCKET_TIMEOUT = 350; // in milliseconds
    private static final int DATA_TIMEOUT = 70; // once we start receiving data, we can use a smaller timeout
    private static final int MAX_READ_WAIT_TIME = 3000; // in milliseconds

    public final String hostname;
    public final int portNumber;
    public String identifier = "";
    
    private Socket socket = null;
    protected Set<String> universe = new HashSet<String>();
    private PrintWriter out;
    private BufferedReader in;
    private int socket_timeout_ms = INIT_SOCKET_TIMEOUT;

    public ExecServerConn(String hostname, int portNumber) {
        this.hostname = hostname;
        this.portNumber = portNumber;
    }

    public boolean isConnected() {
        return (socket == null) ? false : socket.isConnected();
    }

    public boolean connect() {
        if (this.isConnected()) {
             return true;
        }
        
        int numTries = 0;
        boolean success = false;
        
        while ((numTries < MAX_CONN_ATTEMPTS) && (success == false)) { 
            numTries += 1;
            success = true;
            try {
                log.info("Connecting to host - " + hostname + ":" + portNumber);
                socket = new Socket(hostname, portNumber);
                log.info("Connected to " + hostname + " at " + socket.getPort() + " from local port: " + socket.getLocalPort() + " using timeout " + socket_timeout_ms + " milliseconds");
                socket.setSoTimeout(socket_timeout_ms);
                out = new PrintWriter(socket.getOutputStream(), true);
                in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            }
            catch (UnknownHostException e) {
                log.severe("Could not determine IP address of host: " + hostname + ". Retrying connection.");
                success = false;
                continue;
            }
            catch (IOException e) {
                log.severe("Could not create socket for host - " + hostname + ":" + portNumber + ". Retrying connection.");
                success = false;
                continue;
            }
        }
            
        if(success == false) {
            log.severe("Exceeded maximum connection attempts in ExecServerConn. Giving up. (" + hostname + "," + portNumber + ")");
        }
        
        return success;
    }

    public int getTimeoutMillis() {
    	return socket_timeout_ms;
    }
    
    public void setTimeoutMillis(int newTimeout) {
    	socket_timeout_ms = newTimeout;
    	try {
    		socket.setSoTimeout(socket_timeout_ms);
    	}
    	catch (SocketException se){
    		log.info("Unable to set socket timeout due to SocketException in setTimeoutMillis()");
    	}
    }
    
    public void resetTimeout() {
    	socket_timeout_ms = INIT_SOCKET_TIMEOUT;
    }
    
    public void write(String sendStr) {
        out.println(sendStr);
    }

    public String read() throws InterruptedException {
    	log.info("Entered read() in ExecServerConn (" + hostname + "," + portNumber + ")");
        String retVal = "";
        String line = this.readLine();
        int currTimeout = this.getTimeoutMillis();
        long startTime = System.currentTimeMillis();
        //if (System.currentTimeMillis() - startTime > MAX_WAIT_TIME) break;

        while (line != null && !line.equals("")) {
        	this.setTimeoutMillis(DATA_TIMEOUT);
/*        	if (hostname.equals("exectrade4.jc") && identifier.equals("pnl")) {
	        	log.info("line = " + line);
        	}*/
            retVal += line + "\n";
            line = this.readLine();
        }
        log.info("Leaving read() in ExecServerConn (" + hostname + "," + portNumber + ")");
        this.setTimeoutMillis(currTimeout);
        return retVal;
    }

    public String readLine() throws InterruptedException {
    	//log.info("Entered readLine() in ExecServerConn (" + hostname + "," + portNumber + ")");
    	if (Thread.currentThread().isInterrupted()) {
    		throw new InterruptedException();
    	}
        String line;
        try {
            line = in.readLine();
        }
        catch (SocketTimeoutException e) {
        	log.info("Leaving readLine() in ExecServerConn due to SocketTimeoutException (" + hostname + "," + portNumber + ")");
            return null;
        }
        catch (IOException e) {
            log.severe("Encountered IOException while trying to read input socket (" + hostname + "," + portNumber + ")");
            return null;
        }
        //log.info("Leaving readLine() in ExecServerConn normally (" + hostname + "," + portNumber + ")");
        return line;
    }

    public boolean catersToSymbol(String sec) {
        return universe.contains(sec);
    }

    public boolean setUniverse(List<String> symbList) {
        return universe.addAll(symbList);
    }
    
    public void close() {
        if(socket == null) {
            return;
        }
        try {
            socket.close();
        }
        catch (IOException ee) {
            log.severe("Could not close socket for execution server: " + hostname);
        }
    }
}
