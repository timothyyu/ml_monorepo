#!/bin/env python

import curses
import asyncore
import os
from optparse import OptionParser
from socket import gethostname

import util
import config
import guillotine

def cmp_oex(l, r):
    return cmp( \
            abs((int(l['target']) - int(l['position']))*0.5*(float(l['bid'])+float(l['ask']))), \
            abs((int(r['target']) - int(r['position']))*0.5*(float(r['bid'])+float(r['ask']))))

class watcher (object):
    def __init__(self, win, chn):
        self.chn = chn
        self.win = win
        self.buying = {}
        self.selling = {}
        self.top = 0
        self.lft = 0
        self.bot = 0
        self.rgt = 0
        self.cty = 0
        self.draw_box()
        self.changed = True

    def draw_box (self):
        self.win.border()
        self.top, self.lft = self.win.getbegyx()
        self.bot, self.rgt = self.win.getmaxyx()
        self.cty = (self.bot - self.top) / 2
        self.win.hline(self.cty, self.lft, curses.ACS_HLINE, self.rgt - self.lft)
        self.win.refresh()
    
    def draw_symbols(self):
        buying = self.buying.values()
        selling = self.selling.values()
        buying.sort(cmp_oex, reverse=True)
        selling.sort(cmp_oex, reverse=True)

        myy = self.top + 1
        #self.win.erase()
        for m in buying:
            if myy < self.cty and m['position'] != m['target']:
                m['chg'] = abs(m['target'] - m['position'])
                m['mdpx'] = (m['bid']+m['ask']) * 0.5
                msgstr = "%(chg)4d %(symbol)5s $%(mdpx)6.2f %(position)+06d/%(target)+06d $%(avg-price)06.2f #%(last-index)02d %(aggr)2.1f" % m
                self.win.addnstr(myy, self.lft+1, msgstr+(" "*(self.rgt - self.lft-2)), self.rgt - self.lft - 2)
                myy = myy + 1
        while myy < self.cty:
            self.win.addstr(myy, self.lft+1, " "*(self.rgt - self.lft - 2)) 
            myy = myy + 1
        
        myy = self.cty + 1

        for m in selling:
            if myy < self.bot-1 and m['position'] != m['target']:
                m['chg'] = abs(m['target'] - m['position'])
                m['mdpx'] = (m['bid']+m['ask']) * 0.5
                msgstr = "%(chg)4d %(symbol)5s $%(mdpx)6.2f %(position)+06d/%(target)+06d $%(avg-price)06.2f #%(last-index)02d %(aggr)2.1f" % m
                self.win.addnstr(myy, self.lft+1, msgstr, self.rgt - self.lft - 2)
                myy = myy + 1
        while myy < self.bot-1:
            self.win.addstr(myy, self.lft+1, " "*(self.rgt - self.lft - 2)) 
            myy = myy + 1
        self.win.refresh()

    def idle(self):
        if self.changed:
            self.draw_symbols()
            self.changed = False

    def handle_info(self, msg):
        self.changed = True
        #sys.stderr.write("info %s %d %d %r\n" % (msg['symbol'], msg['position'], msg['target'], self.changed))
        if msg['target'] > msg['position']: 
            self.buying[msg['symbol']] = msg
            del(self.selling[msg['symbol']])
        elif msg['target'] < msg['position']:
            self.selling[msg['symbol']] = msg
            del(self.buying[msg['symbol']])
        else:
            del(self.buying[msg['symbol']])
            del(self.selling[msg['symbol']])

    def handle_fill(self, msg):
        #sys.stderr.write("fill %s %d %r\n" % (msg['symbol'], msg['fill'], self.changed))
        self.changed = True
        if int(msg['fill-size']) > 0:
            self.buying[msg['symbol']]['position'] = msg['position']
            if msg['target'] == msg['position']:
                del(self.buying[msg['symbol']])
        if int(msg['fill-size']) < 0:
            self.selling[msg['symbol']]['position'] = msg['position']
            if msg['target'] == msg['position']:
                del(self.selling[msg['symbol']])
        self.draw_symbols()
                


def parse_hostport(s):
    h, p = s.split(':', 2)
    return (h, int(p))

def main (win):
    parser = OptionParser()
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug")
    parser.add_option('-n', '--name', dest='name', help='name of this client to give to server')
    (opt, args) = parser.parse_args()

    if opt.debug:
        util.set_debug()
    else:
        util.set_log_file()

    util.info('launching guillotine commander')
    cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
    util.info("loading config file: %s" % cfg_file)
    trade_cfg = config.load_trade_config(cfg_file)

    gtc = guillotine.multiplex_channel()
    name = "gt-watch from "+(gethostname().split('.',1))[0] if opt.name is None else "gt_watch_" + os.environ['STRAT']
    gtc.connect(trade_cfg['servers'], trade_cfg['account'], trade_cfg['password'], name=name)
    
    w = watcher(win, gtc)
    gtc.register(w)
    asyncore.loop(0.2, use_poll=True)

curses.initscr()
curses.start_color()
curses.use_default_colors()
curses.wrapper(main)
