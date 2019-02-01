#include <iostream>
#include <fstream>
#include <algorithm>
#include <vector>
#include <string>
#include <functional>
#include <utility>

#define BOOST_FILESYSTEM_VERSION 3
#include <boost/filesystem.hpp>
#include <boost/program_options.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/numeric/conversion/cast.hpp>
#include <boost/tokenizer.hpp>

#include "Client/lib2/TimedAggrLiveSource.h"
#include "Client/lib2/AggrDataFileSource.h"
#include "Client/lib2/LiveSource.h"
#include "Client/lib2/Itch2LiveSource.h"
#include "Client/lib2/Events.h"
#include "Client/lib2/CIndex.h"
#include "Client/lib2/EventSource.h"
#include "Common/SockMessage.h"
#include "Common/TowerNet.h"
#include "Common/TowerPort.h"
//#include "Util/Time.h"
#include "c_util/Time.h"
#include "holiday/HolidayList.h"

#include "Bar.hpp"
#include "Pipe.hpp"
#include "BarWriters.hpp"
#include "Mysql.hpp"
#include "MasterDataSource.hpp"

#include <ext/hash_map>
#include <ext/hash_set>
namespace std {
using namespace __gnu_cxx;
}

/////////////////////////////////
/////////////////////////////////
//
// TYPEDEFS
//
////////////////////////////////
////////////////////////////////

struct TInst;
typedef std::vector<Bar> BarVector;
typedef std::vector<int> SecidVector;
typedef std::vector<const char *> TickerVector;
typedef std::vector<std::string> StringVector;
typedef std::vector<TInst> TInstVector;
typedef std::hash_map<int, TInstVector> TickerHistory;
typedef std::hash_set<int> SecidSet;
typedef std::hash_map<int, SecidSet> Date2SecidSet;

using namespace trc::compat::util;

/////////////////////////////////
/////////////////////////////////
//
// BAR SIZE
//
////////////////////////////////
////////////////////////////////

int MINS_PER_BAR = 1;

////////////////////////////////
///////////////////////////////
//
// EXCHANGE BREAKDOWN SUMMARY
//
///////////////////////////////

bool GENERATE_EXCHANGE_SUMMARY = true;

////////////////////////////////
///////////////////////////////
//
// TRADE SIZE REPORT
//
///////////////////////////////

bool GENERATE_TRADE_SIZE_REPORT = true;

/////////////////////////////////
/////////////////////////////////
//
// BREAKPOINT FOR DECIDING BETWEEN 
// LEGACY AND MODERN RETRIEVAL
//
////////////////////////////////
////////////////////////////////

int BREAKPOINT = 20100112;

/////////////////////////////////
/////////////////////////////////
//
// READ THIS
//
////////////////////////////////
////////////////////////////////

int dummyCounter = 0;

struct TInst { //ticker instance
	int born;
	int died;
	std::string ticker;

	TInst(const char *ticker, long born, long died) {
		this->ticker = std::string(ticker);

		//there seems to be this issue where our epoch is from 1970 UTC, while for infra it is EST
		//until we understand this more, move dates by +5hours
		born += 5 * 60 * 60 * 1000;
		died += 5 * 60 * 60 * 1000;

		this->born = DateTime(TimeVal(born / 1000, 1000 * (born % 1000))).getintdate();
		this->died = DateTime(TimeVal(died / 1000, 1000 * (died % 1000))).getintdate();
	}
};

TickerHistory getTickerHistory(SecidVector &secids) //[from,to]
		{
	TickerHistory hist;

	sql::Connection *conn = Database::getConnection();
	sql::PreparedStatement *pst = conn->prepareStatement(
			"SELECT value,born,IFNULL(died,9999999999999) FROM xref WHERE secid=? AND xref_type=2 AND source=2 ORDER BY born ASC");

	for (SecidVector::iterator it = secids.begin(); it != secids.end(); it++) {
		int secid = *it;
		pst->setInt(1, secid);
		sql::ResultSet *res = pst->executeQuery();

		TInstVector vec;
		while (res->next()) {
			vec.push_back(TInst(res->getString(1).c_str(), boost::numeric_cast<long>(res->getInt64(2)), boost::numeric_cast<long>(res->getInt64(3))));
		}
		hist[secid] = vec;

		delete res;
	}

	delete pst;
	delete conn;

	return hist;
}

std::string getTickerInstance(int day, TInstVector &timeline) {
	for (TInstVector::iterator it = timeline.begin(); it != timeline.end(); it++) {
		if (day >= it->born && day < it->died) {
			return it->ticker;
		}
	}
	std::string dummy = "#" + boost::lexical_cast<std::string>(dummyCounter++);
	return dummy; //dummy string, hopefully no data for it
}

