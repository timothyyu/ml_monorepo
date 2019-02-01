#include "MasterDataSource.hpp"
#include <cstdlib>
#include <boost/filesystem.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/numeric/conversion/cast.hpp>
#include <sys/types.h>
#include <unistd.h>
#include <cstring>
#include "Common/SockMessage.h"
#include "Common/ExternalNet.h"
#include "Common/ExternalPort.h"
#include "Client/lib3/datasources/arca/ArcaRawEvent.h"
#include "Client/lib3/datasources/nyseImb/NyseImbRawEvent.h"
#include "Client/lib3/datasources/nasdaq/Itch4RawEvent.h"
#include "Client/lib3/datasources/nasdaq/Itch41RawEvent.h"
#include "Client/lib3/datasources/nyseImb/NyseImbRawLiveSource.h"
#include "Client/lib3/datasources/nasdaq/NasdaqRawSource.h"
#include "Client/lib3/datasources/nasdaq/Nasdaq41RawSource.h"

///////////////// MASTER_DATA_SOURCE_CONFIG ///////////////
MasterDataSourceConfig::MasterDataSourceConfig(int day, CIndex &ci, int debug, Task task, bool withImbalance) : //(bool live,int fromDate,std::vector<std::string> tickers) :
		lib3::TraderConfig() {
	this->task = task;
	this->withImbalance = withImbalance;

	this->unset_all();
	this->unset_quote_source_all();
	this->unset_tick_source_all();
	this->unset_trader_all();

	this->gen_debug_level = "TAEL_ALL";
	this->om_debug_level = "TAEL_ALL";
	this->data_debug_level = "TAEL_ALL";
	//this->book_debug_level = "TAEL_ALL";
	this->sim_action_debug_level = "TAEL_ALL";
	this->sim_exec_debug_level = "TAEL_ALL";

	if (debug > 0) {
		this->gen_log_type = "STDOUT";
		this->om_log_type = "STDOUT";
		this->data_log_type = "STDOUT";
		//this->book_log_type = "STDOUT";
		this->sim_action_log_type = "STDOUT";
		this->sim_exec_log_type = "STDOUT";
	} else {
		//create logging subdir
		boost::filesystem::path filepath = getenv("LOG_DIR");
		filepath /= "bars." + boost::lexical_cast<std::string>(getpid());
		boost::filesystem::create_directories(filepath);
		this->output_dir = filepath.native();

		this->gen_log_type = "FD_LOGGER";
		this->om_log_type = "FD_LOGGER";
		//this->data_log_type = "FD_LOGGER";
		this->data_log_type = "NONE";
		//this->book_log_type = "FD_LOGGER";
		this->sim_action_log_type = "FD_LOGGER";
		this->sim_exec_log_type = "FD_LOGGER";
	}

	this->set(lib3::TCFlags::SEQNUM_CACHE);
	this->seqnum = 1;

	if (task == ASE_V1 || task == ASE_V2) {
		this->set(lib3::TCFlags::TICKS);
	}

	if (task == ASE_V2) {
		this->set(lib3::TCFlags::QUOTES);
		this->set(lib3::TCFlags::BOOK);
		this->aggr_book = true;
		this->auto_correct_aggr = true;
	}

	if (day > 0) {
		this->live = false;
		this->date = day;
		this->set(lib3::TCFlags::HISTORICAL);
	} else {
		this->live = true;
	}

	if (task == ASE_V1 || task == ASE_V2) {
		this->tick_sources[lib3::TraderStumpEnums::NASDAQ_L1_TICK_SOURCE] = 1;
		this->tick_sources[lib3::TraderStumpEnums::NYSE_L1_TICK_SOURCE] = 1;
		this->tick_sources[lib3::TraderStumpEnums::ARCA_L1_TICK_SOURCE] = 1;
		this->tick_sources[lib3::TraderStumpEnums::BATS_L1_TICK_SOURCE] = 1;
		this->tick_sources[lib3::TraderStumpEnums::BOSTON_L1_TICK_SOURCE] = 1;

		if (live || day >= 20100707) {
			this->tick_sources[lib3::TraderStumpEnums::EDGANG_L1_TICK_SOURCE] = 1;
			this->tick_sources[lib3::TraderStumpEnums::EDGXNG_L1_TICK_SOURCE] = 1;
		}

		if (live || day >= 20101008) {
			this->tick_sources[lib3::TraderStumpEnums::PSX_L1_TICK_SOURCE] = 1;
		}

		if (live || day >= 20101014) {
			this->tick_sources[lib3::TraderStumpEnums::BYX_L1_TICK_SOURCE] = 1;
		}
	}

	if (task == ASE_V2) {
		this->quote_sources[lib3::TraderStumpEnums::NASDAQ_L1_ALL_QUOTE_SOURCE] = 1;
		this->quote_sources[lib3::TraderStumpEnums::NYSE_L1_ALL_QUOTE_SOURCE] = 1;
		this->quote_sources[lib3::TraderStumpEnums::ARCA_L1_ALL_QUOTE_SOURCE] = 1;
		this->quote_sources[lib3::TraderStumpEnums::BATS_L1_ALL_QUOTE_SOURCE] = 1;
		this->quote_sources[lib3::TraderStumpEnums::BOSTON_L1_ALL_QUOTE_SOURCE] = 1;

		if (live || day >= 20100707) {
			this->quote_sources[lib3::TraderStumpEnums::EDGANG_L1_ALL_QUOTE_SOURCE] = 1;
			this->quote_sources[lib3::TraderStumpEnums::EDGXNG_L1_ALL_QUOTE_SOURCE] = 1;
		}

		if (live || day >= 20101008) {
			this->quote_sources[lib3::TraderStumpEnums::PSX_L1_ALL_QUOTE_SOURCE] = 1;
		}

		if (live || day >= 20101014) {
			this->quote_sources[lib3::TraderStumpEnums::BYX_L1_ALL_QUOTE_SOURCE] = 1;
		}
	}
	this->filter_symbols = 1;
	for (unsigned int i = 0; i < ci.size(); i++) {
		this->symbols.push_back(ci[i]);
	}
}

