#include <iostream>
#include <algorithm>
#include <cmath>
#include <utility>
#include <boost/lexical_cast.hpp>
#include <boost/numeric/conversion/cast.hpp>
#include "Bar.hpp"

Bar::Bar() {
}

Bar::Bar(const int secid, const TimeVal open_ts, const TimeVal close_ts) {
	first = open = high = low = close = -1;
	volume = trades = 0;
	this->secid = secid;
	this->open_ts = open_ts;
	this->close_ts = close_ts;
	first_book_ts.setnull();
	last_book_ts.setnull();
	lastTick = 0;
	lastBidPrice = lastAskPrice = lastAskSize = lastAskSize2 = lastBidSize = lastBidSize2 = 0;
	midHitTrades = askHitTrades = bidHitTrades = midHitDollars = askHitDollars = bidHitDollars = 0;
	effectiveMidHitTrades = effectiveAskHitTrades = effectiveBidHitTrades = effectiveMidHitDollars
			= effectiveAskHitDollars = effectiveBidHitDollars = 0;
	meanSpread = meanBidSize = meanBidSize2 = meanAskSize = meanAskSize2 = 0;
	meanEffectiveSpread = 0;
        vwap = 0;
	//allTrades = boost::shared_ptr<std::vector<float> >(new std::vector<float>());
	vwapSinceStart = volumeSinceStart = 0;
	tradesSinceStart = 0;
	openSinceStart = lowSinceStart = highSinceStart = closeSinceStart = 0;
}

Bar::Bar(const int secid, const char *ticker, const TimeVal open_ts, const TimeVal close_ts) {
	first = open = high = low = close = -1;
	volume = trades = 0;
	this->secid = secid;
	this->ticker = ticker;
	this->open_ts = open_ts;
	this->close_ts = close_ts;
	first_book_ts.setnull();
	last_book_ts.setnull();
	lastTick = 0;
	lastBidPrice = lastAskPrice = lastAskSize = lastAskSize2 = lastBidSize = lastBidSize2 = 0;
	midHitTrades = askHitTrades = bidHitTrades = midHitDollars = askHitDollars = bidHitDollars = 0;
	effectiveMidHitTrades = effectiveAskHitTrades = effectiveBidHitTrades = effectiveMidHitDollars
			= effectiveAskHitDollars = effectiveBidHitDollars = 0;
	meanSpread = meanBidSize = meanBidSize2 = meanAskSize = meanAskSize2 = 0;
	meanEffectiveSpread = 0;
	vwap = 0;
	//allTrades = boost::shared_ptr<std::vector<float> >(new std::vector<float>());
	vwapSinceStart = volumeSinceStart = 0;
	tradesSinceStart = 0;
	openSinceStart = lowSinceStart = highSinceStart = closeSinceStart = 0;
}

//Update the bar with a new trade
void Bar::update(const int size, const double price) {
	//create dummy tick
	Tick tick(0, size, price, MM_ANY, lib3::THS_DEFAULT, lib3::TT_NORMAL, false);
	update(tick, NULL, TimeVal());
/*	//first bar, like, ever.
	if (open < 0) {
		first = open = close = high = low = price;
		volume = size;
		trades = 1;
		return;
	}

	//we assume that open is inherited from previous bar, so it is already set
	if (first < 0) {
		first = price;
	}
	close = price;
	high = std::max(high, price);
	low = std::min(low, price);
	volume += size;
	trades++;*/
}

void Bar::update(Quote quote, lib3::AggrMarketBook *book, TimeVal ts) {
	//If it is an exec, handle it first as a tick
	if (quote.reason == lib3::EXEC) {
		Tick tick = Tick(quote.bo->cid, quote.bo->fsize, quote.bo->fpx, quote.bo->mm, lib3::THS_DEFAULT,
				lib3::TT_NORMAL, true);
		update(tick, book, ts);
	}

	digest(ts);

	double bid;
	size_t bidSize;
	size_t bidSize2;
	size_t bidOrders;
	book->get_nth_mkt(BUY, quote.bo->cid, 1, &bid, &bidSize2, &bidOrders);
	//now bid is right
	book->get_nth_mkt(BUY, quote.bo->cid, 0, &bid, &bidSize, &bidOrders);
	bidSize2 += bidSize;

	double ask;
	size_t askSize;
	size_t askSize2;
	size_t askOrders;
	book->get_nth_mkt(SELL, quote.bo->cid, 1, &ask, &askSize2, &askOrders);
	//now ask is right
	book->get_nth_mkt(SELL, quote.bo->cid, 0, &ask, &askSize, &askOrders);
	askSize2 += askSize;

        if (isnan(bid) || isnan(ask) || !(bid > 0) || !(ask > 0) || fabs(ask - bid) > 20){
		//DateTime dts(ts);
		//std::cerr<<"Bad quote! " << ticker << " " << dts.getfulltime() << " "<< bid << " " <<ask<<std::endl;
		return;
	}

	if (first_book_ts == 0) {
		first_book_ts = ts;
	}

	last_book_ts = ts;

	lastBidPrice = bid;
	lastAskPrice = ask;
	lastBidSize = bidSize;
	lastBidSize2 = bidSize2;
	lastAskSize = askSize;
	lastAskSize2 = askSize2;
}