TInstVector getTickerInstances(int fromDay, int toDay, TInstVector &timeline) {
	TInstVector result;
	for (TInstVector::iterator it = timeline.begin(); it != timeline.end(); it++) {
		if (it->died <= fromDay || it->born >= toDay) {
			continue;
		} else {
			TInst tinst = *it;
			tinst.born = std::max(it->born, fromDay);
			tinst.died = std::min(it->died, toDay);
			result.push_back(tinst);
		}
	}

	return result;
}

////////////////////////////////////////////////
//
//
// MANIPULATE SECIDS AVAILABLE FOR A DAY
//
////////////////////////////////////////////////

std::string indexFileName = "superIndex.txt";

std::string getIndexFile(int day) {
	using namespace boost;
	using namespace boost::filesystem;

	boost::filesystem::path filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in getIndexFile" << std::endl;
		exit(1);
	}

	filepath /= "bars";
	if (day == 0) {
		DateTime dt;
		dt.setcurrent();
		day = dt.getintdate();
	}
	filepath /= lexical_cast<std::string>(day);
	filepath /= indexFileName;
	return filepath.string();
}

Date2SecidSet retrieved;

bool secidRetrieved(int day, int secid) {
	if (retrieved.find(day) == retrieved.end()) {
		//form the directory to the index file
		ifstream indexFile(getIndexFile(day).c_str());
		std::string line;
		SecidSet &secids = retrieved[day];
		if (indexFile.is_open()) {
			while (getline(indexFile, line)) {
				boost::tokenizer<> tok(line);
				secids.insert(boost::lexical_cast<int>(*(tok.begin())));
			}
			indexFile.close();
		}
		return secids.find(secid) != secids.end();
	} else {
		SecidSet secids = retrieved[day];
		return secids.find(secid) != secids.end();
	}
}

void appendSecidToIndex(int day, int secid, std::string ticker) {
	ofstream indexFile;
	indexFile.open(getIndexFile(day).c_str(), std::ios::out | std::ios::app);

	indexFile << secid << " " << ticker << std::endl;
	retrieved[day].insert(secid);

	indexFile.close();
}

void appendSecidToIndex(int day, SecidVector &secids, StringVector &tickers) {
	ofstream indexFile;
	indexFile.open(getIndexFile(day).c_str(), std::ios::out | std::ios::app);
	for (unsigned int ii = 0; ii < secids.size(); ii++) {
		indexFile << secids[ii] << " " << tickers[ii] << std::endl;
		retrieved[day].insert(secids[ii]);
	}
	indexFile.close();
}

////////////////////////////////////////////////
//
//
// VARIOUS BULLSHIT
//
////////////////////////////////////////////////

//holidays
HolidayList holidays;

void loadHolidays() {
	boost::filesystem::path holidayFilePath = "/apps/hyp2/live-opteron_rhel4/conf/holiday/us.holidays";
	if (!exists(holidayFilePath)) {
		std::cerr << "Could not load holiday schedule file" << std::endl;
		exit(1);
	}

	holidays.addFile(holidayFilePath.c_str());
}

void printUsageAndExit() {
	std::cout
			<< "Use as: [--day YYYYMMDD | --live | --from YYYYMMDD --to YYYYMMDD], [--tickers ticker1 ticker2 ... | --secids secid1 secid2 ... | --secidFiles]"
			<< std::endl;
	exit(1);
}

SecidVector getSecidsFromFile(std::string &filepath) {
	SecidVector secids;

	std::string line;
	std::ifstream file;
	file.open(filepath.c_str());

	if (!file.is_open()) {
		std::cerr << "Failed to open the secid file: " << filepath << std::endl;
		exit(1);
	}

	while (std::getline(file, line)) {
		secids.push_back(boost::lexical_cast<int>(line));
	}

	file.close();

	return secids;
}

int incrementDate(int date) {
	if (date < 19000000)
		return date + 1;

	TimeVal oneDay;
	//this is done because during november time changes, a day has 25 hours and
	//infra takes time zones into account
	oneDay.set(90000, 0);

	DateTime dt;
	dt.setintdate(date);

	return DateTime(dt.getTimeVal() + oneDay).getintdate();
}

TimeVal barOpenCeiling(TimeVal timestamp, TimeVal dayStart, TimeVal barlength) {
	TimeVal ceiling = dayStart;
	while (ceiling < timestamp)
		ceiling = ceiling + barlength;
	return ceiling;
}

////////////////////////////////////////////////
//
//
// LEGACY DATA RETRIEVAL
//
////////////////////////////////////////////////

//Check whether we should return a pointer,smart pointer or object
AggrDataFileSource *getLegacyDataSource(CIndex &cindex, const int sdint) {
	AggrDataFileSource *agg = new AggrDataFileSource();
	agg->setdate(sdint); //set the date

	const int n = cindex.size();
	for (int i = 0; i != n; i++) {
		const char *symbol = cindex[i];

		agg->addSource(new SIACTickFileSource(symbol));
		agg->addSource(new UTDFFileSource(symbol));
	}

	return agg;
}

