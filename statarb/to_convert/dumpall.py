#!/usr/bin/env python 

from calc import *
from loaddata import *
from util import *

parser = argparse.ArgumentParser(description='G')
parser.add_argument("--start",action="store",dest="start",default=None)
parser.add_argument("--end",action="store",dest="end",default=None)
args = parser.parse_args()

start = dateparser.parse(args.start)
end = dateparser.parse(args.end)
lookback = 30
horizon = 5 

uni_df = get_uni(start, end, lookback)    
barra_df = load_barra(uni_df, start, end, None)
price_df = load_prices(uni_df, start, end, None)
uni_df = price_df[['ticker']]
ratings_df = load_ratings_hist(uni_df, start, end, True)
dbars_df = load_daybars(uni_df, start, end, None, freq='15Min')
bbars_df = load_bars(uni_df, start, end, None, freq=15)
intra_df = merge_intra_calcs(dbars_df, bbars_df)
daily_df = merge_barra_data(price_df, barra_df)
daily_df = transform_barra(daily_df)
locates_df = load_locates(uni_df, start, end)
forwards_df = calc_forward_returns(daily_df, horizon)
daily_df = pd.concat( [daily_df, forwards_df, ratings_df], axis=1)
daily_df, factor_df = calc_factors(daily_df)
daily_df = calc_price_extras(daily_df)
intra_df = merge_intra_data(daily_df, intra_df)
intra_df = calc_vol_profiles(intra_df)
dump_hd5(intra_df.sort(), "all")
dump_hd5(factor_df.sort(), "all.factors")

