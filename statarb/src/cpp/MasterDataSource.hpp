#ifndef MASTERDATASOURCE_HPP_
#define MASTERDATASOURCE_HPP_

#include "traderstump/TraderStump.h"
#include "traderstump/TraderConfig.h"
#include "c_util/Time.h"

using namespace trc::compat::util;
enum Task {ASE_V1, ASE_V2};

struct Tick {
	int cid;
	int size;
	double price;
	MarketMaker mm;
	lib3::TickHandlerSource ths;
	lib3::TickType type;
	bool is_bookupdate;

	Tick(int cid, int size, double price, MarketMaker mm,
			lib3::TickHandlerSource ths, lib3::TickType type, bool is_bookupdate) :
		cid(cid), size(size), price(price), mm(mm), ths(ths), type(type), is_bookupdate(is_bookupdate) {
	}

	Tick() {

	}
};

struct Quote {
	int book_id;
	lib3::BookOrder *bo;
	lib3::QuoteReason reason;
	int shares_delta;
	bool done;

	Quote(int book_id, lib3::BookOrder *bo, lib3::QuoteReason reason,
			int shares_delta, bool done) :
		book_id(book_id), bo(bo), reason(reason), shares_delta(shares_delta),
				done(done) {
	}

	Quote() {

	}
};

struct Imbalance {
	int cid;
	int matched;
	int imbalance;
	double refPrice;
	double nearPrice;
	double farPrice;
	char exchange;

	Imbalance(int cid, int matched, int imbalance, double refPrice, double nearPrice, double farPrice, char exchange): cid(cid), matched(matched), imbalance(imbalance),
			refPrice(refPrice), nearPrice(nearPrice), farPrice(farPrice), exchange(exchange){
	}

	Imbalance() {
	}
};

class MasterDataSourceConfig: public lib3::TraderConfig {
public:
	Task task;
	int debug;
	bool withImbalance;
	MasterDataSourceConfig(int day, CIndex &cindex, int debug, Task task, bool withImbalance);
	int getDebugLevel();
};

class MasterDataSource: public lib3::TraderStump {
protected:
	Tick *tick;
	Event *event;
	Quote *quote;
	Imbalance *imb;
	bool errorOnDuplicates;
public:
	bool hasNewTick() {
		return tick != NULL;
	}

	Tick getTick() {
		if (tick != NULL) {
			Tick tmp = *tick;
			delete tick;
			tick = NULL;
			return tmp;
		} else {
			return Tick();
		}
	}

	bool hasNewQuote() {
		return quote != NULL;
	}

	Quote getQuote() {
		if (quote != NULL) {
			Quote tmp = *quote;
			delete quote;
			quote = NULL;
			return tmp;
		} else {
			return Quote();
		}
	}

	bool hasNewImbalance() {
		return imb != NULL;
	}

	Imbalance getImbalance() {
		if (imb != NULL) {
			Imbalance tmp = *imb;
			delete imb;
			imb = NULL;
			return tmp;
		} else {
			return Imbalance();
		}
	}

	Event * getEvent() {
		return this->event;
	}

	TimeVal curtv() {
		return ecb->curtv();
	}

	lib3::AggrMarketBook *getBook() {
		return mb;
	}

	LongSymbolCIndex *getSymbolIndex() {
		return &ci;
	}

	const char *getSymbol(int cid) {
		return ci[cid];
	}

	MasterDataSource(MasterDataSourceConfig &config);

	virtual ~MasterDataSource() {
		if (tick != NULL) {
			delete tick;
		}

		if (quote != NULL) {
			delete quote;
		}

		if (imb != NULL) {
			delete imb;
		}
	}

	// MarketBookListener interface
	virtual void onBookChange(int book_id, lib3::BookOrder *bo,
			lib3::QuoteReason reason, int shares_delta, bool done);

	// TickHandlerListener interace
	virtual void onTick(int cid, u_int32_t size, double px, MarketMaker mm,
			lib3::TickHandlerSource ths, lib3::TickType type,
			bool is_bookupdate, lib3::CustomPluginBase *extra);

	// OrderManagerListener interface
	virtual void onSequence(lib3::Order *order) {
	}
	virtual void onConfirm(lib3::Order *order) {
	}
	virtual void onFill(lib3::Order *order, lib3::FillDetails *fd) {
	}
	virtual void onCancel(lib3::Order *order, lib3::CancelDetails *cd) {
	}
	virtual void onReject(lib3::Order *order, lib3::RejectDetails *rd) {
	}
	virtual void onCancelReject(lib3::Order *order,
			lib3::CancelRejectDetails *rd) {
	}
	virtual void onBreak(lib3::BreakDetails *bd) {
	}
	virtual void onPositionUpdate(const char *acct, int cid, int pos) {
	}
	virtual void onNoSequence(lib3::Order *order) {
	}
	virtual void onNoConfirm(lib3::Order *order) {
	}
	virtual void onNoCancel(lib3::Order *order) {
	}
	virtual void onGlobalMismatch(const char *acct, int cid, int newpos,
			int oldpos) {
	}

	// ReadyListener interface
	virtual void onReady(int id) {
	}

	// EventListener interface
	//int OnEvent(Event *e);
	virtual void onTimer(int timer_id) {
	}

	// UserMessage interface
	virtual void onUserMessage(const int code1, const int code2,
			const char* msg1, const char* msg2) {
	}

	int OnEvent(Event* e);

	bool nextEvent();

protected:
	int processImbalance(Event *e);

};

#endif /* MASTERDATASOURCE2_HPP_ */
