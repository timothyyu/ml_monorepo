#!/usr/bin/env python
import argparse
import csv
import gzip
import heapq
import math
import os
import sys

#n,min,max,mean,stdev,top5,bottom5
def computeStats(secid_value_pairs):
    n = len(secid_value_pairs)
    print n
    if n <= 1:
        print "Did not find any attributes..."
        return 0,0,0,0,0    
    
    s = sum([x[1] for x in secid_value_pairs])
    s2 = sum([x[1] ** 2 for x in secid_value_pairs])
    top5 = heapq.nlargest(5, secid_value_pairs, key=lambda x : x[1])
    bottom5 = heapq.nsmallest(5, secid_value_pairs, key=lambda x : x[1])
    
    return n, bottom5[0][1], top5[0][1], s / n, math.sqrt(1.0 / (n - 1.0) * (s2 - s * s / n)), top5, bottom5

parser = argparse.ArgumentParser(description='Calcres stats')
parser.add_argument("-t", action="store", dest="type", default="new", help="calcres file type [old|new]")
parser.add_argument("-f", action="store", dest="file", help="calcres file")
parser.add_argument("-a", action="store", dest="att", help="attribute name")
args = parser.parse_args()

if args.att is None:
    parser.print_help()
    sys.exit()

calcFile = args.file
if calcFile is None:
    calcFile = os.popen("ls -rt {}/calcres/calcres.*.txt.gz | tail -1".format(os.environ['RUN_DIR'])).readlines()[0].strip()

type = args.type
attName = args.att

print "Looking at {}".format(calcFile)
reader = gzip.open(calcFile, "r")

dialect = csv.Sniffer().sniff(reader.read(1024))
reader.seek(0)
if type == "new":
    csvReader = csv.DictReader(reader, fieldnames=["secid", "att", "att_type", "date", "value", "currency", "born"], dialect=dialect)
elif type == "old":
    csvReader = csv.DictReader(reader, fieldnames=["calctime", "coid", "issueid", "att", "date", "value"], dialect=dialect)
    
#load mapping of old system ids to secids
oldid2secid = {}
with open("/apps/ase/run/useq-live/old.secids.txt", "r") as f:
    for line in f:
        tokens = line.strip().split(r"|")
        coid = int(tokens[0])
        issueid = int(tokens[1])
        secid = int(tokens[2])
        oldid2secid[(coid, issueid)] = secid
    
#date-secid to timestamp-value
ds2tv = {}
for line in csvReader:
    if line["att"] != attName: continue
    if line["secid"] == "FCOV": continue
    
    secid = int(line["secid"]) if type == "new" else oldid2secid[(int(line["coid"]), int(line["issueid"]))]
    value = float(line["value"])
    timestamp = long(line["born"]) if type == "new" else - 1
    date = long(line["date"])
    
    existing = ds2tv.get((date, secid), None)
    if existing is None or timestamp > existing[0]:
        ds2tv[(date, secid)] = (timestamp, value)

#partition by date: date to list of secid, value pairs
d2sv = {}
for ds, tv in ds2tv.iteritems():
    sv = d2sv.get(ds[0], None)
    if sv is None:
        sv = []
        d2sv[ds[0]] = sv
    sv.append((ds[1], tv[1]))
    
#iterate for each day
for d, sv in d2sv.iteritems():
    date = d
    stats = computeStats(sv)
    
    print "Date: ", date
    print "Number: {}".format(stats[0])
    print "Min: {:.6f}".format(stats[1])
    print "Max: {:.6f}".format(stats[2])
    print "Mean: {:.6f}".format(stats[3])
    print "StdDev: {:.6f}".format(stats[4])
    print "Top-5: ", stats[5]
    print "Bottom-5: ", stats[6]
    
    print "\n"
