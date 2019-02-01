from regress import *
from util import *
from s_loaddata import *
from dateutil import parser as dateparser


def calc_hl_daily(full_df, horizon):
    print("Caculating daily hl...")
    result_df = full_df.reset_index()
    # result_df = filter_expandable(result_df)
    result_df = result_df[['close', 'high', 'low', 'date', 'ind1', 'gvkey']]

    print("Calculating hl0...")
    result_df['hl0'] = result_df['close'] / np.sqrt(result_df['high'] * result_df['low'])
    result_df['hl0_B'] = winsorize(result_df['hl0'])

    result_df = result_df.dropna()
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['hl0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['hl0_B_ma'] = indgroups['hl0_B']
    result_df.set_index(['date', 'gvkey'], inplace=True)

    result_df['hl3'] = result_df['hl0'].unstack().shift(3).stack()  # new

    print("Calulating lags...")
    for lag in range(1, horizon):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['hl' + str(lag) + '_B_ma'] = shift_df['hl0_B_ma']

    result_df = pd.merge(full_df, result_df, how='left', on=['date', 'gvkey'], sort=False,
                         suffixes=['', '_dead'])  # new
    result_df = remove_dup_cols(result_df)
    return result_df


def hl_fits(daily_df, full_df, horizon, name):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])

    for lag in range(1, horizon + 1):
        fits_df = fits_df.append(regress_alpha_daily(daily_df, 'hl0_B_ma', lag), ignore_index=True)
    plot_fit(fits_df, "hl_daily_" + name + "_" + df_dates(daily_df))

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)
    coef0 = fits_df.ix['hl0_B_ma'].ix[horizon].ix['coef']

    if 'hl' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['hl'] = 0
        full_df['hlC_B_ma_coef'] = np.nan
        for lag in range(0, horizon + 1):
            full_df['hl' + str(lag) + '_B_ma_coef'] = np.nan

    for lag in range(1, horizon + 1):
        full_df.ix[daily_df.index, 'hl' + str(lag) + '_B_ma_coef'] = coef0 - fits_df.ix['hl0_B_ma'].ix[lag].ix['coef']

    for lag in range(0, horizon):
        full_df.ix[daily_df.index, 'hl'] += full_df['hl' + str(lag) + '_B_ma'] * full_df['hl' + str(lag) + '_B_ma_coef']

    return full_df


def calc_hl_forecast(daily_df, horizon):
    daily_df = calc_hl_daily(daily_df, horizon)

    sector = 10  # 'Energy'
    print("Running hl for sector code %d" % (sector))
    sector_df = daily_df[daily_df['sector'] == sector]
    full_df = hl_fits(sector_df, daily_df, horizon, "in")

    print("Running hl for sector code %d" % (sector))
    sector_df = daily_df[daily_df['sector'] != sector]
    full_df = hl_fits(sector_df, daily_df, horizon, "ex")

    # dump_alpha(full_df, 'hl')

    return full_df


def get_hl(start_s, end_s):
    lookback = 30
    horizon = 5
    pd.set_option('display.max_columns', 100)
    start = dateparser.parse(start_s)
    end = dateparser.parse(end_s)
    uni_df = get_uni(start, end, lookback)
    barra_df = load_barra(uni_df, start, end)
    price_df = load_price(uni_df, start, end)
    daily_df = merge_barra_data(price_df, barra_df)
    result_df = calc_forward_returns(daily_df, horizon)
    daily_df = daily_df.merge(result_df, on=['date', 'gvkey'])
    # intra_df = merge_intra_data(daily_df, daybar_df)
    full_df = calc_hl_forecast(daily_df, horizon)
    full_df.to_hdf('all.%s-%s.h5' % (start_s, end_s), 'full_df', mode='w')
    print(full_df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="the starting date, formatted as 'YYYYMMdd'", type=str)
    parser.add_argument("--end", help="the end date, formatted as 'YYYYMMdd'", type=str)
    parser.add_argument("--data_dir", help="the directory where raw data folder is stored", type=str, default='.')
    parser.add_argument("--out_dir", help="the directory where new data will be generated", type=str, default='.')
    args = parser.parse_args()
    get_hl(args.start, args.end, args.data_dir, args.out_dir)
