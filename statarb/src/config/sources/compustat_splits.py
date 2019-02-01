{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/",
    "local_dir": "compustat/splits",
    "regex": "future_splits.txt",
    "prefix": "%Y%m%d_",
    "format": "compustat_splits",
    "new_data_frequency": 24L*60L*60L*1000L,
}
