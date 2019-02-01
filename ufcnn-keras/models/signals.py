from __future__ import absolute_import
from __future__ import print_function

import sys
from copy import copy, deepcopy
import os.path

import numpy as np
#import matplotlib.pyplot as plt

import pandas as pd
pd.set_option('display.width',    1000)
pd.set_option('display.max_rows', 1000)


def find_all_signals(_df, comission=0.0, max_position_size=1, debug=False):
    """
    Function finds and returns all signals that could result in profitable deals taking into account comission.
    E.g. it will return Buy and Sell signal if ask price at Buy is lower than bid price at Sell minus the comission.
    Then it will move one step forward and consider already seen Sell signal and the next Buy for the possible
    profitable short deal.
    """
    df = deepcopy(_df)
    df['Buy'] = np.zeros(df.shape[0])
    df['Sell'] = np.zeros(df.shape[0])
    df['Buy Mod'] = np.zeros(df.shape[0])
    df['Sell Mod'] = np.zeros(df.shape[0])
    
    inflection_points = pd.DataFrame({'Buy': df["askpx_"].diff().shift(-1) > 0, 'Sell': df["bidpx_"].diff().shift(-1) < 0})
    iterator = inflection_points.iterrows()
    
    max_count = 0
    position_size = 0
    
    try:
        while True:
        #for i in range(0, 100):
                idx_open, next_idx, row_open, sig_type_open = next_signal(iterator, df)
                iterator = inflection_points.loc[next_idx:].iterrows()
                #iterator.next()  # works in python 2.x but not in python 3.x
                iterator.__next__()  # or next(iterator)  in python 3.x+
                df[sig_type_open][idx_open] = 1
    except TypeError:
        print("Iteration stopped")
    
    print("Buy candidates: {} Sell candidates: {}".format(df[df['Buy'] != 0].count()['Buy'], df[df['Sell'] != 0].count()['Sell']))
        
    candidates = df[(df['Buy'] != 0) | (df['Sell'] != 0)].iterrows()
    #idx_open, row_open = candidates.next()  # works in python 2.x but not in python 3.x
    idx_open, row_open = candidates.__next__()  # or use  next(candidates)  in python 3.x+
    for idx, row in candidates:
        if row_open['Buy'] == 1 and (df["bidpx_"][idx] > (df["askpx_"][idx_open] + comission)):
            df['Buy Mod'][idx_open] += 1
            df['Sell Mod'][idx] += 1
            
        elif row_open['Sell'] == 1 and (df["askpx_"][idx] < (df["bidpx_"][idx_open] - comission)):
                df['Sell Mod'][idx_open] += 1
                df['Buy Mod'][idx] += 1
        idx_open = idx
        row_open = row
        
    df = df.rename(columns={"Buy": "Buy Candidates", "Sell": "Sell Candidtates"})
    
    df['Buy'] = np.zeros(df.shape[0])
    df['Sell'] = np.zeros(df.shape[0])
    df['Buy'][df['Buy Mod'] != 0] = 1
    df['Sell'][df['Sell Mod'] != 0] = 1
               
    print("Buy: {} Sell: {}".format(df[df['Buy Mod'] != 0].count()['Buy Mod'], df[df['Sell Mod'] != 0].count()['Sell Mod']))    
    print("Buy: {} Sell: {}".format(df[df['Buy'] != 0].count()['Buy'], df[df['Sell'] != 0].count()['Sell']))  

    return df
                          

