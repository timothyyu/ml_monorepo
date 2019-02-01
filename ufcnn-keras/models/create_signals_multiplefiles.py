from __future__ import absolute_import
from __future__ import print_function

import sys
import glob
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

    path = "./training_data_large/"
    file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))

    if len(file_list) == 0:
        print ("No ./training_data_large/product_data_*txt  files exist in the directory. Please copy them in the ./training_data_large/ . Aborting.")
        sys.exit()

    for j in range(len(file_list)):
        filename = file_list[j]
        print('Training: ',filename)

        min_trade_amount = 1

        #if len(sys.argv) < 2 :
         #   print ("Usage: day_trading_file, NOT target_price-file ")
         #   sys.exit()


        #day_file = sys.argv[1]
        day_file = filename

        if "_2013" in day_file:
            month = day_file.split("_")[4].split(".")[0]
            write_file = path + "signal_" + month + ".csv"
        else:
            write_file = path + "signal.csv"

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
        positive_signal = 0
        negative_signal = 0
        zero_signal = 0

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
           # Count the signals in a single signal file and review the bias
           if row.signal == 1:
               positive_signal += 1
           if row.signal == -1:
               negative_signal += 1
           if row.signal == 0:
               zero_signal += 1

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
        print(' ')
        print("=====================================================")
        print(' ')
        print("Positive Signals ( 1 )   : ", positive_signal)
        print("Zero Signals     ( 0 )   : ", zero_signal)
        print("Negative Signals (-1 )   : ", negative_signal)
        print(' ')
        print("=====================================================")
        # Use the following grep commands in the directory containing the signal files to count
        # the total positive, zero & negative signals in all the signal files ---suggested by stefan
        # grep ",1.0" signal*.csv | wc -l
        # grep ",0.0" signal*.csv | wc -l
        # grep ",-1.0" signal*.csv | wc -l

__main__();
