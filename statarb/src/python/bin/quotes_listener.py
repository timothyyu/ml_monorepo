#!/usr/bin/env python
import sys
import datetime
import os
import asyncore
import time
import csv
from optparse import OptionParser

import util
import config
import guillotine

QUOTE_TIME = datetime.timedelta(seconds=60)
[MKT_OPEN_TIME, MKT_CLOSE_TIME] = util.exchangeOpenClose()

class quotes_listener(object):

    def _init_quotes(self):
        self.reset_quotes()
        self.quotes_requested = True
        self.last_quote_request_time = datetime.datetime.utcnow()

    def __init__(self, gtc):
        util.debug("Initializing quotes_listener")
        
        #Make sure that STRAT is useq-live. This is done to protect against repetition of the following scenario.
        #gt_mon was started by crontab with useq-live, it died, restarted manually buy strat was set to useq-test,
        #so fills ended up in two different run directories
        if (os.environ["STRAT"]!="useq-live"):
            print "gt_listener should be run under STRAT useq-live. Current strat is {}. Quitting...".format(os.environ["STRAT"])
            util.error("gt_listener should be run under STRAT useq-live. Current strat is {}. Quitting...".format(os.environ["STRAT"]))
            exit(1)
        
        self.gtc = gtc
        self.last_idle_time = datetime.datetime.utcnow()
        self.start_time = datetime.datetime.utcnow()
        self._init_quotes()
        self.ticker2secid={}
        self.date=os.environ['DATE']
        
        try:
            filename = os.environ["RUN_DIR"]+"/tickers.txt"
            util.log("Loading tickers from {}".format(filename))
            file=open(filename)
            for line in file:
                if len(line)<=0: continue
                tokens=line.strip().split("|")
                ticker=tokens[0]
                secid=tokens[1]
                self.ticker2secid[ticker]=secid
            file.close()
        except Exception,e:
            util.error("Oh, no! gt_mon failed to find file {}/ticker2secid.txt. If the universe is collapsing, at least create an empty file in this location!")
            raise e
        
    def reset_quotes(self):
        util.debug("Resetting quote listener")
        self.quotes = dict()
        self.quotes_requested = False

    def request_quotes(self):
        util.debug("Making request")
        self.gtc.status()
        self.quotes_requested = True
        self.last_quote_request_time += QUOTE_TIME

    def handle_info(self, msg):
        #         util.debug("msg: %s" % msg)
        symbol = msg['symbol']
        self.quotes[symbol] = msg

    def handle_server(self, msg):
        pass

    def handle_error(self, err):
        subject = "ERROR: Guillotine Error Reported"
        msg = "ERR  %(error)s = %(reason)s (msg %(message-name)s | field %(field)s | sym %(symbol)s" % err
        util.email(subject, msg)

    def handle_message(self, m):
        pass

    def close(self):
        util.debug("Closing multiplex channel, and exiting")
        self.gtc.close()
        sys.exit(0)

    def idle(self):
        now = datetime.datetime.utcnow()
        if time.time() > (MKT_CLOSE_TIME/1000):
            util.debug("Exceeded market close time. Exiting.")
            self.close()
            return

        util.debug("Idling...")
        self.last_idle_time = now

        #handle quote stuff
        if not self.quotes_requested:
            if now - self.last_quote_request_time >= QUOTE_TIME:
                if MKT_CLOSE_TIME/1000 > time.time():
                    self.request_quotes()
        elif not self.gtc.busy() and not self.gtc.waiting():
            self.process_quotes()
            self.reset_quotes()

    def process_quotes(self):
        secs = sorted(self.quotes.keys())
        quote_cnt = 0
        bad_sprd = 0
        bad_mid = 0
        bad_sz = 0
        sprd_tot = 0
        sprd_bps_tot = 0
        bid_sz_tot = 0
        ask_sz_tot = 0
        error_lines = ""
        for sec in secs:
            msg = self.quotes[sec]
#             print "%s|%.4f|%.4f|%d|%d" % (sec, msg['bid'], msg['ask'], msg['bid-size'], msg['ask-size'])
            
            quote_cnt += 1
            mid = (msg['ask'] + msg['bid'])/2
            if mid <= 0 or mid > 1000:
                bad_mid += 1
                error_lines += "ERROR: bad mid: %s %.2f\n" % (sec, mid)
                continue
            
            spread = msg['ask'] - msg['bid']

            if spread <= 0:
                bad_sprd += 1
                error_lines += "ERROR: bad spread %s %.4f\n" % (sec, spread)
                continue

            sprd_bps = 10000 * (spread / mid)
            if sprd_bps > 50:
                bad_sprd += 1
                error_lines += "ERROR: bad spread %s %.2f\n" % (sec, sprd_bps)
                continue

            sprd_tot += spread
            sprd_bps_tot += sprd_bps

            if msg['bid-size'] < 0 or msg['ask-size'] < 0:
                bad_sz += 1
                error_lines += "ERROR: bad bid/ask size %s %d %d\n" % (sec, msg['bid-size'], msg['ask-size'])
                continue

            bid_sz_tot += msg['bid-size']
            ask_sz_tot += msg['ask-size']

        email_msg = ""
        email_subj = ""
        if quote_cnt < 1000 or (bad_mid + bad_sprd + bad_sz) > (0.05*quote_cnt):
            email_subj = "ERROR: "

        email_subj += "Quote Monitor: %d quotes" % quote_cnt

        email_msg += "BAD mid/spread/size: %d/%d/%d\n" % (bad_mid, bad_sprd, bad_sz)
        if (quote_cnt-bad_sprd-bad_mid > 0):
          email_msg += "AVG SPREAD: %.4f/%.2f (bps)\n" % ((sprd_tot/(quote_cnt-bad_sprd-bad_mid)), (sprd_bps_tot/(quote_cnt-bad_sprd-bad_mid)))
        if quote_cnt > 0:
          email_msg += "AVG bidsz/asksz: %d/%d\n" % ((bid_sz_tot/quote_cnt), (ask_sz_tot/quote_cnt))
        email_msg += "\n"
        email_msg += error_lines

        util.email(email_subj, email_msg)

if __name__ == '__main__':
    util.check_running()
    util.check_include()
    
    parser = OptionParser()
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug")
    (options, args) = parser.parse_args()

    if options.debug:
        util.set_debug()
    else:
        util.set_log_file()

    util.info('launching quotes listener')
    cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
    util.info("loading config file: %s" % cfg_file)
    trade_cfg = config.load_trade_config(cfg_file)

    gtc = guillotine.multiplex_channel()
    gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name="quotes_listener_" + os.environ['STRAT'])
    gtc.register(quotes_listener(gtc))

    timeout = 0.2 #polling frequency in seconds
    asyncore.loop(timeout, use_poll=True)
