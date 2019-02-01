{
    "method": "ftp",
    "host": "ftp.standardandpoors.com",
    "user": "limegrp",
    "pass": "sh3nd3r",
    
    "remote_dir": "/outbound/fullcxf/asc/pkgcore01/",
    "local_dir": "compustat/global_full",
    "sub_dirs": "co_aaudit:co_adesind:co_adjfact:co_afnd1:co_afnd2:co_afnddc1:co_afnddc2:co_afntind:co_ainvval:co_amkt:co_filedate:co_fortune:co_hgic:co_iaudit:co_idesind:co_ifndq:co_ifndsa:co_ifndytd:co_ifntq:co_ifntsa:co_ifntytd:co_imkt:co_industry:co_ipcd:company:co_mthly:co_offtitl:currency:ecind_desc:ecind_mth:exrt_dly:exrt_mth:idx_ann:idx_anndes:idxcst_his:idx_daily:idx_index:idx_mth:idx_qrt:idx_qrtdes:refpkgcore01:sec_ann:sec_annfd:sec_divid:sec_dprc:sec_dtrt:sec_idesc:sec_ifnd:sec_ifnt:sec_mdivfn:sec_msptfn:sec_mth:sec_mthdiv:sec_mthprc:sec_mthspt:sec_mthtrt:sec_spind:sec_split:security:spidx_cst:spind:spind_dly:spind_mth",
    "regex": "f_.+\.[0-9]+\.asc\.zip",
    "prefix": "%Y%m_",
    "flag": ".zip:.flg",
    "format": "compustat",
    "new_data_frequency": 30L*24L*60L*60L*1000L,
}
