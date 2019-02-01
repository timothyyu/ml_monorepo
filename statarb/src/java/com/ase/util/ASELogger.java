package ase.util;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.util.Calendar;
import java.util.Enumeration;
import java.util.logging.ConsoleHandler;
import java.util.logging.FileHandler;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.logging.StreamHandler;

@Deprecated
public class ASELogger {
	private static final ASEFormatter df = ASEFormatter.getInstance();

	private static class ASELogFormatter extends Formatter {
		@Override
		public String format(LogRecord record) {
			StringBuilder sb = new StringBuilder();
			sb.append(record.getLevel());
			sb.append(' ');
			sb.append('[');
			sb.append(df.formatLong(Calendar.getInstance().getTime()));
			sb.append(' ');
			String sclass = record.getSourceClassName();
			sb.append(sclass.substring(sclass.lastIndexOf('.') + 1));
			// sb.append(']');
			sb.append('.');
			sb.append(record.getSourceMethodName());
			sb.append(']');
			// sb.append(':');
			sb.append(' ');
			sb.append(record.getMessage());
			sb.append('\n');

			return sb.toString();
		}
	}

	private static Level DEFAULT_LEVEL = "1".equals(System.getenv("DEBUG")) ? Level.FINEST : Level.INFO;
	private static boolean UNSUPERVISED_MODE = false;
	private static String mainClass = "java.unknown";
	private static FileHandler globalFileHandler = null;
	private static String globalLogfile = null;
	private static Logger globalLogger = null;

	// XXX deprecate this...
	static {
		StackTraceElement[] stack = Thread.currentThread().getStackTrace();
		StackTraceElement main = stack[stack.length - 1];
		String fullclass = main.getClassName();
		mainClass = fullclass.substring(fullclass.lastIndexOf("."));
		globalLogfile = System.getenv("LOG_DIR") + "/" + mainClass + "." + System.getenv("STRAT") + "."
				+ ManagementFactory.getRuntimeMXBean().getName().split("@")[0] + ".log";
	}

	public static Logger global() {
		if (globalLogger == null) {
			globalLogger = Logger.getLogger("ase_global");
			globalLogger.setUseParentHandlers(false);
			globalLogger.setLevel(DEFAULT_LEVEL);
			for (Handler h : getGlobalHandlers()) {
				globalLogger.addHandler(h);
			}
		}
		return globalLogger;
	}

	public static void setGlobalMode(boolean unsupervised) {
		setGlobalMode(unsupervised, globalLogfile);
	}

	public static void setGlobalMode(boolean unsupervised, String logfile) {
		if (UNSUPERVISED_MODE == unsupervised)
			return;

		UNSUPERVISED_MODE = unsupervised;
		if (UNSUPERVISED_MODE) {
			assert logfile != null;
			globalLogfile = logfile;
		}

		if (globalLogger != null) {
			// remove all existing handlers
			Handler[] currentHandlers = globalLogger.getHandlers();
			for (Handler h : currentHandlers) {
				if (h instanceof StreamHandler) {
					h.flush();
				}
				globalLogger.removeHandler(h);
			}
			// add new loggers
			for (Handler h : getGlobalHandlers()) {
				globalLogger.addHandler(h);
			}
		}
	}

	public static void setGlobalLevel(Level level) {
		DEFAULT_LEVEL = level;
		if (globalLogger != null) {
			globalLogger.setLevel(DEFAULT_LEVEL);
		}
	}

	protected static Handler[] getGlobalHandlers() {
		if (UNSUPERVISED_MODE) {
			Handler errorHandler = new ConsoleHandler();
			errorHandler.setFormatter(new ASELogFormatter());
			errorHandler.setLevel(Level.SEVERE);

			try {
				if (globalFileHandler == null) {
					globalFileHandler = new FileHandler(globalLogfile);
					globalFileHandler.setFormatter(new ASELogFormatter());
					globalFileHandler.setLevel(Level.ALL);
				}
				return new Handler[] { errorHandler, globalFileHandler };
			}
			catch (IOException e) {
				System.err.println("Logger failed to open output file: " + globalLogfile);
				return new Handler[] { errorHandler };
			}
		}
		else {
			Handler handler = new ConsoleHandler();
			handler.setFormatter(new ASELogFormatter());
			handler.setLevel(Level.ALL);

			return new Handler[] { handler };
		}
	}

	protected static Handler[] getLocalHandlers(String logfile) {
		if (logfile != null) {
			Handler errorHandler = new ConsoleHandler();
			errorHandler.setFormatter(new ASELogFormatter());
			errorHandler.setLevel(Level.SEVERE);

			try {
				FileHandler fh = new FileHandler(logfile);
				fh.setFormatter(new ASELogFormatter());
				fh.setLevel(Level.ALL);

				return new Handler[] { errorHandler, fh };
			}
			catch (IOException e) {
				System.err.println("Logger failed to open output file: " + logfile);
				return new Handler[] { errorHandler };
			}
		}
		else {
			Handler handler = new ConsoleHandler();
			handler.setFormatter(new ASELogFormatter());
			handler.setLevel(Level.ALL);

			return new Handler[] { handler };
		}
	}

	public static Logger getLogger(String name, Level level, String logfile) {
		// check if the logger already exists
		Logger logger = LogManager.getLogManager().getLogger(name);
		// Create new logger
		if (logger == null) {
			logger = Logger.getLogger(name);
			logger.setUseParentHandlers(false);
			logger.setLevel(level);
			for (Handler h : getLocalHandlers(logfile)) {
				logger.addHandler(h);
			}
		}
		else {
			logger.setLevel(level);
		}
		return logger;
	}

	public static void main(String[] args) {
	}
}
