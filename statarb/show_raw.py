import pandas as pd
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--dir", help="the directory where raw files are stored", type=str, default='.')
args = parser.parse_args()
dir = args.dir
barra_df = pd.read_csv("%s/barra_df.csv" % (dir), header=0, sep='|', dtype={'gvkey': str}, parse_dates=[0])
uni_df = pd.read_csv("%s/missing_borrow.csv" % (dir), header=0, sep='|', dtype={'gvkey': str})
price_df = pd.read_csv("%s/price_df.csv" % (dir), header=0, sep='|', dtype={'gvkey': str}, parse_dates=[0])
price_df.set_index(['gvkey', 'date'], inplace=True)
uni_df.set_index('gvkey', inplace=True)
barra_df.set_index(['gvkey', 'date'], inplace=True)

print(uni_df)
