import pandas as pd

def main(locates_dir):
    pd.set_option('display.max_columns', 100)
    ff = locates_dir + "/locates/borrow.csv"
    print("Loading", ff)
    result_df = pd.read_csv(ff, parse_dates=['date'], usecols=['sedol', 'date', 'shares', 'fee'], sep='|')
    print(result_df[result_df['sedol']=='2484088'])

main("./data")
