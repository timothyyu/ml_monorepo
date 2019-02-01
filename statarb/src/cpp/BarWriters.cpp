#include "BarWriters.hpp"
#include <cstdlib>
#include <iostream>
#include <exception>
#include <fstream>
#include <boost/lexical_cast.hpp>
#include <boost/numeric/conversion/cast.hpp>
#include <boost/filesystem.hpp>
#include "gzstream.h"

////////// BarWriter ///////////

BarWriter::BarWriter() {

}

BarWriter::BarWriter(BarPipe &pipe) {
	this->pipe = &pipe;
}

BarWriter::~BarWriter() {

}

void BarWriter::operator()() {
	while (true) {
		BarPipe::item item = pipe->pop();
		if (item.second == false) {
			//this->finalize(); //hopefully it is the virtual finalize
			break;
		} else {
			this->write(item.first);
			continue;
		}
	}
}

////////// CompositeBarWriter ///////////

CompositeBarWriter::CompositeBarWriter() :
	BarWriter() {

}

CompositeBarWriter::CompositeBarWriter(BarPipe &pipe) :
	BarWriter(pipe) {
}

void CompositeBarWriter::addWriter(BarWriter &writer) {
	writers.push_back(&writer);
}

//should probably put things in a try block within the loop
void CompositeBarWriter::finalize() {
	for (std::vector<BarWriter *>::iterator it = writers.begin(); it != writers.end(); it++) {
		(*it)->finalize();
	}
}

void CompositeBarWriter::initialize() {
	for (std::vector<BarWriter *>::iterator it = writers.begin(); it != writers.end(); it++) {
		(*it)->initialize();
	}
}

void CompositeBarWriter::write(Bar &bar) {
	for (std::vector<BarWriter *>::iterator it = writers.begin(); it != writers.end(); it++) {
		(*it)->write(bar);
	}
}

void CompositeBarWriter::deleteWriters() {
	for (std::vector<BarWriter *>::iterator it = writers.begin(); it != writers.end(); it++) {
		delete *it;
	}
}

void CompositeBarWriter::prepare() {
	for (std::vector<BarWriter *>::iterator it = writers.begin(); it != writers.end(); it++) {
		(*it)->prepare();
	}
}

////////// SingleTextBarWriter ///////////
SingleFileBarWriter::SingleFileBarWriter(const char *ticker, int secid, int day, bool autoFlush) :
	BarWriter(), ticker(ticker), secid(secid), day(day), autoFlush(autoFlush), receivedValidBars(false) {

}

SingleFileBarWriter::SingleFileBarWriter(const char *ticker, int secid, int day, bool autoFlush, BarPipe &pipe) :
	BarWriter(pipe), ticker(ticker), secid(secid), day(day), autoFlush(autoFlush), receivedValidBars(false) {

}

void SingleFileBarWriter::initialize() {
	using namespace boost;
	using namespace boost::filesystem;

	filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in SingleFileBarWriter" << std::endl;
		exit(1);
	}

	filepath /= "bars";
	filepath /= lexical_cast<std::string> (day);

	//create the path if it doesn't exist
	create_directories(filepath);

	//open file
	filepath /= lexical_cast<std::string> (secid) + ".txt";
	file.open(filepath.string().c_str());

	if (!file.is_open()) {
		std::cout << "Failed to open file " << filepath.string() << std::endl;
		exit(1);
	}

	//write the header
	file << ticker << std::endl;
	if (autoFlush)
		file << std::flush;

	//std::cout<<"created file "<<filepath.string()<<std::endl;
}

void SingleFileBarWriter::finalize() {
	file.close();

	if (!receivedValidBars) {
		boost::filesystem::remove(filepath);
		//std::cout<<"deleting file "<<filepath.string()<<std::endl;
	}
}

void SingleFileBarWriter::write(Bar &bar) {
	using namespace boost;

	//filter bars based on secid
	if (bar.secid != this->secid)
		return;

	long ots = numeric_cast<long> (1000 * bar.open_ts.sec() + bar.open_ts.usec());
	long cts = numeric_cast<long> (1000 * bar.close_ts.sec() + bar.close_ts.usec());

	file << ots << "|" << cts << "|" << bar.open << "|" << bar.first << "|" << bar.high << "|" << bar.low << "|"
			<< bar.close << "|" << bar.volume << "|" << bar.trades << std::endl;
	if (autoFlush)
		file << std::flush;

	if (bar.open != -1)
		receivedValidBars = true;
}

void SingleFileBarWriter::prepare() {

}

////////// SingleScreenBarWriter ///////////
SingleScreenBarWriter::SingleScreenBarWriter(const char *ticker) :
	BarWriter(), ticker(ticker) {
}

