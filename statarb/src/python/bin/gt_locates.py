#!/usr/bin/env python
import os
import re

output = os.popen(os.environ['BIN_DIR'] + "/gt_cmd.py status").readlines()
if len(output) == 0:
    print('ERROR: gt_cmd.py status returned nothing')
    exit(1)
    
for line in output:
    m = re.match('[0-9\:\.]+.+? (?P<sym>[A-Z\.]+) \[.+\] .+ (?P<size>[-+][0-9]+) / .+? \[(?P<locates>[0-9]+) locates\]$', line)
    if m is None:
        continue
    gd = m.groupdict()
    print '%s|%s' % (gd['sym'], gd['locates'])
