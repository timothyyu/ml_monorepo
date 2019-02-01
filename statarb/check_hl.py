import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--start")
parser.add_argument("--end")
parser.add_argument("--dir", help="the root directory", default='.')
args = parser.parse_args()
data_dir = args.dir + '/data'
ff = data_dir + '/hl/alpha.hl.'+ args.start +'-'+ args.end +'.csv'
df = pd.read_csv(ff, header=0, parse_dates=['date'], dtype={'gvkey': str})
# print(df)
# import sys
# sys.exit()
df = df.set_index(['date','gvkey'])
df['hl_abs']=df['hl'].abs()
df = df.sort_values('hl_abs',ascending=False)
maxhl=df.iloc[[0]]
print(maxhl)

ff = data_dir + "/raw/" + args.end + "/price_df.csv"
df = pd.read_csv(ff, header=0, delimiter='|', parse_dates=['date'], dtype={'gvkey': str})
df = df.set_index(['date','gvkey']).sort_index()
print(df.loc[('2013-04-30','011644'),['high','low','open','close']])
