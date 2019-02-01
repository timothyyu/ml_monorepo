#!/usr/bin/env python

import asyncore
import sys
import time
import os
from optparse import OptionParser
from socket import gethostname

import util
import config
import guillotine
import datafiles

tic2sec, sec2tic = datafiles.load_tickers(os.environ['RUN_DIR'] + "/tickers.txt")
class oneoff (object):
    def __init__(self, chn):
        self.chn = chn
        self.acted = False
        self.status = {}

    def idle(self):
        if not self.chn.busy() and not self.chn.waiting() and len(self.status) > 0:
            keys = self.status.keys()
            keys.sort()
            if all(map(lambda k: self.amidone(self.status[k]), keys)):
                self.chn.close()
                #print "Successfully acted on %d symbols." % (len(self.status), )
            elif self.acted == False:
                self.action()
                self.acted = True

    def handle_server(self, msg):
        pass

    def handle_info(self, msg):
        self.status[msg['symbol']] = msg

    def handle_error(self, msg):
        print "\n\nERROR: closing connection.  Check message and try again?\n"
        print "\tReason: " + msg['reason']
        print "\t%r" % msg
        self.chn.close()

class do_stop (oneoff):
    def __init__(self, chn, *args):
        oneoff.__init__(self, chn)
    def handle_server(self, msg):
        self.action()
        self.acted = True
    def action(self):
        self.chn.stop()
    def amidone(self, stat):
        return int(stat['qtyLeft']) == 0

class do_halt (oneoff):
    def __init__(self, chn, *args):
        oneoff.__init__(self, chn)
        self.sym = None
        if len(args[0]) > 0:
            self.sym = args[0]
    def handle_server(self, msg):
        self.action()
        self.acted = True
    def action(self):
        if self.sym is None:
            self.chn.halt()
        else:
            self.chn.halt(self.sym)
    def amidone(self, stat):
        return stat['halt'];

class do_resume (oneoff):
    def __init__(self, chn, *args):
        oneoff.__init__(self, chn)
        self.sym = None
        if len(args[0]) > 0:
            self.sym = args[0]
    def handle_server(self, msg):
        self.action()
        self.acted = True
    def action(self):
        if self.sym is None:
            self.chn.resume()
        else:
            self.chn.resume(self.sym)
    def amidone(self, stat):
        return not stat['halt'];
    
class do_status (oneoff):
    def __init__(self, chn, *args):
        oneoff.__init__(self, chn)
        self.action()
        self.printed = {}
    def handle_server(self, msg):
        self.acted = True
    def action(self):
        pass # self.chn.status()
    def amidone(self, st):
        if not self.printed.get(st['symbol'], False):
            stat = st.copy()
            stat['haltstr'] = "*HALTED*" if st['halt'] else ' trading'
            stat['bid'] = float(st['bid'])
            stat['ask'] = float(st['ask'])
            stat['aggr'] = float(st['aggr'])
            stat['position'] = int(st['position'])
            stat['qtyLeft'] = int(st['qtyLeft'])
            sec = int(st['time'])
            usec = int(1000 * (st['time'] - sec))
            stat['tmstr'] = time.strftime('%T', time.localtime(int(sec)))
            stat['usec'] = usec
            try:
                stat['locates'] = int(st['locates'])
                print "%(tmstr)s.%(usec)03d: %(symbol)5s [%(bid)7.2f x %(ask)7.2f] : %(haltstr)s pos:%(position)+6d  qtyLeft:%(qtyLeft)+6d %(aggr).1f [%(locates)d locates]" % stat
            except KeyError:
                print "%(tmstr)s.%(usec)03d: %(symbol)5s [%(bid)7.2f x %(ask)7.2f] : %(haltstr)s pos:%(position)+6d  qtyLeft:%(qtyLeft)+6d %(aggr).1f " % stat
            self.printed[stat['symbol']] = True
        return True

class do_fills (object):
    def __init__(self, chn, *args):
        self.chn = chn
    def handle_fill(self, f):
        fill = f.copy()
        fill['qtyLeft'] = int(f['qtyLeft'])
        fill['position'] = int(f['position'])
        fill['fill-size'] = int(f['fill-size'])
        fill['fill-price'] = float(f['fill-price'])
        fill['orderID'] = long(f['orderID'])
        sec = int(f['time'])
        usec = int(1000 * (f['time'] - sec))
        fill['tmstr'] = time.strftime('%T', time.localtime(int(sec)))
        fill['usec'] = usec
        print "%(tmstr)s.%(usec)03d: %(symbol)5s | qtyLeft:%(qtyLeft)+6d pos:%(position)+6d | %(fill-size)+4d @ $%(fill-price)7.2f [orderID = %(orderID)]" % fill
    def idle(self):
        pass