//assumes that the tick is valid
void Bar::update(Tick tick, lib3::AggrMarketBook *book, TimeVal ts) {
	//first bar, like, ever.
	if (open < 0) {
		first = open = close = high = low = tick.price;
		volume = tick.size;
		trades = 1;
		meanEffectiveSpread = effectiveSpread(tick.price, lastAskPrice, lastBidPrice);
		vwap = tick.price;
		lastTick = tick.price;
	} else {
		//we assume that open is inherited from previous bar, so it is already set
		if (first < 0) {
			first = tick.price;
		}
		close = tick.price;
		high = std::max(high, tick.price);
		low = std::min(low, tick.price);
		volume += tick.size;
		trades++;
		meanEffectiveSpread += 1.0 / trades * (effectiveSpread(tick.price, lastAskPrice, lastBidPrice)
				- meanEffectiveSpread);
		vwap += 1.0 *  tick.size / volume * (tick.price - vwap);
		lastTick = tick.price;
	}
	
	allTrades.push_back((float) tick.price);
	volumeSinceStart += tick.size;
	tradesSinceStart++;
	vwapSinceStart += 1.0 * tick.size / volumeSinceStart * (tick.price - vwapSinceStart);
	if (openSinceStart != 0) {
		closeSinceStart = tick.price;
		highSinceStart = std::max(highSinceStart, tick.price);
		lowSinceStart = std::min(lowSinceStart, tick.price);
	} else {
		openSinceStart = closeSinceStart = highSinceStart = lowSinceStart = tick.price;
	}

	//tick before book?
	if (first_book_ts == 0)
		return;

	double notional = tick.price * tick.size;

	if (!(lastAskPrice > lastBidPrice)) {
		midHitTrades++;
		midHitDollars += notional;
	} else if (tick.price >= lastAskPrice - 1e-4) {
		askHitTrades++;
		askHitDollars += notional;
	} else if (tick.price <= lastBidPrice + 1e-4) {
		bidHitTrades++;
		bidHitDollars += notional;
	} else {
		midHitTrades++;
		midHitDollars += notional;
	}

	double mid = (lastBidPrice + lastAskPrice) / 2;
	if (!(lastAskPrice > lastBidPrice)) {
		effectiveMidHitTrades++;
		effectiveMidHitDollars += notional;
	} else if (tick.price > mid + 1e-4) {
		effectiveAskHitTrades++;
		effectiveAskHitDollars += notional;
	} else if (tick.price < mid - 1e-4) {
		effectiveBidHitTrades++;
		effectiveBidHitDollars += notional;
	} else {
		effectiveMidHitTrades++;
		effectiveMidHitDollars += notional;
	}
}

//"rollover bar", i.e., create a new bar "in-place" following a previous one. this way the new bar inherits the close price of the previous bar
void Bar::rollover(const TimeVal new_close_ts) {
	open = high = low = close;
	volume = 0;
	trades = 0;
	first = -1;
	open_ts = close_ts;
	close_ts = new_close_ts;
	vwap = vwap;
	lastTick = lastTick;

	if (first_book_ts > 0) {
		first_book_ts = open_ts;
		last_book_ts = open_ts;

		//useless but included for clarity
		lastBidPrice = lastBidPrice;
		lastAskPrice = lastAskPrice;
		lastBidSize = lastBidSize;
		lastBidSize2 = lastBidSize2;
		lastAskSize = lastAskSize;
		lastAskSize2 = lastAskSize2;

		//Actually these values shouldn't matter, even if there are no book updates within a bar. Digest takes care of this. Here for clarity
		meanSpread = lastAskPrice - lastBidPrice;
		meanEffectiveSpread = lastAskPrice - lastBidPrice;
		meanBidSize = lastBidSize;
		meanBidSize2  = lastBidSize2;
		meanAskSize = lastAskSize;
		meanAskSize2 = lastAskSize2;

		//these counters need indeed to be reset
		midHitTrades = askHitTrades = bidHitTrades = midHitDollars = askHitDollars = bidHitDollars = 0;
		effectiveMidHitTrades = effectiveAskHitTrades = effectiveBidHitTrades = effectiveMidHitDollars
				= effectiveAskHitDollars = effectiveBidHitDollars = 0;
	}
}

