{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/",
    "local_dir": "compustat/global_corporate_actions",
    "regex": "corp_actions_hist_intl\.zip",
    "flag": ".zip:.flg",
    "new_data_frequency": 24L*60L*60L*1000L,
}
