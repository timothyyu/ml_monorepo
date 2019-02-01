{
    "method": "oli_buybacks",

    "remote_dir": "",
    "local_dir": "/onlineinvestor/buybacks",
    #use these to download historical data
    #"sub_dirs": "jan_thru_jun_10-2010:oct_nov_dec_09-2009:may_thru_sep_09-2009:apr_09_archive-2009:mar_09_archive-2009:feb_09_archive-2009:jan_09_archive-2009:dec_08_archive-2008:title-2008:oct_08_archive-2008:aug_08_archive-2008:jul_08_archive-2008:jun_08_archive-2008:may_08_archive-2008:apr_08_archive-2008:mar_08_archive-2008:feb_08_archive-2008:jan_08_archive-2008",
    #"local_dir": "onlineinvestor/buybacks_hist/",
    "regex": ".+\.txt",
    "format": "oli_buybacks",
    "new_data_frequency": 24L*60L*60L*1000L,
}