def next_signal(iterator, df=None, sig_type=None, outer_idx=None, outer_row=None):
    """
    Recursive function to find best signal (Buy or Sell) of the sequnce of possible candidates (inflection points).
    It compares current candidate and next candidates, if one of the next candidates of the same type is better,
    e.g. if current candidate is Buy with ask price 20 and next candidate (1) is Buy with ask price 10,
    then next candidate (2) is Buy with ask price 15, the function should return next candidate (1) with ask price 10
    when it will face first consequtive Sell candidate.
    """
    prev_idx = outer_idx
    best_idx = outer_idx
    best_row = outer_row
    for idx, row in iterator:
        # print(idx, row)
        if row['Buy'] or row['Sell']:
            inner_sig_type = 'Buy' if row['Buy'] else 'Sell'
            # print("Inner signal: ", idx, inner_sig_type)
            if sig_type:
                # print("Outer signal: ", outer_idx, sig_type)
                if inner_sig_type == sig_type:
                    # print("Compare {} bid: {} ask: {} with {} bid: {} ask: {}".
                    #      format(best_idx, df["bidpx_"][best_idx], df["askpx_"][best_idx], idx, df["bidpx_"][idx], df["askpx_"][idx]))
                    if sig_type == 'Buy' and df["askpx_"][idx] < df["askpx_"][best_idx]:
                        # print("Better {} candidate at {} with price {}".format(sig_type, idx, df["askpx_"][idx]))
                        best_idx, best_row = idx, row
                        #return idx, idx, row, sig_type
                    if sig_type == 'Sell' and df["bidpx_"][idx] > df["bidpx_"][best_idx]:
                        # print("Better {} candidate at {} with price {}".format(sig_type, idx, df["bidpx_"][idx]))
                        best_idx, best_row = idx, row
                        #return idx, idx, row, sig_type
                    prev_idx = idx
                else:
                    # print("Best {} candidate at {}, break...".format(sig_type, outer_idx))
                    return best_idx, prev_idx, best_row, sig_type
            else:
                # print("Recursion")
                return next_signal(iterator, df, inner_sig_type, idx, row)

        
        
def set_positions(_df):
    df = deepcopy(_df)
    df['Pos'] = np.zeros(df.shape[0])
    
    last_position = 0
    longs = 0
    shorts = 0
    
    iterator = df.iterrows()
    last_idx, last_row = iterator.next()
    for idx, row in iterator:
        df.loc[idx]['Pos'] = row['Buy Mod'] - row ['Sell Mod'] + last_row['Pos']
        last_idx, last_row = idx, row
        if df.loc[idx]['Pos'] != last_position and df.loc[idx]['Pos'] > 0:
            longs += 1
        elif df.loc[idx]['Pos'] != last_position and df.loc[idx]['Pos'] < 0:
            shorts += 1
        last_position = df.loc[idx]['Pos']
        
    print("Long positions: {} Short positions: {}".format(longs, shorts))
    
    return df
            

def find_signals(df, sig_type, comission=0.0, debug=False):
    colnames = {"Buy": ("Buy", "Sell Close"),
                "Sell": ("Sell", "Buy Close")}
    inflection_points_buy = df["askpx_"].diff().shift(-1) > 0
    inflection_points_sell = df["bidpx_"].diff().shift(-1) < 0
    
    iterator = inflection_points_buy.iteritems() if sig_type == "Buy" else inflection_points_sell.iteritems()
    inflection_points = inflection_points_buy if sig_type == "Buy" else inflection_points_sell
    inner_inflection_points = inflection_points_sell if sig_type == "Buy" else inflection_points_buy
    
    max_count = 0
    
    (major_colname, minor_colname) = colnames[sig_type]
    
    df[major_colname] = np.zeros(df.shape[0])
    df[minor_colname] = np.zeros(df.shape[0])
    
    for idx, val in iterator:
        if max_count > 10000 and debug:
            print("Max count reached, break...")
            break
        inner_iterator = inner_inflection_points.loc[idx:].iteritems()
        if df[df[minor_colname]==1].empty:
            can_open = True
        else:
            can_open = idx > df[df[minor_colname]==1].index[-1]
        max_count += 1
        if val and can_open:
            print("{} candidate at {} with price {}".format(sig_type, idx, df["askpx_"][idx]))
            for inner_idx, inner_val in inner_iterator:
                if inner_idx > idx:
                    if sig_type == "Buy":
                        if df["askpx_"][inner_idx] < df["askpx_"][idx] and inflection_points[inner_idx]:
                            print("Better {} candidate at {} with price {}, break...".format(sig_type, inner_idx, df["askpx_"][inner_idx]))
                            break
                        if df["bidpx_"][inner_idx] > (df["askpx_"][idx] + comission) and inner_val:
                            df[major_colname][idx] = 1
                            df[minor_colname][inner_idx] = 1
                            print("Buy at {} with price {}".format(idx, df["askpx_"][idx]))
                            print("Sell at {} with price {}".format(inner_idx, df["bidpx_"][inner_idx]))
                            break
                    elif sig_type == "Sell":
                        if df["bidpx_"][inner_idx] > df["bidpx_"][idx] and inflection_points[inner_idx]:
                            print("Better {} candidate at {} with price {}, break...".format(sig_type, inner_idx, df["bidpx_"][inner_idx]))
                            break
                        if df["askpx_"][inner_idx] < (df["bidpx_"][idx] - comission) and inner_val:
                            df[major_colname][idx] = 1
                            df[minor_colname][inner_idx] = 1
                            print("Sell at {} with price {}".format(idx, df["bidpx_"][idx]))
                            print("Buy at {} with price {}".format(inner_idx, df["askpx_"][inner_idx]))
                            break   
    return df


