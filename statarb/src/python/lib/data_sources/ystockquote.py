#!/usr/bin/env python
#
#  Copyright (c) 2007, Corey Goldberg (corey@goldb.org)
#
#  license: GNU LGPL
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.

import urllib2
import csv
import re
import time
import util

"""
This is the "ystockquote" module.

This module provides a Python API for retrieving stock data from Yahoo Finance.

sample usage:
>>> from ystockquote import *
>>> print get_symbol('GOOG', filter_fields=['last_trade_price', 'pe_ratio'])
{'last_trade_price': '620.11', 'pe_ratio': '51.80'}
"""

fields = {
          '50day_mov_avg':                      'm3',
          '52week_high':                        'k',
          '52week_low':                         'j',
          '52week_range':                       'w',
          '200day_mov_avg':                     'm4',
          'annualized_gain':                    'g3',
          'ask':                                'a',
          'ask_rt':                             'b2',
#          'ask_size':                           'a5',
# ask size can have , as in 1,000
          'avg_daily_volume':                   'a2',
          'bid':                                'b',
          'bid_rt':                             'b3',
#          'bid_size':                           'b6',
# bid size can have , as in 1,000
          'book_value':                         'b4',
          'change':                             'c1',
          'change_afterhours_rt':               'c8',
          'change_and_percent_change':          'c',
          'change_from_50day_mov_avg':          'm7',
          'change_from_52week_high':            'k4',
          'change_from_52week_low':             'j5',
          'change_from_200day_mov_avg':         'm5',
          'change_percent':                     'p2',
          'change_percent_rt':                  'k2',
          'change_rt':                          'c6',
          'commission':                         'c3',
          'day_high':                           'h',
          'day_low':                            'g',
          'day_range':                          'm',
          'day_range_rt':                       'm2',
          'day_value_change':                   'w1',
          'day_value_change_rt':                'w4',
          'dividend_pay_date':                  'r1',
          'dividend_share_ratio':               'd',
          'dividend_yield':                     'y',
          'earnings_share_ratio':               'e',
# ebitda also had a comma - 20090910 kearns
#          'ebitda':                             'j4',
          'eps_est_cur_year':                   'e7',
          'eps_est_next_qtr':                   'e9',
          'eps_est_next_year':                  'e8',
          'error_flag':                         'e1',
          'ex_dividend_date':                   'q',
          'exchange':                           'x',
#          'float_shares':                       'f6',
# float shares has commas in the values, fucks the parsing
          'high_limit':                         'l2',
          'holdings_gain':                      'g4',
          'holdings_gain_percent':              'g1',
          'holdings_gain_percent_rt':           'g5',
          'holdings_gain_rt':                   'g6',
          'holdings_value':                     'v1',
          'holdings_value_rt':                  'v7',
          'info':                               'i',
          'last_trade_date':                    'd1',
          'last_trade_plustime':                'l',
          'last_trade_price':                   'l1',
          'last_trade_rt_plustime':             'k1',
#          'last_trade_size':                    'k3',
# last trade size can have ,
          'last_trade_time':                    't1',
          'low_limit':                          'l3',
          'market_cap':                         'j1',
          'market_cap_rt':                      'j3',
          'name':                               'n',
          'notes':                              'n4',
          'open':                               'o',
          'order_book_rt':                      'i5',
          'pe_ratio':                           'r',
          'pe_ratio_rt':                        'r2',
          'peg_ratio':                          'r5',
          'percent_change_from_50day_mov_avg':  'm8',
          'percent_change_from_52week_high':    'k5',
          'percent_change_from_52week_low':     'j6',
          'percent_change_from_200day_mov_avg': 'm6',
          'prev_close':                         'p',
          'price_book_ratio':                   'p6',
          'price_eps_est_cur_year_ratio':       'r6',
          'price_eps_est_next_year_ratio':      'r7',
          'price_paid':                         'p1',
          'price_sales_ratio':                  'p5',
          'shares_owned':                       's1',
          'short_ratio':                        's7',
          'symbol':                             's',
          'ticker_trend':                       't7',
          'trade_date':                         'd2',
#          'trade_links':                        't6',
# useless field
          'volume':                             'v',
          '1yr_target_price':                   't8'}

def __request(symbols, stat):
    url = 'http://finance.yahoo.com/d/quotes.csv?s=%s&f=%s' % ("+".join(symbols), stat)
    data=None
    maxAttempts=5
    attempts=0
    
    while True:
        try:
            time.sleep(2)
            util.info("Starting attempt "+str(attempts+1))
            data=urllib2.urlopen(url).read()
            return data
        except:
            attempts+=1
            if attempts==maxAttempts: raise
    #return urllib2.urlopen(url,timeout=120).read()

def get_symbols(symbols, filter_fields=None):
    """
    Get all available quote data for the given ticker symbol.

    Returns a dictionary.
    """

    if filter_fields is not None:
        selected_fields = dict()
        
        for field in filter_fields:
            selected_fields[field] = fields[field]

    else:
        selected_fields = fields

    stats = ''.join(selected_fields.values())
    result = ""
    for i in xrange(0, len(symbols), 200):
        util.info("Starting batch "+str(i))
        result += __request(symbols[i:i+200], stats)
    #print len(result)
    reader = csv.reader(result.splitlines())
    data = dict()
    symbol_idx = 0

    for line in reader:
        if len(line) != len(selected_fields):
            print line
            print selected_fields
            for a in zip(selected_fields.keys(), line):
                print a
        assert(len(line) == len(selected_fields))
        symbol = symbols[symbol_idx]
        symbol_idx += 1
        value_idx = 0
        data[symbol] = dict()
        for field in selected_fields.iterkeys():
            value = line[value_idx]
            value_idx += 1
            # Remove HTML tags
            value = re.sub("<.*?>", "", value)
            value = re.sub("&(#[0-9]{1,3}|[a-z]{3,6});", "", value)
            data[symbol][field] =  value
        if 'error_flag' in selected_fields and data[symbol]['error_flag'] != 'N/A':
            del data[symbol]

    return data

def test():
    our_fields = [
        "name",
        "symbol",
        "exchange",
        "error_flag",

        "market_cap",
        "avg_daily_volume",
        
        "ex_dividend_date",
        "dividend_pay_date",
        "dividend_share_ratio",
        "dividend_yield",
        
        "ebitda",
        "earnings_share_ratio",
        "eps_est_cur_year",
        "eps_est_next_qtr",
        "eps_est_next_year",
        "pe_ratio",
        "peg_ratio",
        "price_book_ratio",
        "price_eps_est_cur_year_ratio",
        "price_eps_est_next_year_ratio",
        "price_sales_ratio",
        "short_ratio",
    ]
    data = get_symbols(["AAPL", "DAL", "IBM", "MSFT", "GOOG"], our_fields)
    for symbol in data.iterkeys():
        print ''
        print symbol
        print ''
        for field in data[symbol].iterkeys():
            print field, data[symbol][field]
