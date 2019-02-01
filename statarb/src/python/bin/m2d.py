#!/usr/bin/env python
import sys
import re
import util

if len(sys.argv)==1:
    data = sys.stdin.readlines()
    for line in data:
        fields = line.strip().split("|")
        newlin = ""
        for i,field in enumerate(fields):
            if re.match("\d{12,13}", field):
                newlin += str(util.convert_millis_to_datetime(long(field)).strftime("%Y%m%d %H:%M:%S"))
            else:
                newlin += field
            if i!=len(fields)-1:
                newlin += "|"
        print newlin
elif len(sys.argv)==2:
    print util.convert_millis_to_datetime(long(sys.argv[1])).strftime("%Y%m%d %H:%M:%S")
else:
    print "Either pipe lines, or give a single long as input"