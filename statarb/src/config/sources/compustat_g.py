{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/trancxf/pkgcore01/",
    "local_dir": "compustat/global",
    "regex": "t_.+-[0-9]{8}\.[0-9]{2}\.asc\.zip",
    "flag": ".zip:.flg",
    "format": "compustat2",
    "new_data_frequency": 8L*60L*60L*1000L,
}
