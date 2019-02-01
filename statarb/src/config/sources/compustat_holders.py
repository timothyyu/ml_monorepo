{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/",
    "local_dir": "compustat/holders",
    "regex": "(Institutional|Insider).+\.zip",
    "flag": ".zip:.flg",
    "new_data_frequency": 7L*24L*60L*60L*1000L,
}