SingleScreenBarWriter::SingleScreenBarWriter(const char *ticker, BarPipe &pipe) :
	BarWriter(pipe), ticker(ticker) {

}

void SingleScreenBarWriter::initialize() {

}

void SingleScreenBarWriter::finalize() {
}

void SingleScreenBarWriter::write(Bar &bar) {
	using namespace boost;

	//filter bars based on secid
	if (bar.ticker != this->ticker)
		return;

	std::cout << bar.outputHuman() << std::endl << std::flush;
}

void SingleScreenBarWriter::prepare() {

}

////////////BufferedZipBarWriter////////////
BufferedZipBarWriter::BufferedZipBarWriter(int day, bool live, int version) :
	BarWriter(), day(day), live(live), version(version) {
	if (version == 1) {
		barFolder = "bars";
		barFilePrefix = "bars_v1.txt";
        }
	else if (version == 2) {
		barFolder = "bars";
		barFilePrefix = "bars_v2.txt";
	}
	else {
		std::cerr << "What on earth does version " << version << " mean?" << std::endl;
		exit(1);
	}
}

BufferedZipBarWriter::BufferedZipBarWriter(int day, bool live, int version, BarPipe &pipe) :
	BarWriter(pipe), day(day), live(live), version(version) {
	if (version == 1) {
		barFolder = "bars";
		barFilePrefix = "bars_v1.txt";
        }
	else if (version == 2) {
		barFolder = "bars";
		barFilePrefix = "bars_v2.txt";
	}
	else {
		std::cerr << "What on earth does version " << version << " mean?" << std::endl;
		exit(1);
	}
}

BufferedZipBarWriter::BufferedZipBarWriter(int day, bool live, int version, std::string barFolder, std::string barFilePrefix) :
	BarWriter(), day(day), live(live), version(version), barFolder(barFolder), barFilePrefix(barFilePrefix) {
	if (version != 1 && version != 2) {
		std::cerr << "What on earth does version " << version << " mean?" << std::endl;
		exit(1);
	}
}

BufferedZipBarWriter::BufferedZipBarWriter(int day, bool live, int version, BarPipe &pipe, std::string barFolder,
		std::string barFilePrefix) :
	BarWriter(pipe), day(day), live(live), version(version), barFolder(barFolder), barFilePrefix(barFilePrefix) {
	if (version != 1 && version != 2) {
		std::cerr << "What on earth does version " << version << " mean?" << std::endl;
		exit(1);
	}
}

void BufferedZipBarWriter::initialize() {
	using namespace boost;
	using namespace boost::filesystem;

	path filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in SingleFileBarWriter" << std::endl;
		exit(1);
	}

	filepath /= barFolder;
	filepath /= lexical_cast<std::string> (day);

	//create the path if it doesn't exist
	create_directories(filepath);

	//open file
	filepath /= (barFilePrefix + ".live");
	file.open(filepath.string().c_str(), std::ios::out | std::ios::app);

	if (!file.is_open()) {
		std::cerr << "Couldn't open file " << filepath.string() << std::endl;
		exit(1);
	}
}

void BufferedZipBarWriter::write(Bar &bar) {
	using namespace boost;
	int secid = bar.secid;

	if (validBars.find(secid) == validBars.end()) {
		validBars[secid] = false;
		buffer[secid] = BarVector();
	}

	if (bar.open == -1) {
		buffer[secid].push_back(bar);
	} else if (bar.open != -1 && validBars[secid] == true) {
		outputBar(bar);
	} else //bar.open!=-1 and validBars[secid]==false
	{
		validBars[secid] = true;
		BarVector &bufferedBars = buffer[secid];
		bufferedBars.push_back(bar);
		for (BarVector::iterator it = bufferedBars.begin(); it != bufferedBars.end(); it++) {
			outputBar(*it);
		}
		bufferedBars.clear();
	}
}

void BufferedZipBarWriter::write(std::string out) {
	file << out << std::endl;
	//flush
	file.flush();
}

void BufferedZipBarWriter::outputBar(Bar &bar) {
	if (version == 1)
		file << bar.output_v1() << std::endl;
	else if (version == 2)
		file << bar.output_v2() << std::endl;
	//flush
	file.flush();
}