//I don't like how events are continuously casted, but this will have to be the way
//until I better understand how msgtypes correspond to events and vice-versa
void parseLegacyEvent(Event *e, bool *success, std::string *symbol, int *size, float *price) {
	TickEvent *te = dynamic_cast<TickEvent*>(e);
	if (te != NULL) {
		*success = true;
		if (*success) {
			*symbol = te->Symbol();
			*price = te->Px();
			*size = te->Size();
		}
		return;
	}

	//failure
	*success = false;
	return;
}

void legacyDataRetrieval(int fromDay, int toDay, CIndex &cindex, SecidVector &secids, const int debug) {
	DateTime dt;
	DateTime dt1;
	dt1.setintdate(fromDay);
	DateTime dt2;
	dt2.setintdate(toDay);

	TimeVal oneDay;
	oneDay.set(86400, 0);

	for (dt = dt1; dt.getTimeVal() < dt2.getTimeVal(); dt = DateTime(dt.getTimeVal() + oneDay)) {
		int day = dt.getintdate();

		if (debug > 0)
			std::cout << "Starting day " << day << std::endl;

		if (!holidays.isBusinessDay(day, true)) {
			if (debug > 0)
				std::cout << "Not a business day" << std::endl;
			continue;
		}

		DateTime dayStart;
		dayStart.setintdate(day);
		dayStart.settime(9, 30, 00);
		//Trading day end
		DateTime dayEnd;
		dayEnd.setintdate(day);
		dayEnd.settime(16, 00, 00);

		//bar length
		TimeVal barLength(MINS_PER_BAR * 60, 0);
		TimeVal barStart = dayStart.getTimeVal(); //first bar start [
		TimeVal barEnd = barStart + barLength; //first bar end )

		//get data source
		AggrDataFileSource *source = getLegacyDataSource(cindex, day);

		if (debug > 0)
			std::cout << "Data source retrieved" << std::endl;

		typedef Pipe<Bar> BarPipe;
		BarPipe pipe; //pipe for piping bars to be written to the writer (thread)
		CompositeBarWriter writer(pipe);

		//create the bars and the writers
		BarVector bars;
		//only write if debug
		if (debug > 0) {
			for (unsigned int i = 0; i != secids.size(); i++) {
				bars.push_back(Bar(secids[i], cindex[i], barStart, barEnd));
				BarWriter *w = new SingleScreenBarWriter(cindex[i]);
				writer.addWriter(*w);
			}
		} else {
			BarWriter *w = new BufferedZipBarWriter(day, false, 1);
			writer.addWriter(*w);
			w = new DayBarWriter(day, false);
			writer.addWriter(*w);
			for (unsigned int i = 0; i != secids.size(); i++) {
				bars.push_back(Bar(secids[i], cindex[i], barStart, barEnd));
			}
		}

		if (debug > 0)
			std::cout << "Initializing writers" << std::endl << std::flush;

		//init writers
		writer.initialize();

		if (debug > 0)
			std::cout << "Launching writer thread" << std::endl << std::flush;

		//launch writer thread
		boost::thread backgroundWriter(boost::ref(writer));

		if (debug > 0)
			std::cout << "Entering main loop" << std::endl << std::flush;

		bool stop = false;
		//get events
		while (!stop) {
			//current event info
			float price;
			int size;
			bool success;
			std::string ticker;
			TimeVal timestamp;

			Event *event = source->next(); //current event
			if (debug >= 3 && event != NULL)
				std::cout << event->print() << std::endl;

			if (event == NULL) //end of events
					{
				timestamp = dayEnd.getTimeVal();
				stop = true;
			} else {
				timestamp = event->livetv;
			}

			if (timestamp >= dayEnd.getTimeVal()) {
				stop = true;
				timestamp = dayEnd.getTimeVal();
			}

			//timestamp = std::min(timestamp, dayEnd.getTimeVal()); //truncate timestamp to end of trading day

			//modified since we can start mid day
			//if (timestamp < dayStart.getTimeVal()) //ignore pre-trading trades
			if (timestamp < barStart)
				continue;

			//rollover bars if needed. as many times as necessary if time between events spans multiple bar intervals (unlikely)
			while (barEnd <= timestamp) {
				//the new bar start and end times
				barStart = barEnd;
				//barEnd = std::min(barStart + barLength, dayEnd.getTimeVal()); //truncate end of bar to end of trading day
				barEnd = barStart + barLength;

				//push the bars to pipe. the bars are *copied*. also roll them over
				for (BarVector::iterator it = bars.begin(); it != bars.end(); it++) {
					pipe.push(*it);
					it->rollover(barEnd);
				}
			}

			//if the start of the new bar exceeds the end of trading day,we are done. note the equality in the condition. we assume
			//that the trading day is [dayStart,dayEnd)
			if (stop) {
				if (event != NULL) {
					Event *ec = event->cloneEvent();
					source->insert(ec);
				}
				break;
			}

			//finally, try to see if the event is a trade and parse it
			parseLegacyEvent(event, &success, &ticker, &size, &price);
			if (success && cindex[ticker.c_str()] >= 0) {
				bars[cindex[ticker.c_str()]].update(size, price);
				if (debug >= 2) {
					std::cout << "TRADE!: " << event->print() << std::endl;
				}
			}
		}

		if (debug > 0)
			std::cout << "Finishing..." << std::endl;
		//close the pipe
		pipe.close();
		backgroundWriter.join();

		//finalize writers
		writer.finalize();

		//delete them
		writer.deleteWriters();

		//kill the source
		delete source;
	}
}

