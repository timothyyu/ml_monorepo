#!/usr/bin/env python                                                                                                                                                                                          
import sys
import config

source_name = sys.argv[1]
local_path = sys.argv[2]
remote_path = sys.argv[3]

config = config.load_source_config(source_name)
if (config["method"] == "sftp"):
    from data_sources.sftp_source import SFTPSource
    source = SFTPSource(config["host"], config["user"], config["pass"])
else:
    raise ValueError("Source doesn't support put")

print 'uploading to %s: %s -> %s' % (source_name, local_path, remote_path)
source.list(".+")
source.put(local_path, remote_path)
source.list(".+")
del source
