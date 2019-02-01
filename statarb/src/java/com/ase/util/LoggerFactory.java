package ase.util;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.util.Calendar;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.logging.ConsoleHandler;
import java.util.logging.FileHandler;
import java.util.logging.Formatter;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.logging.StreamHandler;

public class LoggerFactory {
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
	private static FileHandler logfileHandler = null;
	private static String logfilePath = null;
	private static HashSet<String> independentLoggers = new HashSet<String>();

	// XXX deprecate this...
	static {
		StackTraceElement[] stack = Thread.currentThread().getStackTrace();
		StackTraceElement main = stack[stack.length - 1];
		String fullclass = main.getClassName();
		mainClass = fullclass.substring(fullclass.lastIndexOf("."));
		logfilePath = System.getenv("LOG_DIR") + "/" + mainClass + "." + System.getenv("STRAT") + "."
				+ ManagementFactory.getRuntimeMXBean().getName().split("@")[0] + ".log";
	}

	public static void setLoggerFile(String loggerFile) {
		logfilePath = loggerFile;
	}

	public static void setUnsupervisedMode(boolean unsupervised) {
		if (UNSUPERVISED_MODE == unsupervised)
			return;

		UNSUPERVISED_MODE = unsupervised;
		Enumeration<String> loggerNames = LogManager.getLogManager().getLoggerNames();
		while (loggerNames.hasMoreElements()) {
			String name = loggerNames.nextElement();

			// ignore system loggers
			if (name.equals("") || name.equals("global") || independentLoggers.contains(name)) {
				continue;
			}

			Logger logger = LogManager.getLogManager().getLogger(name);
			// remove all existing handlers
			Handler[] currentHandlers = logger.getHandlers();
			for (Handler h : currentHandlers) {
				if (h instanceof StreamHandler) {
					h.flush();
				}
				logger.removeHandler(h);
			}
			// add new loggers
			for (Handler h : getHandlers(UNSUPERVISED_MODE)) {
				logger.addHandler(h);
			}
		}
	}

	public static void setGlobalLevel(Level level) {
		DEFAULT_LEVEL = level;
		Enumeration<String> loggerNames = LogManager.getLogManager().getLoggerNames();

		while (loggerNames.hasMoreElements()) {
			String name = loggerNames.nextElement();

			// ignore system loggers
			if (name.equals("") || name.equals("global")) {
				continue;
			}

			Logger logger = LogManager.getLogManager().getLogger(name);
			logger.setLevel(DEFAULT_LEVEL);
		}
	}

	public static Logger getLogger(String name) {
		return getLogger(name, DEFAULT_LEVEL);
	}

	protected static Handler[] getHandlers(boolean unsupervised) {
		if (unsupervised) {
			Handler errorHandler = new ConsoleHandler();
			errorHandler.setFormatter(new ASELogFormatter());
			errorHandler.setLevel(Level.SEVERE);

			try {
				if (logfileHandler == null) {
					logfileHandler = new FileHandler(logfilePath);
					logfileHandler.setFormatter(new ASELogFormatter());
					logfileHandler.setLevel(Level.ALL);
				}
				return new Handler[] { errorHandler, logfileHandler };
			}
			catch (IOException e) {
				System.err.println("Logger failed to open output file: " + logfilePath);
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

	/**
	 * Create a stderr handler where all severe messages will go and a filehandler where all messages will go
	 * 
	 * @param logfile
	 * @return
	 */
	protected static Handler[] getIndependentHandlers(String logfile) {
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

	public static Logger getIndependentLogger(String name, Level level, String logfile) {
		// check if the logger already exists
		Logger logger = LogManager.getLogManager().getLogger(name);	
		// Create new logger
		if (logger == null) {
			logger = Logger.getLogger(name);
			logger.setUseParentHandlers(false);
			logger.setLevel(level);
			for (Handler h : getIndependentHandlers(logfile)) {
				logger.addHandler(h);
			}
			independentLoggers.add(name);
		}
		else {
			assert independentLoggers.contains(name);
		}
		return logger;
	}

	public static Logger getLogger(String name, Level level) {
		// check if the logger already exists
		Logger logger = LogManager.getLogManager().getLogger(name);
		// Create new logger
		if (logger == null) {
			logger = Logger.getLogger(name);
			logger.setUseParentHandlers(false);
			logger.setLevel(level);
			for (Handler h : getHandlers(UNSUPERVISED_MODE)) {
				logger.addHandler(h);
			}
		}
		else {
			logger.setLevel(level);
		}
		return logger;
	}

	public static void main(String[] args) {
		LoggerFactory.setUnsupervisedMode(true);
		logger.finest("Finest!");
		LoggerFactory.setGlobalLevel(Level.FINEST);
		logger.finest("Finest!");
		logger2.finest("Finest2!");
		LoggerFactory.setGlobalLevel(Level.INFO);
		logger.finest("Finest!");
		logger.severe("HELP!");

	}
}