////////////////////////////////////////////////
//
//
// TRADERSTUMP BASED DATA RETRIEVAL
//
////////////////////////////////////////////////

std::string createImbalanceEntry(Imbalance &imb, Bar &bar, TimeVal ts) {
	std::stringstream ss;
	long lts = boost::numeric_cast<long>(1000 * ts.sec() + ts.usec()/1000);
	ss << bar.secid << "|" << lts << "|" << imb.matched << "|" << imb.imbalance << "|" << imb.refPrice << "|" << imb.nearPrice << "|" << imb.farPrice << "|"
			<< bar.lastTick << "|" << bar.lastBidPrice << "|" << bar.lastAskPrice<< "|"<<imb.exchange;
	return ss.str();
}

//Check whether we should return a pointer,smart pointer or object
MasterDataSource *getModernDataSource(CIndex &cindex, const int sdint, int debug, Task task) {
	MasterDataSourceConfig config(sdint, cindex, debug, task, true);
	MasterDataSource *source = new MasterDataSource(config);

	return source;
}

void dumpVolSummary(int day, bool *relMMs, std::vector<std::hash_map<int, int> > &volSummary, SecidVector &secids) {
	using namespace boost;
	using namespace boost::filesystem;
	
	if (secids.empty())
		return;
		
	boost::filesystem::path filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in DayBarWriter" << std::endl;
		exit(1);
	}

	filepath /= "bars";
	filepath /= lexical_cast<std::string> (day);
	create_directories(filepath);
	filepath /= ("volsum.txt");
	std::ofstream file;
	file.open(filepath.string().c_str(), std::ios::out | std::ios::app);
	if (!file.is_open()) {
		std::cerr << "Couldn't open file " << filepath.string() << std::endl;
		exit(1);
	}

	//header
	file << "secid";
	for (int mm = 0; mm < NUM_MARKET_MAKERS; mm++) {
		if (relMMs[mm])
			file << "|" << MarketMakerDesc[mm];
	}
	file << std::endl;
	
	int ii = 0;
	for (std::vector<std::hash_map<int, int> >::iterator secVolSum = volSummary.begin(); secVolSum != volSummary.end(); secVolSum++, ii++) {
		file << secids[ii];
		for (int mm = 0; mm < NUM_MARKET_MAKERS; mm++) {
			if (relMMs[mm]) {
				std::hash_map<int, int>::iterator e = secVolSum->find(mm);
	                        int trades = (e != secVolSum->end())? e->second : 0;
        	                file << "|" << trades;
			}
		}
		file << std::endl;
	} 

	file.close();
}

void dumpTradeSzInfo(int day, std::vector<std::hash_map<int, int> > &tradeSzInfo, SecidVector &secids) {
	using namespace boost;
	using namespace boost::filesystem;

	if (secids.empty())
		return;

	boost::filesystem::path filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in DayBarWriter" << std::endl;
		exit(1);
	}

	filepath /= "bars";
	filepath /= lexical_cast<std::string> (day);
	create_directories(filepath);
	filepath /= ("tradeSz.txt");
	std::ofstream file;
	file.open(filepath.string().c_str(), std::ios::out | std::ios::app);
	if (!file.is_open()) {
		std::cerr << "Couldn't open file " << filepath.string() << std::endl;
		exit(1);
	}

	//header
	file << "secid|size|count" << std::endl;

	int ii = 0;
	for (std::vector<std::hash_map<int, int> >::iterator secTradeSz = tradeSzInfo.begin(); secTradeSz != tradeSzInfo.end(); secTradeSz++, ii++) {
		for (std::hash_map<int, int>::iterator szPair = secTradeSz->begin(); szPair != secTradeSz->end(); szPair++) {
			file << secids[ii] << "|" << szPair->first << "|" << szPair->second << std::endl;
		}
	}

	file.close();
}

