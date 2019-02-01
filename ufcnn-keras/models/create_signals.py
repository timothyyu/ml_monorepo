from __future__ import absolute_import
from __future__ import print_function

import sys

import numpy as np
import matplotlib.pyplot as plt

import pandas as pd
pd.set_option('display.width',    1000)
pd.set_option('display.max_rows', 1000)

def __main__():
    """ 
    Trading Simulator from curriculumvite trading competition
    see also the arvix Paper from Roni Mittelman http://arxiv.org/pdf/1508.00317v1
    Modified by Ernst.Tmp@gmx.at
    
    produces data to train a neural net
    """
    # Trades smaller than this will be omitted
    min_trade_amount = 1

    if len(sys.argv) < 2 :
        print ("Usage: day_trading_file, NOT target_price-file ")
        sys.exit()


    day_file = sys.argv[1]


    if "_2013" in day_file: 
        month = day_file.split("_")[2].split(".")[0]
        write_file = "signal_" + month + ".csv"
    else:
        write_file = "signal.csv"

    print("Processing file ",day_file)
    print("Writing to file ",write_file)

    df = pd.read_csv(day_file, sep=" ", usecols=[0,1,2,3,4,5], index_col = 0, header = None, names = ["time","mp","bidpx_","bidsz_","askpx_","asksz_",])
    #df = pd.read_csv(day_file, sep=" ",  header = None, names = ["time","mp","bidpx_","bidsz_","askpx_","asksz_",])


    # calculate the market price
    df['mktpx_'] = df.apply(lambda row: ( (row['bidpx_']*row['asksz_'] + row['askpx_'] * row['bidsz_']) / (row['bidsz_'] + row['asksz_'])
                                               if row['asksz_'] + row['bidsz_'] > 0
                                               else row['bidpx_']+row['askpx_'] /2.),
                           axis=1)

    # and calculate the price difference
    df['ret_'] = df.mktpx_ - df.mktpx_.shift(1)
    df['absret_'] = abs(df.ret_)
    df['shftret_'] = df.ret_.shift(-1)
    df.fillna(0., inplace=True)
    df['tradeid'] = 0

    last_signal = 0 
    trade_count = 0
    trade_sum = 0

    df['signal'] = np.sign(df.shftret_)

    notrade_list = []
    
    for index,row in df.iterrows():
       #print(row)
       if row.signal != last_signal and row.signal != 0:
           if trade_sum < min_trade_amount:
               notrade_list.append(trade_count)         
           trade_sum = 0
           trade_count += 1
           last_signal = row.signal
       if row.signal == 0:
           df.loc[index,'signal'] = last_signal 
       trade_sum += row['absret_']
       df.loc[index,'tradeid'] = trade_count

    df.loc[df['tradeid'].isin(notrade_list),'signal']=0.
    df.loc[df['tradeid'].isin(notrade_list),'absret_']=0.

    # and write the signal 
    signal_df = df['signal']
    signal_df.to_csv(write_file)

    #print ("Trades")
    #print(trades2_df)
    #print(trades3_df)
    #print ("Read DF from ", day_file)
    #print(df)
    print("Max. theoret. PNL    : ", df.sum().absret_)
    print("Max. number of trades: ", trade_count - len(notrade_list))
    print("Min Trading Amount   : ", min_trade_amount)


__main__();
