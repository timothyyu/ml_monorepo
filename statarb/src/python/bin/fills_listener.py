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

FILL_TIME = datetime.timedelta(seconds=60)
[MKT_OPEN_TIME, MKT_CLOSE_TIME] = util.exchangeOpenClose()
FILL_WAIT_TIME = 10*60 # Number of seconds beyond market close that we should wait for fills

class fills_listener(object):

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

    def __init__(self, gtc):
        util.debug("Initializing fills_listener")
        
        #Make sure that STRAT is useq-live. This is done to protect against repetition of the following scenario.
        #gt_mon was started by crontab with useq-live, it died, restarted manually buy strat was set to useq-test,
        #so fills ended up in two different run directories
        if (os.environ["STRAT"]!="useq-live"):
            print "gt_listener should be run under STRAT useq-live. Current strat is {}. Quitting...".format(os.environ["STRAT"])
            util.error("gt_listener should be run under STRAT useq-live. Current strat is {}. Quitting...".format(os.environ["STRAT"]))
            exit(1)
        
        self.gtc = gtc
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

    def handle_info(self, msg):
        pass

    def handle_fill(self, msg):
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

    util.info('launching fills listener')
    cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
    moc_cfg_file = os.environ['CONFIG_DIR'] + '/exec.moc.conf'
    util.info("loading config file: %s" % cfg_file)
    trade_cfg = config.load_trade_config(cfg_file)
    moc_trade_cfg = config.load_trade_config(moc_cfg_file)
    

    gtc = guillotine.simple_multiplex_channel()
    gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name="fills_listener_" + os.environ['STRAT'], listenToBcast=1)
    gtc.connect(moc_trade_cfg['servers'], moc_trade_cfg['account'], moc_trade_cfg['password'], name="fills_listener_" + os.environ['STRAT'],listenToBcast=1)
    gtc.register(fills_listener(gtc))

    timeout = 0.2 #polling frequency in seconds
    asyncore.loop(timeout, use_poll=True)
