from regress import *
from util import *
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

def hl_fits(daily_df, full_df, horizon, name, reg_st, reg_ed, out_dir):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])

    for lag in range(1, horizon + 1):
        fits_df = fits_df.append(regress_alpha(daily_df, 'hl0_B_ma', lag, median=True, start=reg_st, end=reg_ed),
                                 ignore_index=True)
    plot_fit(fits_df, out_dir + "/" + "hl_daily_" + name + "_" + df_dates(daily_df))

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)
    coef0 = fits_df.ix['hl0_B_ma'].ix[horizon].ix['coef']

    if 'hl' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['hl'] = 0
        full_df['hlC_B_ma_coef'] = np.nan
        for lag in range(1, horizon + 1):
            full_df['hl' + str(lag) + '_B_ma_coef'] = np.nan

    for lag in range(1, horizon + 1):
        full_df.loc[daily_df.index, 'hl' + str(lag) + '_B_ma_coef'] = coef0 - fits_df.ix['hl0_B_ma'].ix[lag].ix['coef']

    for lag in range(1, horizon):
        full_df.loc[daily_df.index, 'hl'] += full_df['hl' + str(lag) + '_B_ma'] * full_df[
            'hl' + str(lag) + '_B_ma_coef']
    return full_df


def calc_hl_forecast(daily_df, horizon, reg_st, reg_ed, output_dir):
    daily_df = calc_hl_daily(daily_df, horizon)

    sector = 10  # 'Energy'
    print("Running hl for sector code %d" % (sector))
    sector_df = daily_df[daily_df['sector'] == sector]
    full_df = hl_fits(sector_df, daily_df, horizon, "in", reg_st, reg_ed, output_dir)

    print("Running hl for sector code %d" % (sector))
    sector_df = daily_df[daily_df['sector'] != sector]
    full_df = hl_fits(sector_df, daily_df, horizon, "ex", reg_st, reg_ed, output_dir)

    coefs = []
    for lag in range(1, horizon + 1):
        coefs.append('hl' + str(lag) + '_B_ma_coef')
    coef_df = full_df[coefs]

    # dump_alpha(full_df, 'hl')

    return full_df, coef_df


def six_months_before(date_s):
    if date_s[-4:] == '0101':
        return str(int(date_s[:4]) - 1) + '0630'
    else:
        return date_s[:4] + '0101'


def get_hl(start_s, end_s, dir):
    lookback = 30
    horizon = 3 # new
    d2 = end_s
    dfs = []
    for i in range(3):
        print("Loading raw data folder %s..." % d2)
        barra_df = pd.read_csv("%s/data/raw/%s/barra_df.csv" % (dir, d2), header=0, sep='|', dtype={'gvkey': str},
                               parse_dates=[0])
        uni_df = pd.read_csv("%s/data/raw/%s/uni_df.csv" % (dir, d2), header=0, sep='|', dtype={'gvkey': str},
                             parse_dates=[0])
        price_df = pd.read_csv("%s/data/raw/%s/price_df.csv" % (dir, d2), header=0, sep='|', dtype={'gvkey': str},
                               parse_dates=[0])
        price_df.set_index(['date', 'gvkey'], inplace=True)
        uni_df.set_index('gvkey', inplace=True)
        barra_df.set_index(['date', 'gvkey'], inplace=True)

        daily_df = merge_barra_data(price_df, barra_df)
        result_df = calc_forward_returns(daily_df, horizon)
        daily_df = daily_df.merge(result_df, on=['date', 'gvkey'])
        daily_df = daily_df.join(uni_df[['sedol']],on='gvkey', how='inner')
        daily_df.index.names=['date','gvkey']
        # intra_df = merge_intra_data(daily_df, daybar_df)
        dfs.append(daily_df)
        d2 = six_months_before(d2)
    reg_st = d2
    reg_ed = start_s
    daily_df = pd.concat(dfs).sort_index()
    graphs_dir = dir + "/data/all_graphs"
    full_df, coef_df = calc_hl_forecast(daily_df, horizon, reg_st, reg_ed, graphs_dir)
    full_df = full_df.truncate(before=dateparser.parse(start_s), after=dateparser.parse(end_s))
    output_dir = dir+ "/data/all"
    full_df.to_hdf('%s/all.%s-%s.h5' % (output_dir, start_s, end_s), 'full_df', mode='w')
    return coef_df
