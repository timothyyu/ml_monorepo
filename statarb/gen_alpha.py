import argparse
import os
import glob
import re
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="the starting date to generate alpha signals, formatted as 'YYYYMMdd'",
                        type=str)
    parser.add_argument("--end", help="the end date to generate alpha signals, formatted as 'YYYYMMdd'", type=str)
    parser.add_argument("--dir", help="the root directory", type=str, default='.')
    args = parser.parse_args()

    start = args.start
    end = args.end
    dir = args.dir

    found = False
    for ff in sorted(glob.glob(dir + "/data/all/all.*")):
        m = re.match(r".*all\.(\d{8})-(\d{8}).h5", str(ff))
        d1 = m.group(1)
        d2 = m.group(2)
        if d2 <= start or d1 >= end: continue
        print("Loading %s" % ff)
        found = True
        df = pd.read_hdf(ff, key='full_df')
        new = df[['hl']]
        new.to_csv(r"%s/data/hl/alpha.hl.%s-%s.csv" % (dir, d1, d2))
        print(new)
    if not found:
        print("insufficient \"all...\" files")

main()