void Bar::digest(TimeVal ts) {
	if (first_book_ts.sec() == 0)
		return;

	double wn = 1.0 * (1e6 * (ts.sec() - last_book_ts.sec()) + ts.usec() - last_book_ts.usec());
	double wtotal = 1.0 * (1e6 * (ts.sec() - first_book_ts.sec()) + ts.usec() - first_book_ts.usec());

	//nothing to digest if ts == first_book_ts
	if (ts == first_book_ts) {
		return;
	}

	//first book update of the bar
	if (last_book_ts == open_ts) {
		assert(last_book_ts == first_book_ts);
		meanSpread = (lastAskPrice - lastBidPrice);
		meanAskSize = lastAskSize; 
		meanAskSize2 = lastAskSize2; 
		meanBidSize = lastBidSize; 
		meanBidSize2 = lastBidSize2;
	}
	else {
		assert(wn / wtotal <= 1.0);
		meanSpread += wn / wtotal * (lastAskPrice - lastBidPrice - meanSpread);
		meanAskSize += wn / wtotal * (lastAskSize - meanAskSize);
		meanAskSize2 += wn / wtotal * (lastAskSize2 - meanAskSize2);
		meanBidSize += wn / wtotal * (lastBidSize - meanBidSize);
		meanBidSize2 += wn / wtotal * (lastBidSize2 - meanBidSize2);
	}

}

void Bar::digest() {
	digest(close_ts);
}

std::string Bar::output_v1() {
	std::stringstream oss;
	long ots = long_open_ts();
	long cts = long_close_ts();
	oss << secid << "|" << ots << "|" << cts << "|" << open << "|" << first << "|" << high << "|" << low << "|"
			<< close << "|" << volume << "|" << trades << "|" << vwap;
	return oss.str();
}

std::string Bar::output_v2() {
	std::stringstream oss;
	long ots = long_open_ts();
	long cts = long_close_ts();
	oss << secid << "|" << ots << "|" << cts << "|" << open << "|" << first << "|" << high << "|" << low << "|"
			<< close << "|" << volume << "|" << meanSpread << "|" << meanEffectiveSpread << "|" << meanBidSize << "|"
			<< meanAskSize << "|" << trades << "|" << bidHitTrades << "|" << midHitTrades << "|" << askHitTrades << "|"
			<< effectiveBidHitTrades << "|" << effectiveMidHitTrades << "|" << effectiveAskHitTrades << "|"
			<< bidHitDollars << "|" << midHitDollars << "|" << askHitDollars << "|" << effectiveBidHitDollars << "|"
			<< effectiveMidHitDollars << "|" << effectiveAskHitDollars << "|" << vwap;
	return oss.str();
}

long Bar::long_open_ts() {
	return boost::numeric_cast<long>(1000 * open_ts.sec() + open_ts.usec()/1000);
}

long Bar::long_close_ts() {
	return boost::numeric_cast<long>(1000 * close_ts.sec() + close_ts.usec()/1000);
}

std::string Bar::outputHuman() {
	std::stringstream oss;
	DateTime ots(open_ts);
	DateTime cts(close_ts);
	oss << ticker << "|" << ots.getfulltime() << "|" << cts.getfulltime() << "|" << open << "|" << first << "|" << high
			<< "|" << low << "|" << close << "|" << volume << "|" << meanSpread << "|" << meanEffectiveSpread << "|"
			<< meanBidSize << "|" << meanAskSize << "|" << trades << "|" << bidHitTrades << "|" << midHitTrades << "|"
			<< askHitTrades << "|" << effectiveBidHitTrades << "|" << effectiveMidHitTrades << "|"
			<< effectiveAskHitTrades << "|" << bidHitDollars << "|" << midHitDollars << "|" << askHitDollars << "|"
			<< effectiveBidHitDollars << "|" << effectiveMidHitDollars << "|" << effectiveAskHitDollars << "|" << vwap;
	return oss.str();
}

std::pair<double, double> Bar::EHL(double e) {
	int n = tradesSinceStart;
	if (n == 0)
		return std::make_pair(0.0, 0.0);

	int high = (int) floor(n * e);
	std::nth_element(allTrades.begin(), allTrades.begin() + high, allTrades.begin() + n);
	double ehigh = allTrades.at(high);

	int low = (int) floor(n * (1 - e));
	std::nth_element(allTrades.begin(), allTrades.begin() + low, allTrades.begin() + n);
	double elow = allTrades.at(low);

	return std::make_pair(ehigh, elow);
}

double Bar::effectiveSpread(double price, double ask, double bid) {
	if (ask <= bid)
		return 0.0;

	double mid = (ask + bid) / 2;
	double effectiveAsk;
	double effectiveBid;

	effectiveAsk = (price >= mid) ? std::min(price, ask) : ask;
	effectiveBid = (price <= mid) ? std::max(price, bid) : bid;

	return effectiveAsk - effectiveBid;
}
