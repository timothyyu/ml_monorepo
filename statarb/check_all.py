import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--start")
parser.add_argument("--end")
parser.add_argument("--dir", help="the root directory", default='.')
args = parser.parse_args()
pd.set_option('display.max_columns', 100)
data_dir = args.dir + '/data'
ff = data_dir + '/all/all.'+ args.start +'-'+ args.end +'.h5'
df = pd.read_hdf(ff, 'full_df')
#print(df[['symbol','sector','ind1']].head())
#print(df[['symbol','sector','ind1']].xs('011644',level=1).head())
#print(df.loc[df['symbol']=='AMZN',['symbol','sector','ind1']].head())
