{
    "method": "ftp",
    "host": "ftp.barra.com",
    "user": "towerres",
    "pass": "s45yV43I",
    "tz": "US/Pacific",
    #"tz": "Etc/GMT+8",
    
    "remote_dir": "/towerres/use3s_daily",
    "local_dir": "/barra/use3s_daily",
    "regex": "USE3S[0-9]{6}\.(RSK|DFR)",
    "format": "barra_test",
    "new_data_frequency": 24L*60L*60L*1000L,
}
