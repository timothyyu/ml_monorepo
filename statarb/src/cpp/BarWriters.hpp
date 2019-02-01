#ifndef BARWRITERS_HPP_
#define BARWRITERS_HPP_

#include <vector>
#include <fstream>
#include "Pipe.hpp"
#include "Bar.hpp"
#define BOOST_FILESYSTEM_VERSION 3
#include <boost/filesystem.hpp>
#include <ext/hash_map>

namespace std {
using namespace __gnu_cxx;
}

class PassThoughWriter {

};

class BarWriter {
protected:
	typedef Pipe<Bar> BarPipe;
	BarPipe *pipe;
public:
	BarWriter();
	BarWriter(BarPipe &pipe);
	virtual ~BarWriter()=0;
	virtual void initialize()=0;
	virtual void finalize()=0;
	virtual void write(Bar &bar)=0;
	virtual void prepare()=0;
	void operator()(); //The thread recursion code
};

class CompositeBarWriter: public BarWriter {
protected:
	std::vector<BarWriter *> writers;
public:
	CompositeBarWriter();
	CompositeBarWriter(BarPipe &pipe);
	void addWriter(BarWriter &writer);
	void deleteWriters();
	void finalize();
	void initialize();
	void write(Bar &bar);
	void prepare();
};

class SingleFileBarWriter: public BarWriter {
protected:
	std::string ticker;
	int secid;
	int day;
	bool autoFlush;
	bool receivedValidBars;
	std::ofstream file;
	boost::filesystem::path filepath;
public:
	SingleFileBarWriter(const char *ticker, int secid, int day, bool autoFlush);
	SingleFileBarWriter(const char *ticker, int secid, int day, bool autoFlush, BarPipe &pipe);
	void finalize();
	void initialize();
	void write(Bar &bar);
	void prepare();
};

class SingleScreenBarWriter: public BarWriter {
protected:
	std::string ticker;
public:
	SingleScreenBarWriter(const char *ticker);
	SingleScreenBarWriter(const char *ticker, BarPipe &pipe);
	void finalize();
	void initialize();
	void write(Bar &bar);
	void prepare();
};

class BufferedZipBarWriter: public BarWriter {
protected:
	typedef std::hash_map<int, bool> SecidValidBars;
	typedef std::hash_map<int, std::vector<Bar> > SecidBarBuffer;
	typedef std::vector<Bar> BarVector;
	int day;
	bool live;
        int version;
	SecidValidBars validBars;
	SecidBarBuffer buffer;
	std::ofstream file;
	std::string barFolder;
	std::string barFilePrefix;
	void outputBar(Bar &bar);
public:
	BufferedZipBarWriter(int day, bool live, int version);
	BufferedZipBarWriter(int day, bool live, int version, BarPipe &pipe);
	BufferedZipBarWriter(int day, bool live, int version, std::string barFolder, std::string barFilePrefix);
	BufferedZipBarWriter(int day, bool live, int version, BarPipe &pipe, std::string barFolder, std::string barFilePrefix);
	void finalize();
	void initialize();
	void write(Bar &bar);
	void write(std::string out);
	void prepare();
};

class DayBarWriter: public BarWriter {
protected:
	int day;
	bool live;
	std::ofstream file;
	std::string barFolder;
	std::string barFilePrefix;
	boost::filesystem::path filepath;
	void outputBar(Bar &bar);
public:
	DayBarWriter(int day, bool live);
	DayBarWriter(int day, bool live, BarPipe &pipe);
	DayBarWriter(int day, bool live, std::string barFolder, std::string barFilePrefix);
	DayBarWriter(int day, bool live, BarPipe &pipe, std::string barFolder, std::string barFilePrefix);
	void finalize();
	void initialize();
	void write(Bar &bar);
	void write(std::string out);
	void prepare();
};

#endif /* BARWRITERS_HPP_ */
