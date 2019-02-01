import hl_csv
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--start", help="the starting date, formatted as YYYYMMdd", type=str)
parser.add_argument("--end", help="the ending date, formatted as YYYYMMdd", type=str)
parser.add_argument("--dir", help="the root directory", type=str, default='.')
args = parser.parse_args()
coef_dfs = []
period = []
#pd.set_option('expand_frame_repr', False) to change

d1 = args.start
while d1 < args.end:
    if d1[-4:] == '0101':
        d2 = d1[:4] + '0630'
    else:
        d2 = str(int(d1[:4]) + 1) + '0101'
    print("Creating all.%s-%s.h5..." % (d1, d2))
    period.append(d1 + "-" + d2)
    coef_dfs.append(hl_csv.get_hl(d1, d2, args.dir).drop_duplicates())
    d1 = d2

for i in range(len(period)):
    print("Unique coefficients in the period %s:" % period[i])
    print(coef_dfs[i])