void modernDataRetrieval(int fromDay, int toDay, CIndex &cindex, SecidVector &secids, const int debug, Task task) {

	TimeVal oneDay;
	oneDay.set(86400, 0);

	bool live = false;
	if (fromDay == 0) { //assume live data if day==0
		DateTime dt;
		dt.setcurrent();
		fromDay = dt.getintdate();
		dt = DateTime(dt.getTimeVal() + oneDay);
		toDay = dt.getintdate();
		live = true;
	}

	DateTime dt;
	DateTime dt1;
	dt1.setintdate(fromDay);
	DateTime dt2;
	dt2.setintdate(toDay);

	for (dt = dt1; dt.getTimeVal() < dt2.getTimeVal(); dt = DateTime(dt.getTimeVal() + oneDay)) {
		int day = dt.getintdate();

		if (debug > 0)
			std::cout << "Starting day " << day << std::endl;

		if (!holidays.isBusinessDay(day, true)) {
			if (debug > 0)
				std::cout << "Not a business day" << std::endl;
			continue;
		}

		DateTime dayStart;
		dayStart.setintdate(day);
		dayStart.settime(9, 30, 00);
		//Trading day end
		DateTime dayEnd;
		dayEnd.setintdate(day);
		dayEnd.settime(16, 00, 00);

		//bar length
		TimeVal barLength(MINS_PER_BAR * 60, 0); 
		TimeVal barStart; //first bar start [
		if (live) {
			barStart = std::max(dayStart.getTimeVal(), barOpenCeiling(TimeVal().setcurrent(), dayStart.getTimeVal(), barLength));
		} else {
			barStart = dayStart.getTimeVal();
		}
		TimeVal barEnd = barStart + barLength; //first bar end )

		MasterDataSource *source = getModernDataSource(cindex, live ? 0 : day, debug, task);

		if (debug > 0)
			std::cout << "Data source retrieved" << std::endl;

		typedef Pipe<Bar> BarPipe;
		BarPipe pipe; //pipe for piping bars to be written to the writer (thread)
		CompositeBarWriter writer(pipe);
		DayBarWriter *imbWriter; //use a daybar writer for imblances

		//create the bars and the writers
		BarVector bars;
		std::vector<std::hash_map<int, int> > volSummary(secids.size());
		std::vector<std::hash_map<int, int> > tradeSzInfo(secids.size());
		bool relMMs[NUM_MARKET_MAKERS];
		for (int i = 0; i < NUM_MARKET_MAKERS; i++) relMMs[i] = false;
		//only write if debug
		if (debug >= 1) {
			for (unsigned int i = 0; i != secids.size(); i++) {
				std::cout << secids[i] << " " << cindex[i] << std::endl << std::flush;
				bars.push_back(Bar(secids[i], cindex[i], barStart, barEnd));
				BarWriter *w = new SingleScreenBarWriter(cindex[i]);
				writer.addWriter(*w);
			}
			imbWriter = NULL;
		} else {
			int version;
			if (task == ASE_V1)
				version = 1;
			else if (task == ASE_V2)
				version = 2;
			else {
				std::cerr << "What sort of task is this?" << std::endl;
				exit(1);
			}

			BarWriter *w = new BufferedZipBarWriter(day, live, version);
			writer.addWriter(*w);
			w = new DayBarWriter(day, live);
			writer.addWriter(*w);
			for (unsigned int i = 0; i != secids.size(); i++) {
				bars.push_back(Bar(secids[i], cindex[i], barStart, barEnd));
			}
			imbWriter = new DayBarWriter(day, live, "bars", "imb_v1.txt");
		}

		if (debug > 0)
			std::cout << "Initializing writers" << std::endl << std::flush;

		//init writers
		writer.initialize();
		if (imbWriter != NULL)
			imbWriter->initialize();

		if (debug > 0)
			std::cout << "Launching writer thread" << std::endl << std::flush;

		//launch writer thread
		boost::thread backgroundWriter(boost::ref(writer));

		if (debug > 0)
			std::cout << "Entering main loop" << std::endl << std::flush;

		bool stop = false;
		TimeVal timestamp;
		Tick tick;
		Quote quote;
		Imbalance imb;
		//get events
		while (!stop) {
			bool moreData;
			bool hasTick = false;
			bool hasQuote = false;
			bool hasImbalance = false;

			moreData = source->nextEvent();

			if (debug >= 3) {
				if (source->getEvent() != NULL)
					std::cout << source->getEvent()->print() << std::endl;
				else
					std::cout << "NULL event" << std::endl;
			}

			if (!moreData) {
				timestamp = dayEnd.getTimeVal();
				stop = true;
			} else if (!source->hasNewTick() && !source->hasNewQuote()) {
				continue;
			} else {
				timestamp = source->curtv();
				if (source->hasNewQuote()) {
					hasQuote = true;
					quote = source->getQuote();
				}
				if (source->hasNewTick()) {
					hasTick = true;
					tick = source->getTick();
				}
				if (source->hasNewImbalance()) {
					hasImbalance = true;
					imb = source->getImbalance();
				}
			}

			if (timestamp >= dayEnd.getTimeVal()) {
				stop = true;
				timestamp = dayEnd.getTimeVal();
			}

			//timestamp = std::min(timestamp, dayEnd.getTimeVal()); //truncate timestamp to end of trading day

			if (timestamp < dayStart.getTimeVal()) //ignore pre-trading trades
				continue;

			//rollover bars if needed. as many times as necessary if time between events spans multiple bar intervals (unlikely)
			while (barEnd <= timestamp) {
				//the new bar start and end times
				barStart = barEnd;
				//barEnd = std::min(barStart + barLength, dayEnd.getTimeVal()); //truncate end of bar to end of trading day
				barEnd = barStart + barLength;

				//digest the info in the bars
				//push the bars to pipe. the bars are *copied*. also roll them over
				writer.prepare();
				for (BarVector::iterator it = bars.begin(); it != bars.end(); it++) {
					it->digest();
					pipe.push(*it);
					it->rollover(barEnd);
				}
			}

			//if the start of the new bar exceeds the end of trading day,we are done. note the equality in the condition. we assume
			//that the trading day is [dayStart,dayEnd)
			if (stop) {
				break;
			}

			int cid = -1;
			if (hasTick && hasQuote && debug >= 2) {
				std::cout << "Quote and tick at the same time" << std::endl;
			}

			//////////////////////////////////

			if (hasTick && debug >= 2) {
				std::cout << "Tick " << DateTime(timestamp).gettimestring() << " " << source->getSymbol(tick.cid) << " " << tick.size << " " << tick.price
						<< " " << MarketMakerDesc[tick.mm] << " " << tick.ths << " " << tick.is_bookupdate << std::endl;
				cid = tick.cid;
			}
			if (hasTick && tick.size > 0 && tick.price > 0 && (tick.type == lib3::TT_NORMAL || tick.type == lib3::TT_HIDDEN || tick.type == lib3::TT_IMPLIED)
					&& timestamp >= barStart) {
				int pos = cindex[source->getSymbol(tick.cid)];
				if (pos >= 0) {
					bars[pos].update(tick, source->getBook(), timestamp);
					volSummary[pos][(int)tick.mm] += tick.size;
					tradeSzInfo[pos][(int)tick.size] += 1;
					relMMs[(int)tick.mm] = true;
				}
			}

			/////////////////////////////////

			if (hasQuote && debug >= 2) {
				std::cout << "Quote " << DateTime(timestamp).gettimestring() << " " << source->getSymbol(quote.bo->cid) << " "
						<< lib3::QuoteReasonDesc[quote.reason] << " " << quote.shares_delta << " " << quote.bo->px << " " << MarketMakerDesc[quote.bo->mm]
						<< " " << quote.bo->dir << std::endl;
				cid = quote.bo->cid;
			}
			if (hasQuote) {
				int pos = cindex[source->getSymbol(quote.bo->cid)];
				if (pos >= 0)
					bars[pos].update(quote, source->getBook(), timestamp);
			}

			//////////////////////////////////////

			if (hasImbalance && debug >=2) {
				std::cout << "Imbalance " << DateTime(timestamp).gettimestring() << " " << source->getSymbol(imb.cid) << " " << imb.matched << " " << imb.imbalance << " "
						<< imb.refPrice << " " << imb.nearPrice << " " << imb.farPrice << std::endl;
				//std::cout << createImbalanceEntry(imb, bars[cindex[source->getSymbol(imb.cid)]], timestamp) <<std::endl;
			}

			if (hasImbalance && imb.cid>=0 && cindex[source->getSymbol(imb.cid)] >= 0) {
				imbWriter->write(createImbalanceEntry(imb, bars[cindex[source->getSymbol(imb.cid)]], timestamp));
			}

			///////////////////////////////////////////////

			if ((hasQuote || hasTick) && task == ASE_V2 && debug >= 2) {
				std::cout << source->getBook()->print_book(cid, 3) << std::endl;
			}
		}

		if (debug > 0)
			std::cout << "Finishing..." << std::endl;
		//close the pipe
		pipe.close();
		backgroundWriter.join();

		//finalize writers
		writer.finalize();
		if (imbWriter != NULL)
			imbWriter->finalize();

		//delete them
		writer.deleteWriters();
		if (imbWriter != NULL)
			delete imbWriter;

		if (GENERATE_EXCHANGE_SUMMARY)
			dumpVolSummary(day, relMMs, volSummary, secids);

		if (GENERATE_TRADE_SIZE_REPORT)
			dumpTradeSzInfo(day, tradeSzInfo, secids);

		//kill the source
		// GREATE JOB CLEANING UP MEMORY INFRA...
		//delete source;
	}
}