int MasterDataSourceConfig::getDebugLevel() {
	return debug;
}

///////////////// MASTER_DATA_SOURCE ///////////////

MasterDataSource::MasterDataSource(MasterDataSourceConfig &config) :
		lib3::TraderStump(config), tick(NULL), event(NULL), quote(NULL), imb(NULL), errorOnDuplicates(false) {

	//XXXXXXXXXXXXXXXXXXXXXXXXXX
	//Imbalance data sources. This part is ripped from TraderStump, keep it updated!
	if (config.withImbalance) {
		if (config.live) {
			add_raw_live_source<lib3::NyseImbRawLiveSource>(NYSEIMB_RAW_PORT_AZ, McastNyseImbRawAZ);
			add_source_live_nasdaq41_raw(false);
		}
		else if (config.date>=20110101) {
			add_historical_raw_source<lib3::Nasdaq41RawSource>("/apps/nasdaq41-raw", 0);
			add_historical_raw_source<lib3::NyseImbRawLiveSource>("/apps/nyseimb-raw", 0);
		}
		else {
			add_historical_raw_source<lib3::NyseImbRawLiveSource>("/apps/nyseimb-raw", 0);
			add_historical_raw_source<lib3::NasdaqRawSource>("/apps/nasdaq-raw", 0);
		}

		//Manually listen to the appropriate messages
		ecb->addListener(NASDAQ_RAW_IMBALANCE, this);
		ecb->addListener(NASDAQ41_RAW_IMBALANCE, this);
		ecb->addListener(AMEXIMB_RAW_OPEN, this);
		ecb->addListener(NYSEIMB_RAW_OPEN, this);
		ecb->addListener(AMEXIMB_RAW_CLOSE, this);
		ecb->addListener(NYSEIMB_RAW_CLOSE, this);
		ecb->addListener(AMEXIMB_RAW_NO, this);
		ecb->addListener(NYSEIMB_RAW_NO, this);
	}

	if (config.getDebugLevel() >= 3) {
		for (int i = 0; i <= MAX_MSGTYPE; i++) {
			//these listeners are already added by the TraderStump constructor
			if (i == TIME_MESSAGE || i == TRADER_STUMP_COMMAND || i == USER_MESSAGE)
				continue;
			ecb->addListener(i, this);
		}
	}
}

void MasterDataSource::onTick(int cid, u_int32_t size, double px, MarketMaker mm, lib3::TickHandlerSource ths, lib3::TickType type, bool is_bookupdate,
		lib3::CustomPluginBase *extra) {
	if (errorOnDuplicates && this->tick != NULL) {
		std::cerr << "New tick while old one is still there. Aborting..." << std::endl;
		exit(1);
	} else if (this->tick != NULL) {
		//std::cerr << "New tick while old one is still there..." << std::endl;
		delete this->tick;
	}
	this->tick = new Tick(cid, size, px, mm, ths, type, is_bookupdate);
}

