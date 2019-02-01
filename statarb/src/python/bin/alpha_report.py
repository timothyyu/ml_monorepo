#!/usr/bin/env python
import config
import datetime
import os
import re
import subprocess
import time

# Create the report directory if its not already present
ALPHA_REPORT_DIR = os.environ['DATA_DIR'] + '/trading/' + os.environ['STRAT'] + '/exec/' + os.environ['DATE']
if not os.path.exists(ALPHA_REPORT_DIR):
    os.makedirs(ALPHA_REPORT_DIR)

os.chdir(ALPHA_REPORT_DIR)

# Look at exec.conf to get list of servers
cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
trade_cfg = config.load_trade_config(cfg_file)

# Create output file
outfile = open('alpha.' + os.environ['DATE'] + '.txt', 'w')
outfile.write('ticker|kfrtAlpha (bps)|kfrtWeight|imbAlpha (bps)|imbWeight|netAlpha (bps)|timestamp\n')
UTC_OFFSET_TIMEDELTA = datetime.datetime.utcnow() - datetime.datetime.now()

def bps(input):
  if input.strip() == "NA":
    return input
  return str(10000*float(input))

# Download fills file from each server
REMOTE_LOG_DIR = '/spare/local/guillotine/log'
alphaByTS = {}
for (host,port) in trade_cfg['servers']:
  server_num = re.findall('[0-9]+', host)[0]
  p = subprocess.Popen('scp ase@' + host + ':' + REMOTE_LOG_DIR + '/rts1_' + str(server_num) + '/alpha.log alpha.rts1_' + server_num + '.log',env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  retcode = p.wait()
  if not os.path.exists('alpha.rts1_' + server_num + '.log'):
    continue
  alphaFile = open('alpha.rts1_' + server_num + '.log', 'r')
  init = False
  for line in alphaFile:
    if not init:
      init = True
      continue

    if len(line.strip()) == 0:
      continue

    fields = line.strip().split('|')
    ts = fields[0]
    temp = ts.split()
    newts = temp[0] + ' ' + temp[1].split('.')[0]
    # now convert ts to UTC
    local_datetime = datetime.datetime.strptime(newts, "%Y/%m/%d %H:%M:%S")
    utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
    newts = utc_datetime.strftime("%Y%m%d %H:%M:%S")
    if newts not in alphaByTS:
      alphaByTS[newts] = []
    alphaByTS[newts].append((fields[1],bps(fields[2]),fields[3],bps(fields[4]),fields[5],bps(fields[6])))
  alphaFile.close()
  p = subprocess.Popen('gzip alpha.rts1_' + server_num + '.log',env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  retcode = p.wait()

tsList = alphaByTS.keys()
tsList.sort()
for ts in tsList:
  alphaByTS[ts].sort()
  for item in alphaByTS[ts]:
    for field in item:
      outfile.write(field + '|')
    outfile.write(ts + '\n')

outfile.close()
p = subprocess.Popen('gzip alpha.' + os.environ['DATE'] + '.txt',env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
retcode = p.wait()

