{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/trancxf/bNAstd01/",
    "local_dir": "/compustat/compustat",
    "regex": "t_.+-[0-9]{8}\.[0-9]{2}\.asc\.zip",
    "flag": ".zip:.flg",
    "format": "compustat",
    "new_data_frequency": 12L*60L*60L*1000L,
}