void BufferedZipBarWriter::finalize() {
	file.close();

	//temporary hack
	if (!live)
		return;

	boost::filesystem::path zipath = getenv("DATA_DIR");
	zipath /= barFolder;
	zipath /= boost::lexical_cast<std::string>(day);

	boost::filesystem::path lipath = zipath;
	boost::filesystem::path zopath = zipath;

	lipath /= (barFilePrefix + ".live");
	zipath /= (barFilePrefix + ".gz");
	zopath /= (barFilePrefix + ".gz.tmp");

	ogzstream zofile;
	zofile.open(zopath.c_str());
	igzstream zifile;
	zifile.open(zipath.c_str());
	std::string line;

	//merge live and existing zip into a new zip
	//if (zifile.is_open()) {
	while (getline(zifile, line))
		zofile << line << std::endl;
	zifile.close();
	//}

	//now append there the new bars
	std::ifstream lifile;
	lifile.open(lipath.c_str());
	//if (lifile.is_open()) {
	while (getline(lifile, line))
		zofile << line << std::endl;
	lifile.close();
	//}

	zofile.close();

	//now mop up
	boost::system::error_code ec;
	boost::filesystem::remove(zipath);
	boost::filesystem::remove(lipath);
	boost::filesystem::rename(zopath, zipath);
}

void BufferedZipBarWriter::prepare() {

}

////////////DayBarWriter////////////
DayBarWriter::DayBarWriter(int day, bool live) :
	BarWriter(), day(day), live(live), barFolder("bars"), barFilePrefix("daily_v1.txt") {
}

DayBarWriter::DayBarWriter(int day, bool live, BarPipe &pipe) :
	BarWriter(pipe), day(day), live(live), barFolder("bars"), barFilePrefix("daily_v1.txt") {
}

DayBarWriter::DayBarWriter(int day, bool live, std::string barFolder, std::string barFilePrefix) :
	BarWriter(), day(day), live(live), barFolder(barFolder), barFilePrefix(barFilePrefix) {
}

DayBarWriter::DayBarWriter(int day, bool live, BarPipe &pipe, std::string barFolder, std::string barFilePrefix) :
	BarWriter(pipe), day(day), live(live), barFolder(barFolder), barFilePrefix(barFilePrefix) {
}

void DayBarWriter::initialize() {
	using namespace boost;
	using namespace boost::filesystem;

	boost::filesystem::path filepath = getenv("DATA_DIR");
	if (!exists(filepath) || !is_directory(filepath)) {
		std::cerr << "Bad DATA_DIR directory in DayBarWriter" << std::endl;
		exit(1);
	}

	filepath /= barFolder;
	filepath /= lexical_cast<std::string> (day);

	//create the path if it doesn't exist
	create_directories(filepath);

	//open file
	filepath /= (barFilePrefix + ".live");
	file.open(filepath.string().c_str(), std::ios::out | std::ios::app);
	if (!file.is_open()) {
		std::cerr << "Couldn't open file " << filepath.string() << std::endl;
		exit(1);
	}
}

void DayBarWriter::write(Bar &bar) {
	double elow;
	double ehigh;

	if (bar.tradesSinceStart == 0) {
		elow = 0;
		ehigh = 0;
	} else {
		std::pair<double, double> p = bar.EHL(0.995);
		ehigh = p.first;
		elow = p.second;
	}

	file << bar.secid << "|" << bar.long_close_ts() << "|" << bar.openSinceStart << "|" << bar.highSinceStart << "|" <<bar.lowSinceStart << "|" << bar.closeSinceStart << "|" << ehigh<< "|" << elow << "|" << bar.vwapSinceStart << "|" <<bar.volumeSinceStart<< "|" << bar.tradesSinceStart << std::endl;
	//flush
	file.flush();
}

void DayBarWriter::write(std::string out) {
	file << out << std::endl;
	//flush
	file.flush();
}

void DayBarWriter::finalize() {
	file.close();

	//temporary hack
	if (!live)
		return;

	boost::filesystem::path zipath = getenv("DATA_DIR");
	zipath /= barFolder;
	zipath /= boost::lexical_cast<std::string>(day);

	boost::filesystem::path lipath = zipath;
	boost::filesystem::path zopath = zipath;

	lipath /= (barFilePrefix + ".live");
	zipath /= (barFilePrefix + ".gz");
	zopath /= (barFilePrefix + ".gz.tmp");

	ogzstream zofile;
	zofile.open(zopath.c_str());
	igzstream zifile;
	zifile.open(zipath.c_str());
	std::string line;

	//merge live and existing zip into a new zip
	//if (zifile.is_open()) {
	while (getline(zifile, line))
		zofile << line << std::endl;
	zifile.close();
	//}

	//now append there the new bars
	std::ifstream lifile;
	lifile.open(lipath.c_str());
	//if (lifile.is_open()) {
	while (getline(lifile, line))
		zofile << line << std::endl;
	lifile.close();
	//}

	zofile.close();

	//now mop up
	boost::system::error_code ec;
	boost::filesystem::remove(zipath);
	boost::filesystem::remove(lipath);
	boost::filesystem::rename(zopath, zipath);
}

void DayBarWriter::prepare() {
}
