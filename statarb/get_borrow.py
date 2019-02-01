import pandas as pd
import argparse
import glob

def get_borrow(locates_dir):
    result_dfs = []
    for ff in sorted(glob.glob(locates_dir + "/locates/Historical_Avail_US_Weekly_*")):
        print("Loading", ff)
        df = pd.read_csv(ff, parse_dates=['history_date'],
                         usecols=['history_date', 'sedol', 'shares', 'fee', 'ticker'])
        df = df.rename(columns={'history_date': 'date', 'ticker': 'symbol'})
        result_dfs.append(df)
    result_df = pd.concat(result_dfs)
    result_df.set_index("date", inplace=True)
    result_df.to_csv(r"%s/locates/borrow.csv" % locates_dir, "|")
    print(result_df)

parser = argparse.ArgumentParser()
parser.add_argument("--locates_dir", help="the directory to the locates folder", type=str, default='.')
args = parser.parse_args()
get_borrow(args.locates_dir)