////////////////////////////////////////////////
//
//
// MAIN
//
////////////////////////////////////////////////

void dataRetrieval(int fromDay, int toDay, StringVector &tickers, const int debug, Task task) {
	//Map tickers to fake secids.
	CIndex cindex;
	SecidVector dummySecids(tickers.size());
	for (StringVector::iterator it = tickers.begin(); it != tickers.end(); it++) {
		cindex.add(it->c_str());
	}

	if (fromDay == 0) //live
			{
		modernDataRetrieval(fromDay, toDay, cindex, dummySecids, debug, task);
	} else {
		//Get both for debugging purposed.
		//legacyDataRetrieval(fromDay, toDay, cindex, dummySecids, debug);
		modernDataRetrieval(fromDay, toDay, cindex, dummySecids, debug, task);
	}
}

void dataRetrieval(int fromDay, int toDay, SecidVector &secids, TickerHistory &tickerHistory, const int debug, Task task) {
	static const int partitionDate = BREAKPOINT;
	//partition appropriately
	if (fromDay != 0 && fromDay < partitionDate && toDay > partitionDate) {
		dataRetrieval(fromDay, partitionDate, secids, tickerHistory, debug, task);
		dataRetrieval(partitionDate, toDay, secids, tickerHistory, debug, task);
	} else if (fromDay == 0 || fromDay >= partitionDate) { //modern retrieval, on a per day basis for all secids
		for (int day = fromDay; day < toDay; day = incrementDate(day)) {
			//get the appropriate tickers
			SecidVector subsecids;
			StringVector subtickers;
			CIndex cindex;
			for (SecidVector::iterator it = secids.begin(); it != secids.end(); it++) {
				int secid = *it;

				if (debug == 0 && secidRetrieved(day, secid))
					continue;

				std::string ticker;
				if (fromDay == 0) {
					ticker = getTickerInstance(DateTime().setcurrent().getintdate(), tickerHistory[secid]);
				} else {
					ticker = getTickerInstance(day, tickerHistory[secid]);
				}

				if (cindex[ticker.c_str()] >= 0) {
					std::cerr << "Ticker conflict! Secid " << secid << " and " << subsecids[cindex[ticker.c_str()]] << " share ticker " << ticker
							<< ". Not getting data for " << subsecids[cindex[ticker.c_str()]] << std::endl << std::flush;
					continue;
				}

				cindex.add(ticker.c_str()); //cindex copies the char array internally
				subsecids.push_back(secid);
				subtickers.push_back(ticker);
			}
			modernDataRetrieval(day, incrementDate(day), cindex, subsecids, debug, task);
			if (debug == 0)
				appendSecidToIndex(day, subsecids, subtickers);
		}
	}
	/*else { //legacy retrieval
	 for (int day = fromDay; day < toDay; day = incrementDate(day)) {
	 int n = secids.size();
	 int step = 50;
	 int startPos = 0;
	 int stopPos = std::min(n, startPos + step);

	 while (startPos < stopPos) {
	 //get the appropriate tickers
	 SecidVector subsecids;
	 CIndex cindex;
	 for (int pos = startPos; pos < stopPos; pos++) {
	 //for (SecidVector::iterator it = secids.begin(); it != secids.end(); it++) {
	 //int secid = *it;
	 int secid = secids[pos];

	 if (debug == 0 && secidRetrieved(day, secid))
	 continue;

	 std::string ticker = getTickerInstance(day, tickerHistory[secid]);
	 if (cindex[ticker.c_str()] >= 0) {
	 std::cerr << "Ticker conflict! Secid " << secid << " and " << subsecids[cindex[ticker.c_str()]] << " share ticker " << ticker
	 << ". Not getting data for " << subsecids[cindex[ticker.c_str()]] << std::endl << std::flush;
	 continue;
	 }

	 cindex.add(ticker.c_str()); //cindex copies the char array internally
	 subsecids.push_back(secid);
	 }
	 legacyDataRetrieval(day, incrementDate(day), cindex, subsecids, debug);
	 if (debug == 0)
	 appendSecidToIndex(day, subsecids);

	 startPos = stopPos;
	 stopPos = std::min(n, startPos + step);
	 }
	 }
	 }*/
	else { //legacy retrieval,
		   //for each security
		for (SecidVector::iterator it = secids.begin(); it != secids.end(); it++) {
			int secid = *it;
			SecidVector subsecids;
			subsecids.push_back(secid);
			//segment range according to secid ticker history
			TInstVector secTickers = getTickerInstances(fromDay, toDay, tickerHistory[secid]);
			//for each consecutive range on which it had the same ticker
			for (TInstVector::iterator it2 = secTickers.begin(); it2 != secTickers.end(); it2++) {
				TInst tinst = *it2;
				int subFrom = tinst.born;
				int subTo = tinst.died;
				CIndex cindex;

				cindex.add(tinst.ticker.c_str()); //WARNING,noone will touch tickers, c_str points internally to tickers

				//finally for each day
				for (int day = subFrom; day < subTo; day = incrementDate(day)) {
					if (secidRetrieved(day, secid))
						continue;
					legacyDataRetrieval(day, incrementDate(day), cindex, subsecids, debug);
					if (debug == 0)
						appendSecidToIndex(day, secid, tinst.ticker);
				}
			}
		}
	}

}

