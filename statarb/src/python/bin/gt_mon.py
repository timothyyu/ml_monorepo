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
FILL_TIME = datetime.timedelta(seconds=60)
IDLE_TIME = datetime.timedelta(seconds=1)
DIE_TIME = datetime.timedelta(hours=6.5)
[MKT_OPEN_TIME, MKT_CLOSE_TIME] = util.exchangeOpenClose()
FILL_WAIT_TIME = 10*60 # Number of seconds beyond market close that we should wait for fills

class gt_listener(object):

    def _init_fills(self):
        self.tot_buys = 0
        self.tot_sells = 0
        #reread existing fills file 
        self.seqnum = 0
        fillfile_name = os.environ['RUN_DIR'] + '/fills.' + os.environ['DATE'] + '.txt'
        self.fillsfile = open(fillfile_name, 'a', 0)
        if (self.fillsfile.tell() == 0):
            self.fillsfile.write("type|date|strat|seqnum|secid|ticker|ts_received|ts_exchange|shares|price|exchange|liquidity|orderID|tactic\n")
        else:
            self.fillsfile.close()
            self.fillsfile = open(fillfile_name, 'r')
            dialect = csv.Sniffer().sniff(self.fillsfile.read(1024))
            self.fillsfile.seek(0)
            reader = csv.DictReader(self.fillsfile, dialect=dialect)
            for row in reader:
                self.seqnum = int(row['seqnum'])
                if float(row['shares']) > 0:
                    self.tot_buys += float(row['shares']) * float(row['price'])
                else:
                    self.tot_sells += float(row['shares']) * float(row['price'])
                    
            self.fillsfile.close()
            self.fillsfile = open(fillfile_name, 'a', 0)
        self.reset_fills()

    def _init_quotes(self):
        self.reset_quotes()
        self.quotes_requested = True
        self.last_quote_request_time = datetime.datetime.utcnow()

    def __init__(self, gtc):
        util.debug("Initializing gt_listener")
        
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
        self._init_fills()
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
        
    def reset_fills(self):
        util.debug("Resetting fills listener")
        self.last_fill_dump_time = datetime.datetime.utcnow()
        self.fills_batch = ""
        self.buys = 0
        self.sells = 0

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

    def handle_fill(self, msg):
#         util.debug("MSG: %s" % msg)
        sec = msg['symbol']
        fill_size = msg['fill-size']
        fill_price = msg['fill-price']
        self.seqnum += 1
        
        secid=self.ticker2secid.get(sec,0)
        if secid==0:
            util.error("Failed to map ticker {} to a secid".format(sec))

        traded = fill_size * fill_price
        if fill_size > 0:
            self.buys += traded
            self.tot_buys += traded
        else:
            self.sells += traded
            self.tot_sells += traded

        strat=1
        line="F|{date}|{strat}|{seqnum}|{secid}|{ticker}|{ts_received}|{ts_exchange}|{shares}|{price}|{exchange}|{liquidity}|{orderID}|{tactic}\n".format(date=self.date,strat=strat,seqnum=self.seqnum,secid=secid,ticker=sec,ts_received=util.now(),ts_exchange=long(msg['time']*1000),shares=fill_size,price=msg['fill-price'],exchange=msg['exchange'],liquidity=msg['liquidity'],orderID=msg['orderID'],tactic=msg['strat'])
        #line = "%d|%s|%d|%d|%.4f|%d|%f\n" % (util.convert_date_to_millis(datetime.datetime.utcnow()), sec, self.seqnum, fill_size, msg['fill-price'], msg['index'], (msg['time']*1000))
        self.fills_batch += line
        self.fillsfile.write(line)

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
        if time.time() > (MKT_CLOSE_TIME/1000 + FILL_WAIT_TIME):
            util.debug("Exceeded market close time + wait time for fills beyond market close.")
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

        #handle fill stuff
        if now - self.last_fill_dump_time >= FILL_TIME:
            self.process_fills()

    def process_fills(self):
        subj = ""
        if self.buys + abs(self.sells) > 200000 or self.buys+abs(self.sells) < 10:
            subj = "WARNING: "
        
        subj += "Fill Monitor: %d/%d Total: %d/%d " % (self.buys, self.sells, self.tot_buys, self.tot_sells)
        util.email(subj, self.fills_batch)
        
        self.reset_fills()

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

    util.info('launching guillotine listener')
    cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
    util.info("loading config file: %s" % cfg_file)
    trade_cfg = config.load_trade_config(cfg_file)

    gtc = guillotine.multiplex_channel()
    gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name="gt_listener_" + os.environ['STRAT'])
    gtc.register(gt_listener(gtc))

    timeout = 0.2 #polling frequency in seconds
    asyncore.loop(timeout, use_poll=True)
