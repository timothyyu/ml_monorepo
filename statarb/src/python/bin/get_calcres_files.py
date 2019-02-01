#!/usr/bin/env python

import glob
import re
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-c", "--calctime", dest="calctime", type=int, default=1400)
parser.add_option("-s", "--startdate", dest="startdate", type=int)
parser.add_option("-r", "--rootdir", dest="rootdir", default="/apps/multex/trade/run/live-prod")
(options, args) = parser.parse_args()

directories = glob.glob(options.rootdir + "/2010/*/*/calcres")
directories.sort()
for adir in directories:
    fs = [g for g in glob.glob(adir + "/calcres.*.txt.gz")]
    fs.sort()
    found = False
    for file in fs:
        if found: continue
        match = re.search('.*calcres\.(\d+)_(\d+)\.txt\.gz', file)
        if match:
            if float(match.group(1)) > options.startdate and float(match.group(2)) > options.calctime:
                print file
                found = True



