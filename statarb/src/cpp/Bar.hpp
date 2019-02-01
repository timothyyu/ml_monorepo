#ifndef BAR_HPP_
#define BAR_HPP_

#include <algorithm>
#include <iostream>
#include <vector>
#include <boost/accumulators/accumulators.hpp>
#include <boost/accumulators/statistics/stats.hpp>
#include <boost/accumulators/statistics/pot_quantile.hpp>
#include <boost/shared_ptr.hpp>
#include "c_util/Time.h"
#include "MasterDataSource.hpp"

using namespace trc::compat::util;
using namespace boost::accumulators;

class Bar {
public:
	double first;
	double open;
	double high;
	double low;
	double close;
	double volume;
	int trades;
	int secid;
	std::string ticker;
	TimeVal open_ts;
	TimeVal close_ts;

	//
	TimeVal first_book_ts;
	TimeVal last_book_ts;
	double lastTick;
	double lastBidPrice;
	double lastAskPrice;
	double lastBidSize;
	double lastBidSize2;
	double lastAskSize;
	double lastAskSize2;

	double midHitTrades;
	double askHitTrades;
	double bidHitTrades;
	double midHitDollars;
	double askHitDollars;
	double bidHitDollars;

	double effectiveMidHitTrades;
	double effectiveAskHitTrades;
	double effectiveBidHitTrades;
	double effectiveMidHitDollars;
	double effectiveAskHitDollars;
	double effectiveBidHitDollars;

	int bookChanges;

	double meanSpread;
	double meanBidSize;
	double meanBidSize2;
	double meanAskSize;
	double meanAskSize2;
	double meanEffectiveSpread;
	double vwap;

	//do quantiles based on all trades for now
	//std::vector<float> allTrades;
	vector<float> allTrades;
	int tradesSinceStart;
	double volumeSinceStart;
	double vwapSinceStart;
	double openSinceStart;
	double closeSinceStart;
	double highSinceStart;
	double lowSinceStart;

	Bar();
	Bar(const int secid, const TimeVal open_ts, const TimeVal close_ts);
	Bar(const int secid, const char *ticker, const TimeVal open_ts, const TimeVal close_ts);
	void update(const int size, const double price);
	void update(Quote quote, lib3::AggrMarketBook *book, TimeVal ts);
	void update(Tick tick, lib3::AggrMarketBook *book, TimeVal ts);
	void digest(TimeVal ts);
	void digest();
	void rollover(const TimeVal new_close_ts);
	std::string output_v1();
	std::string output_v2();
	std::string outputHuman();
	std::pair<double,double> EHL(double e);
	long long_open_ts();
	long long_close_ts();

protected:
	double effectiveSpread(double price,double ask,double bid);
};

#endif /* BAR_HPP_ */