int main(int argc, char **argv) {
	//parse arguments
	namespace po = boost::program_options;
	po::options_description desc("Allowed options");
	desc.add_options()("day", po::value<int>(), "set date YYYYMMDD")("live", "read live data")("tickers", po::value<StringVector>()->multitoken(),
			"tickers and secids as ticker:secid")("secids", po::value<SecidVector>()->multitoken(), "secids")("from", po::value<int>(),
			"set from date YYYYMMDD (closed interval)")("to", po::value<int>(), "set to date YYYYMMDD (open interval)")("debug", po::value<int>(),
			"debug level 0:nothing, 1:print bars, 2:print trades, 3:print events")("secidFile", po::value<std::string>(), "files of secids")("groupSize",
			po::value<int>(), "partition secids")("v1", "v1 bars")("v2", "v2 bars")("mins",po::value<int>(),"number of mins per bars")("breakpoint",po::value<int>(),
			"breakpoint for deciding between legacy and modern retrieval");

	po::variables_map vm;
	po::store(boost::program_options::parse_command_line(argc, argv, desc), vm);
	po::notify(vm);

	if (vm.count("mins")) {
		MINS_PER_BAR = vm["mins"].as<int>();
	}

	if (vm.count("breakpoint")) {
		BREAKPOINT = vm["breakpoint"].as<int>();
	}

	int debug = 0;
	if (vm.count("debug")) {
		std::cout.setf(std::ios::unitbuf); //turn on buffering on stdout
		debug = vm["debug"].as<int>();
	}

	bool live = false;
	if (vm.count("live")) {
		live = true;
	}

	int day = 0;
	if (vm.count("day")) {
		day = vm["day"].as<int>();
	}

	int fromDay = 0;
	if (vm.count("from")) {
		fromDay = vm["from"].as<int>();
	}

	int toDay = 0;
	if (vm.count("to")) {
		toDay = vm["to"].as<int>();
	}

	Task task = ASE_V2;
	if (vm.count("v2")) {
		task = ASE_V2;
	}
	else if (vm.count("v1")) {
		task = ASE_V1;
	}

	//exclusive or: one of --live, --date, --from --to must be set
	bool singleDay = (day > 0);
	bool dayRange = (fromDay > 0 && toDay > 0);

	if (!((singleDay && !dayRange && !live) || (!singleDay && dayRange && !live) || (!singleDay && !dayRange && live))) {
		printUsageAndExit();
	}

	StringVector tickers;
	if (vm.count("tickers")) {
		tickers = vm["tickers"].as<StringVector>();
		debug = std::max(1, debug); //increase debug level to at least 1
	}

	SecidVector secids;
	if (vm.count("secids")) {
		secids = vm["secids"].as<SecidVector>();
	} else if (vm.count("secidFile")) {
		std::string filepath = vm["secidFile"].as<std::string>();
		secids = getSecidsFromFile(filepath);
	}

	int groupSize = 100;
	if (vm.count("groupSize")) {
		groupSize = vm["groupSize"].as<int>();
	}

	bool usingSecids = std::max(vm.count("secids"), vm.count("secidFile"));
	bool usingTickers = vm.count("tickers");

	if (!(usingSecids ^ usingTickers)) {
		printUsageAndExit();
	}

	//if single day, convert it to dummy range
	if (day > 0) {
		fromDay = day;
		toDay = day + 1;
	} else if (live) {
		fromDay = 0;
		toDay = 1;
	}

	//Get mapping of secids to tickers
	TickerHistory tickerHist;
	if (usingSecids) {
		tickerHist = getTickerHistory(secids);
	} else if (usingTickers) {
		//insert dummy secids.
		secids.clear();
		secids.insert(secids.begin(), tickers.size(), 0);
	}

	//load holidays
	loadHolidays();

	if (usingTickers) {
		dataRetrieval(fromDay, toDay, tickers, debug, task);
	} else if (usingSecids) {
		dataRetrieval(fromDay, toDay, secids, tickerHist, debug, task);
	}
}
