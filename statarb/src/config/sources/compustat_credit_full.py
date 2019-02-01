{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/fullcxf/asc/aSPCRd01/",
    "sub_dirs": "adsprate:refaSPCRd01",
    "local_dir": "/compustat/credit_full",
    "regex": "f_.+\.[0-9]+\.asc\.zip",
    "prefix": "%Y%m_",
    "flag": ".zip:.flg",
    "format": "compustat",
    "new_data_frequency": 30L*24L*60L*60L*1000L,
}
