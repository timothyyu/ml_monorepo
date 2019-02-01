{
    "method": "ftp",
    "host": "ftp.barra.com",
    "user": "towerres",
    "pass": "s45yV43I",
    "tz": "US/Pacific",
    #"tz": "Etc/GMT+8",

    "local_dir": "/barra/use3s_monthly",
    "remote_dir": "/towerres",
    "regex": "USE3S[0-9]{4}\.(BET|COV|FRT|RET|RSK)",
    "format": "barra_test",
    "new_data_frequency": 30L*24L*60L*60L*1000L,
}