def filter_signals(df):
    buys = df["Buy"] + df["Buy Close"]
    df["Buy Mod"] = np.zeros(df.shape[0])
    df["Buy Mod"][buys == 2] = 1
    sells = df["Sell"] + df["Sell Close"]
    df["Sell Mod"] = np.zeros(df.shape[0])
    df["Sell Mod"][sells == 2] = 1
    
    iterator = df.iterrows()
    current_signal = 0
    
    for idx, row in iterator:
        current_signal = row["Buy Mod"] - row["Sell Mod"]
        
        if current_signal != 0:
            print("Signal {} at {}".format(current_signal, idx))
            inner_iterator = df.loc[idx:].iterrows()
            #inner_iterator.next()  # works in python 2.x but not in python 3.x
            inner_iterator.__next__()  # or next(inner_iterator)  in python 3.x+
            for inner_idx, inner_row in inner_iterator:
                next_signal = inner_row["Buy Mod"] - inner_row["Sell Mod"]
                if next_signal == current_signal:
                    print("Consecutive similar signal {} at {}".format(next_signal, inner_idx))
                    if current_signal == 1:
                        df_slice = df.loc[idx:inner_idx]
                        candidates = df_slice[df_slice["Sell"] == 1]
                        best_candidate = candidates["bidpx_"].idxmax()
                        print(df.loc[best_candidate])
                        df["Sell Mod"].loc[best_candidate] = 1
                        break
                    elif current_signal == -1:
                        df_slice = df.loc[idx:inner_idx]
                        candidates = df_slice[df_slice["Buy"] == 1]
                        best_candidate = candidates["askpx_"].idxmin()
                        print(df.loc[best_candidate])
                        df["Buy Mod"].loc[best_candidate] = 1
                        break
                elif next_signal != 0 and next_signal != current_signal:
                    break
                    
    df["Buy Open"] = df["Buy"]
    df["Sell Open"] = df["Sell"]
    df = df.drop(["Buy", "Sell"], axis=1)
    print(df.columns)
    df = df.rename(columns={"Buy Mod": "Buy", "Sell Mod": "Sell"})
    print(df.columns)
    # df = df.drop(["Buy Close", "Sell Close"], axis=1)
    return df


def make_spans(df, sig_type):
    span_colname = "Buys" if sig_type == "Buy" else "Sells"
    reversed_df = df[::-1]
    df[span_colname] = np.zeros(df.shape[0])
    
    for idx in df[sig_type][df[sig_type] == 1].index:
        signal_val = df.loc[idx]
        iterator = reversed_df.loc[idx:].iterrows()
        #_d = print("Outer loop:", idx, signal_val["askpx_"]) if sig_type == "Buy" else print("Outer loop:", idx, signal_val["bidpx_"])
        for i, val in iterator:
            # _d = print("Inner loop:", i, val["askpx_"]) if sig_type == "Buy" else print("Inner loop:", i, val["bidpx_"])
            if sig_type == "Buy":
                if val["askpx_"] == signal_val["askpx_"]:
                    # print("Add to buys")
                    df[span_colname][i] = 1
                else:
                    break
            elif sig_type == "Sell":
                if val["bidpx_"] == signal_val["bidpx_"]:
                    # print("Add to sells")
                    df[span_colname][i] = 1
                else:
                    break
    return df


