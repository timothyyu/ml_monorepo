import h5py
import pandas as pd

pd.set_option('display.max_columns', 100)
filename1 = './all/all.20040101-20040630.h5'
df = pd.read_hdf(filename1, key='full_df')
print(df.index.levels[0].dtype)
df = df.reset_index()
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
df.set_index(['date', 'gvkey'], inplace=True)
print(df.index.levels[0].dtype)
df.to_hdf('./all/all.20040101-20040630.h5', 'full_df', mode='w')