class do_trade (oneoff):
    def __init__(self, chn, args):
        oneoff.__init__(self, chn)
        #print "%d | %r" % (len(args), args)
        if len(args) > 1:
            self.sym = args[0]
            self.qty = int(args[1])
            self.aggr = 1.0 if len(args) <= 2 else float(args[2])
            self.orderID = -1 if len(args) <= 3 else long(args[3])
        else:
            print "Trade requires at least two arguments: symbol and quantity.";
            self.chn.close()

    def action(self):
        try:
            self.chn.trade(self.sym, self.qty, self.aggr, self.orderID)
        except (KeyError):
            print "Warning: Can not trade %s" % (self.sym, )
    def amidone(self, stat):
        return stat['symbol'] != self.sym or int(stat['qtyLeft']) == self.qty

class do_file (oneoff):
    def __init__(self, chn, args):
        oneoff.__init__(self, chn)
        self.trades = {}
        readme = sys.stdin if len(args) == 0 else open(args[0])
        for ln in readme.readlines():
            symln = ln.split()
            if len(symln) < 2:
                print "Ignoring trade line '%s'." % ln
            else:
                sym = symln[0]
                qty = int(symln[1])
                aggr = 1.0 if len(symln) <= 2 else float(symln[2])
                orderID = -1 if len(symln) <= 3 else long(symln[3])
                self.trades[sym] = [qty, aggr, orderID]

    def action(self):
        for sym in self.trades.keys():
            qty, aggr, orderID = self.trades[sym]
            try:
                self.chn.trade(sym, qty, aggr, orderID)
            except (KeyError):
                print "Warning: Can not trade %s" % (sym, )

    def amidone(self, stat):
        qty, aggr, orderID = self.trades.get(stat['symbol'], (None, None, None))
        return qty is None or int(stat['qtyLeft']) == qty

class do_order (oneoff):
    def __init__(self, chn, args):
        oneoff.__init__(self, chn)
        self.trades = {}
        readme = sys.stdin if len(args) == 0 else open(args[0])
        count = 0
        for ln in readme.readlines():
            count += 1
            if count == 1:
              # skip header
              continue
            symln = ln.split('|')
            if len(symln) < 11:
                print "Ignoring trade line '%s'." % ln
            else:
                secid = int(symln[2])
                sym = sec2tic[secid]
                qty = int(symln[4])
                aggr = float(symln[10])
                orderID = long(symln[1])
                self.trades[sym] = [qty, aggr, orderID]

    def action(self):
        for sym in self.trades.keys():
            qty, aggr, orderID = self.trades[sym]
            try:
                self.chn.trade(sym, qty, aggr, orderID)
            except (KeyError):
                print "Warning: Can not trade %s" % (sym, )

    def amidone(self, stat):
        qty, aggr, orderID = self.trades.get(stat['symbol'], (None, None, None))
        return qty is None or int(stat['qtyLeft']) == qty

if __name__ == '__main__':
    util.check_include()
    parser = OptionParser()
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug")
    parser.add_option('-n', '--name', dest='name', help='name of this client to give to server')
    (opt, args) = parser.parse_args()

    if opt.debug:
        util.set_debug()
    else:
        util.set_log_file()

    if (len(args) == 0):
        print "action must be exactly one of\n\tstop\n\thalt [symbol]\n\tresume [symbol]\n\tstatus\n\tfills\n\ttrade SYMBOL QUANTITY\n\tfile FILENAME\n\tmoc halt [symbol]\n\tmoc resume [symbol]\n\tmoc status\n\tmoc order FILENAME\n\tfills #(read from stdin)"
        exit(2)
    else:
        action = args[0]
        action_args = args[1:]

    util.info('launching guillotine commander')
    if action == 'moc':
      cfg_file = os.environ['CONFIG_DIR'] + '/exec.moc.conf'
    else:
      cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
    util.info("loading config file: %s" % cfg_file)
    trade_cfg = config.load_trade_config(cfg_file)

    gtc = guillotine.multiplex_channel()
    if action == 'moc':
      action = args[1]
      action_args = args[2:]
    name = "gt-cmd "+action+" from "+(gethostname().split('.',1))[0] if opt.name is None else "gt_commander_" + os.environ['STRAT']
    gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name=name)
    act = globals()['do_'+action](gtc, action_args)
    gtc.register(act)
    asyncore.loop(0.2, use_poll=True)