def pnl(df, chained=False, comission=0.02):
    deals = []
    pnl = 0
    
    if not chained:
        for idx, row in df[(df['Buy Mod'] != 0) | (df['Sell Mod'] != 0)].iterrows():
            current_trade = row['Sell Mod'] * row["bidpx_"] - row['Buy Mod'] * row["askpx_"]
            pnl = pnl + current_trade - comission
            deals.append(current_trade)
            print("Running PnL: ", pnl)

        print("Check PnL: {} vs {}".format(pnl, np.sum(deals)))
        return pnl, len(deals)
    else:
        is_opened = False

        for idx, row in df.iterrows():
            if row["Buy"]:
                if is_opened:
                    deals.append(-row["askpx_"])
                deals.append(-row["askpx_"])
                is_opened = True
            elif row["Sell"]:
                if is_opened:
                    deals.append(row["bidpx_"])
                deals.append(row["bidpx_"])
                is_opened = True
        print(len(deals))
        deals.pop()
        print(len(deals))
        return np.sum(deals), len(deals)
    
    
def generate_signals_for_file(day_file, comission=0.0, write_spans=False, chained_deals=False, min_trade_amount=None):
    (path, filename) = os.path.split(day_file)
    
    path = "./training_data_large/"  # to make sure signal files are written in same directory as data files
    
    if "_2013" in filename: 
        month = filename.split("_")[2].split(".")[0]
        write_signal_file = path + "signal_" + month + ".csv"
        write_signals_file = path + "signals_" + month + ".pickle"
    else:
        write_signal_file = path + "signal.csv"
        write_signals_file = path + "signals.pickle"

    print("Processing file ",day_file)
    print("Writing to files {}, {}".format(write_signal_file, write_signals_file))

    df = pd.read_csv(day_file, sep=" ", usecols=[0,1,2,3,4,5], index_col = 0, header = None, names = ["time","mp","bidpx_","bidsz_","askpx_","asksz_",])
    
    if not chained_deals:
        df = find_all_signals(df, comission)
    else:
        df = find_signals(df, "Buy")
        df = find_signals(df, "Sell")
        df = filter_signals(df)
    
    df['signal'] = np.zeros(df.shape[0])
    
    if write_spans:
        df = make_spans(df, "Buy")    
        df = make_spans(df, "Sell")
        df['signal'][df["Buys"] == 1] = 1.0
        df['signal'][df["Sells"] == 1] = -1.0
        print("Saving spanned signals instead of point signals!")
    else:
        df['signal'][df["Buy"] == 1] = 1.0
        df['signal'][df["Sell"] == 1] = -1.0

    df['signal mod'] = df['Buy Mod'] - df['Sell Mod']
    
    _pnl, trade_count = pnl(df, chained_deals)
    print("Max. theoret. PNL    : ", _pnl) #df.sum().absret_)
    print("Max. theoret. return : ", _pnl / df["mp"].iloc[0])
    print("Max. number of trades: ", trade_count)
    print("PnL per time-step: ", _pnl / df.shape[0])
    print("Min Trading Amount   : ", min_trade_amount)
    
    # and write the signal 
    if write_spans:
        df = df[['signal', 'Buy', 'Sell', 'Buys', 'Sells', 'signal mod']]
    else:
        df = df[['signal', 'Buy', 'Sell', 'signal mod']]
    signal_df = df['signal']
    df.to_pickle(write_signals_file)
    signal_df.to_csv(write_signal_file)
    print("Results saved")
    return df