// MarketBookListener interface
void MasterDataSource::onBookChange(int book_id, lib3::BookOrder *bo, lib3::QuoteReason reason, int shares_delta, bool done) {
	if (errorOnDuplicates && this->quote != NULL) {
		std::cerr << "New quote while old one is still there. Aborting..." << std::endl;
		exit(1);
	} else if (this->quote != NULL) {
		//std::cerr << "New quote while old one is still there..." << std::endl;
		delete this->quote;
	}

	this->quote = new Quote(book_id, bo, reason, shares_delta, done);
}

bool MasterDataSource::nextEvent() {
	return this->ecb->processNextEvent();
}

int MasterDataSource::OnEvent(Event* e) {
	this->event = e;
	processImbalance(e);
	TraderStump::OnEvent(e);
	return 0;
}

//a bit redundant for efficiency
int MasterDataSource::processImbalance(Event *e) {

	switch (e->msgtype) {
	case NASDAQ41_RAW_IMBALANCE: {
		lib3::Itch41RawEvent *iimb = static_cast<lib3::Itch41RawEvent *>(e);
		if (iimb->imb->crossType != 'C' || iimb->imb->refPrice == 0)
			break;

		if (errorOnDuplicates && this->imb != NULL) {
			std::cerr << "New imbalance while old one is still there. Aborting..." << std::endl;
			exit(1);
		} else if (this->imb != NULL) {
			//std::cerr << "New tick while old one is still there..." << std::endl;
			delete this->imb;
		}

		int imbQty = 0;
		switch(iimb->imb->imbDir) {
		case 'B':
			imbQty = iimb->imb->imbQty;
			break;
		case 'S':
			imbQty = -iimb->imb->imbQty;
			break;
		case 'N':
			imbQty = 0;
			break;
		case 'O':
			imbQty = 0;
			break;
		default:
			std::cerr<<"Unexpected imbalance dir code"<<std::endl;
			break;
		}

		this->imb = new Imbalance(ci[iimb->Symbol()], iimb->imb->pairQty, imbQty, iimb->imb->refPrice/lib3::Itch41PxDiv, iimb->imb->nearPrice/lib3::Itch41PxDiv, iimb->imb->farPrice/lib3::Itch41PxDiv, 'I');
		break;
	}
	case NASDAQ_RAW_IMBALANCE: {
		lib3::Itch4RawEvent *iimb = static_cast<lib3::Itch4RawEvent *>(e);
		if (iimb->imb->crossType != 'C' || iimb->imb->refPrice == 0)
			break;

		if (errorOnDuplicates && this->imb != NULL) {
			std::cerr << "New imbalance while old one is still there. Aborting..." << std::endl;
			exit(1);
		} else if (this->imb != NULL) {
			//std::cerr << "New tick while old one is still there..." << std::endl;
			delete this->imb;
		}

		int imbQty = 0;
		switch(iimb->imb->imbDir) {
		case 'B':
			imbQty = iimb->imb->imbQty;
			break;
		case 'S':
			imbQty = -iimb->imb->imbQty;
			break;
		case 'N':
			imbQty = 0;
			break;
		case 'O':
			imbQty = 0;
			break;
		default:
			std::cerr<<"Unexpected imbalance dir code"<<std::endl;
			break;
		}

		this->imb = new Imbalance(ci[iimb->Symbol()], iimb->imb->pairQty, imbQty, iimb->imb->refPrice/lib3::Itch4PxDiv, iimb->imb->nearPrice/lib3::Itch4PxDiv, iimb->imb->farPrice/lib3::Itch4PxDiv, 'I');
		break;
	}

	case AMEXIMB_RAW_CLOSE:
	case NYSEIMB_RAW_CLOSE: {
		lib3::NyseImbRawEvent *nimb = static_cast<lib3::NyseImbRawEvent *>(e);
		if (nimb->Px()<=0.0)
			break;

		if (errorOnDuplicates && this->imb != NULL) {
			std::cerr << "New imbalance while old one is still there. Aborting..." << std::endl;
			exit(1);
		} else if (this->imb != NULL) {
			//std::cerr << "New tick while old one is still there..." << std::endl;
			delete this->imb;
		}

		int imbQty = 0;
		switch(nimb->Type()) {
		case 'B':
			imbQty = nimb->ImbQty();
			break;
		case 'S':
			imbQty = -nimb->ImbQty();
			break;
		default:
			imbQty = 0;
			break;
		}

		this->imb = new Imbalance(ci[nimb->Symbol()], nimb->PairedQty(), imbQty, nimb->Px(), nimb->NearPx(), nimb->FarPx(), 'N');
		break;
	}
	default:
		break;
	}

	return 0;
}
