#!/usr/bin/env python 

from loaddata import *
from util import *

ofile = "../../mus/20120208.ORDER.csv"
efile = "../../mus/20120208.EXECUTION.csv"

odf = load_qb_orders(ofile)
edf = load_qb_exec(efile)

merged_df = pd.merge(odf.reset_index(), edf.reset_index(), how='left', left_on=['id'], right_on=['order_id'], suffixes=['_ord', '_exec'])
merged_df['symbol'] = merged_df['symbol_ord']
del merged_df['symbol_ord']
del merged_df['symbol_exec']
del merged_df['index']
del merged_df['id']
assert merged_df['sid_ord'] == merged_Df['sid_exec']
merged_df['sid'] = merged_df['sid_ord']
del merged_df['sid_ord']
del merged_df['sid_exec']
merged_df.set_index(['ts_ord', 'sid'], inplace=True)






