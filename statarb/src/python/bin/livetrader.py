#!/usr/bin/env python

import asyncore
import datetime
import math
import os
import sys
import time

import util
import guillotine
import datafiles
import config
from data_sources import file_source

IDLE_TIME = datetime.timedelta(seconds=1)
MAX_NOFILL_TIME = datetime.timedelta(minutes=50)
WARN_NOFILL_SYMS = 10
NUM_WAIT_TIMES_IN_IDLE = 3 # number of times we should wait in the idle loop for guillotine
                           # to be initialized (get symbols etc). The time for which we wait
                           # is this number multiplied by the 'timeout' (specified below)
MKT_CLOSE_TIME = util.exchangeOpenClose()[1]
util.check_include()

cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
util.info("loading config file: %s" % cfg_file)
trade_cfg = config.load_trade_config(cfg_file)

tic2sec, sec2tic = datafiles.load_tickers(os.environ['RUN_DIR'] + "/tickers.txt")
util.set_log_file()

class trade_listener(object):
    def __init__(self, gtc):
        self.gtc = gtc
#        self.last_submitted = None
        self.last_submitted_time = 0
        self.fs = file_source.FileSource(os.environ['RUN_DIR'] + '/orders/')
        self.last_idle_time = datetime.datetime.utcnow()
        self.last_trade_time = datetime.datetime.utcnow()
        self.trading = {}
        self.guillotine_wait_times = 0 # we should wait for guillotine server to be initialized, when we enter the idle loop the first few times
                                          
    def _check_trading(self):
        utcnow = datetime.datetime.utcnow()
        notfilled = 0
        for sym, lastfill in self.trading.iteritems():
            if utcnow - lastfill > MAX_NOFILL_TIME:
                util.log("No fills on %s after MAX_NOFILL_TIME" % sym)
                notfilled += 1
                self.trading[sym] = self.last_trade_time

        if notfilled >= WARN_NOFILL_SYMS:
            util.log("No fills on %d syms after MAX_NOFILL_TIME" % notfilled, "WARNING")

    def handle_info(self, msg):
        if int(msg['qtyLeft']) == 0:
            if msg['symbol'] in self.trading:
                del(self.trading[msg['symbol']])
        else:
            if msg['symbol'] not in self.trading:
                self.trading[msg['symbol']] = self.last_trade_time

    def handle_fill(self, msg):
        if int(msg['qtyLeft']) == 0:
            if msg['symbol'] in self.trading:
                del(self.trading[msg['symbol']])
        else:
            self.trading[msg['symbol']] = datetime.datetime.utcnow()

    def handle_server(self, msg):
        pass

    def handle_message(self, m):
        for k, v in m.items():
            util.log("%s: %s" % (k, v))

    def close(self):
        util.debug("Closing multiplex channel, and exiting")
        self.gtc.close()
        sys.exit(0)

    def idle(self):
        if MKT_CLOSE_TIME/1000 < time.time():
            util.debug("Exceeded market close time.")
            self.close()
            return
        
        now = datetime.datetime.utcnow()
        if now - self.last_idle_time < IDLE_TIME:
            return
        self.last_idle_time = now

        #sleep the first few times to make sure that guillotine initializes
        if self.guillotine_wait_times < NUM_WAIT_TIMES_IN_IDLE:
            self.guillotine_wait_times += 1
            util.log('waiting for guillotine to initialize')
            return            

        if len(self.gtc.symmap) == 0:
            util.log('not submitting, not connected')
            return
        #self._check_trading()
        listing = self.fs.list('orders\.[0-9_]+\.txt')
        if len(listing) == 0:
            return
        listing.sort(key = lambda x: x[0], reverse=True)
        orderfilename = listing[0][0]
        orderfileStat = os.stat(os.environ['RUN_DIR'] + '/orders/' + orderfilename)
        if math.trunc(orderfileStat.st_ctime) <= self.last_submitted_time:
            return
        util.log("Submitting trades in {}".format(orderfilename))
        orderfile = open(os.environ['RUN_DIR'] + '/orders/' + orderfilename, 'r')
        reader = util.csvdict(orderfile)
        
        trades=set()
        allSymbols = filter(lambda key: self.gtc.symmap[key] != None, self.gtc.symmap.keys())
        tradeSymbols = []
        
        #gather trades
        currentSecid=None
        currentTicker=None
        buyDollars = 0
        sellDollars = 0
        try:
            for row in reader:
                #save this info for error messages
                currentSecid=None
                currentTicker=None
                
                qty=int(float(row['shares']))
                if qty == 0:
                  continue
                sec = int(row['secid'])
                currentSecid=sec
                ticker = sec2tic[sec]
                currentTicker = ticker
                if qty > 0:
                  buyDollars += qty*float(row['oprice'])
                else:
                  sellDollars += qty*float(row['oprice'])
                aggr=float(row['aggr'])
                orderID=long(row['orderid'])
                
                self.gtc.test_trade(ticker, qty, aggr, orderID)
                trades.add((sec,ticker,qty,aggr,orderID))
                tradeSymbols.append(ticker)
                
        except KeyError:
            msg='submission failed, key error '+str(currentSecid)+' '+str(currentTicker)+". If the ticker is None, the problem happened when translating the secid to ticker. Else, the ticker was not in the guilottine symbol map"
            util.log(msg)
            util.email("[ERROR] livetrader "+orderfilename, msg)
            return
        
        #now actually send the trades. not that if we have a super=unexpected error, we will mark the file as done, so as not to screw things even more
        #by resending
        report=[]
        report.append("Buy $ = {:,.2f}".format(buyDollars))
        report.append("Sell $ = {:,.2f}".format(sellDollars))
        report.append("secid|ticker|qty|aggr|orderID")
        setZeroQtySymbols = [sym for sym in allSymbols if sym not in tradeSymbols]
        setZeroQtySymbols = filter(lambda key: key in tic2sec, setZeroQtySymbols)
        try:
            for trade in trades:
                report.append("{}|{}|{}|{}|{}".format(trade[0],trade[1],trade[2],trade[3],trade[4]))
                self.gtc.trade(trade[1], trade[2], trade[3], trade[4])
            for sym in setZeroQtySymbols:
                report.append("{}|{}|{}|{}|{}".format(tic2sec[sym], sym, 0, 1.0, -1))
                self.gtc.trade(sym, 0, 1.0, -1)
        except KeyError:
            msg='Submission half-done due to a super-unexpected key error. I have not clue why we reached this point'
            util.log(msg)
            util.email("[ERROR] livetrader "+orderfilename, msg)
        else:    
            util.email("livetrader submitted successfully {} trades from file {}".format(str(len(trades)), orderfilename), "\n".join(report))
        
#        self.last_submitted = tradefilename
        self.last_submitted_time = math.trunc(orderfileStat.st_ctime)
        self.last_trade_time = datetime.datetime.utcnow()
        util.log('submitted %s' % orderfilename)

util.log('launching trade listener')
util.check_running()

gtc = guillotine.multiplex_channel()
gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name="trade_listener")

gtc.register(trade_listener(gtc))

timeout = 0.2 #seconds loop will poll
asyncore.loop(timeout, use_poll=True)
