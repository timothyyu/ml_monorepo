#!/usr/bin/env python
import config
import os
import re
import subprocess
import time
import util
from data_sources import file_source

# Create the report directory if its not already present
EXEC_REPORT_DIR = os.environ['REPORT_DIR'] + '/exec/' + os.environ['DATE']
if not os.path.exists(EXEC_REPORT_DIR):
    os.makedirs(EXEC_REPORT_DIR)

os.chdir(EXEC_REPORT_DIR)

# Look at exec.conf to get list of servers
cfg_file = os.environ['CONFIG_DIR'] + '/exec.conf'
trade_cfg = config.load_trade_config(cfg_file)
moc_cfg_file = os.environ['CONFIG_DIR'] + '/exec.moc.conf'
moc_trade_cfg = config.load_trade_config(moc_cfg_file)

# Create output file
outfile = open('exec.' + os.environ['DATE'] + '.txt', 'w')
outfile.write('As of ' + time.asctime(time.gmtime()) + '\n\n')
outfile.write('Aggregate Statistics (each row sums to 100%)\n')
outfile.write('field')

dollars = dict()
numFills = dict()

def check_add_algo(algo, input):
  if not (algo in input):
    input[algo] = {}

def check_add_exch(input, exch):
  if not (exch in input):
    input[exch] = {}

def check_add_category(input, category, value):
  if not (category in input):
    input[category] = 0
  input[category] += value

def get_liq_str(liq):
  if liq == 'A':
    return 'Add'
  elif liq == 'R':
    return 'Rem'
  elif liq == 'O':
    return 'Other'
  else:
    print ('Unknown liquidity type ' + liq)
    return ''

def check_add_liquidity(input, liq, value):
  category = get_liq_str(liq)
  check_add_category(input, 'liq' + category, value)

# Read the orders files in RUN_DIR, and create an orderID to aggressiveness mapping
fs = file_source.FileSource(os.environ['RUN_DIR'] + '/orders/')
listing = fs.list('orders\.[0-9_]+\.txt')
oid2aggr = {}
for item in listing:
    orderfile = open(os.environ['RUN_DIR'] + '/orders/' + item[0], 'r')
    reader = util.csvdict(orderfile)
    for row in reader:
        orderid = long(row['orderid'])
        aggr = float(row['aggr'])
        oid2aggr[orderid] = aggr
    orderfile.close()

# Download fills file from each server
REMOTE_LOG_DIR = os.environ['EXEC_LOG_DIR']
exchanges = set()
algos = set()
aggrs = set()
liqs = set()
trade_cfg['servers'].extend(moc_trade_cfg['servers'])
for (host,port) in trade_cfg['servers']: 
  server_num = re.findall('[0-9]+', host)[0]
  p = subprocess.Popen('scp ase@' + host + ':' + REMOTE_LOG_DIR + '/fills.txt fills.rts1_' + server_num + '.txt',env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  retcode = p.wait()
  outfile.write(' | ' + host)
  if not os.path.exists('fills.rts1_' + server_num + '.txt'):
    continue
  fillsFiles = open('fills.rts1_' + server_num + '.txt', 'r')
  init = False
  for line in fillsFiles:
    if not init:
      init = True
      dollars[host] = {}
      numFills[host] = {}
      continue

    fields = line.split('|')
    shares = int(fields[4])
    price = float(fields[5])
    exch = fields[6].strip()
    liq = fields[7].strip()
    orderID = long(fields[8])
    algo = fields[9].strip()
    aggr = 'UNKN'
    if orderID in oid2aggr:
        aggr = oid2aggr[orderID]

    exchanges.add(exch)
    algos.add(algo)
    aggrs.add(aggr)
    liqStr = get_liq_str(liq)
    liqs.add(liqStr)
    check_add_exch(dollars[host], exch)
    check_add_exch(numFills[host], exch)

    notional = abs(shares) * price
    signedNotional = shares * price
    check_add_category(dollars[host][exch], 'all', notional)
    check_add_category(numFills[host][exch],'all', 1)
    check_add_liquidity(numFills[host][exch], liq, 1)
    check_add_category(dollars[host][exch], 'algo' + algo, notional)
    check_add_category(numFills[host][exch],'algo' + algo, 1)
    check_add_category(dollars[host][exch], 'aggr' + str(aggr), notional)
    check_add_category(numFills[host][exch],'aggr' + str(aggr), 1)
    check_add_category(dollars[host][exch], 'aggralgo' + str(aggr) + ' ' + algo, notional)
    check_add_category(numFills[host][exch],'aggralgo' + str(aggr) + ' ' + algo, 1)
    check_add_category(dollars[host][exch], 'algoliq' + algo + ' liq ' + liqStr, notional)
    check_add_category(numFills[host][exch],'algoliq' + algo + ' liq ' + liqStr, 1)
    if shares < 0:
      check_add_category(dollars[host][exch], 'sell', signedNotional)
    else:
      check_add_category(dollars[host][exch], 'buy', signedNotional)

outfile.write(' | all \n')
exchanges = list(exchanges)
exchanges.sort()
algos = list(algos)
algos.sort()
aggrs = list(aggrs)
aggrs.sort()
liqs = list(liqs)
liqs.sort()

# assumes input of the kind input[host][exch], which contains category
def aggrCategoryByHost(input, category, header, universeTotal=None):
  outfile.write(header)
  stuff = dict()
  stuffTotal = 0
  for (host,port) in trade_cfg['servers']:
    stuff[host] = 0
    if host not in input:
      input[host] = {}
    for exch in input[host]:
      if category not in input[host][exch]:
        input[host][exch][category] = 0
      stuff[host] += input[host][exch][category]
    stuffTotal += stuff[host]

  for (host,port) in trade_cfg['servers']:
    if abs(stuffTotal) > 0:
      percent = ('%.2f' % (100*stuff[host]/float(stuffTotal)))
    else:
      percent = '0'
    outfile.write(' | ' + str(stuff[host]) + ' (' + percent + '%)')
  if universeTotal == None:
    outfile.write(' | ' + str(stuffTotal) + '\n')
  else:
    if abs(universeTotal) > 0:
      percent = ('%.2f' % (100*abs(stuffTotal/float(universeTotal))))
      outfile.write(' | ' + str(stuffTotal) + ' (' + percent + '%)\n')
  return stuffTotal

# assumes input of the kind input[host][exch]
# universeTotal is the sum of input across host and exchanges
def aggrByHost(input, header, universeTotal=None):
  outfile.write(header)
  stuff = dict()
  stuffTotal = 0
  for (host,port) in trade_cfg['servers']:
    stuff[host] = 0
    if host not in input:
      input[host] = {}
    for exch in input[host]:
      stuff[host] += input[host][exch]
    stuffTotal += stuff[host]

  for (host,port) in trade_cfg['servers']:
    if abs(stuffTotal) > 0:
      percent = ('%.2f' % (100*stuff[host]/float(stuffTotal)))
    else:
      percent = '0'
    outfile.write(' | ' + str(stuff[host]) + ' (' + percent + '%)')
  if universeTotal == None:
    outfile.write(' | ' + str(stuffTotal) + '\n')
  else:
    if abs(universeTotal) > 0:
      percent = ('%.2f' % (100*abs(stuffTotal/float(universeTotal))))
      outfile.write(' | ' + str(stuffTotal) + ' (' + percent + '%)\n')
  return stuffTotal

# assumes input of the kind input[host][exch] for a sub-category e.g. input could be addLiqByHost
# allinput is of the kind allinput[host][exch] aggregated across categories e.g. numFillsByHost 
# Columns go across categories, and sum to 100%.
def categoryAggrByHost(input, category, header):
  outfile.write(header)
  stuff = dict()
  stuffTotal = 0
  allStuff = dict()
  allStuffTotal = 0
  for (host,port) in trade_cfg['servers']:
    stuff[host] = 0
    allStuff[host] = 0
    if host not in input:
      input[host] = {}
    for exch in input[host]:
      if category not in input[host][exch]:
          input[host][exch][category] = 0
      stuff[host] += input[host][exch][category]
      allStuff[host] += input[host][exch]['all']
    stuffTotal += stuff[host]
    allStuffTotal += allStuff[host]

  for (host,port) in trade_cfg['servers']:
    if abs(allStuff[host]) > 0:
      percent = ('%.2f' % (100*abs(stuff[host]/float(allStuff[host]))))
    else:
      percent = '0'
    outfile.write(' | ' + str(stuff[host]) + ' (' + percent + '%)')
  if abs(allStuffTotal) > 0:
    percent = ('%.2f' % (100*abs(stuffTotal/float(allStuffTotal))))
    outfile.write(' | ' + str(stuffTotal) + ' (' + percent + '%)\n')

# assumes input of the kind input[host][exch] for a sub-category e.g. input could be addLiqByHost
# allinput is of the kind allinput[host][exch] aggregated across categories e.g. numFillsByHost 
# Columns go across categories, and sum to 100%.
def subAggrByHost(input, header, allInput):
  outfile.write(header)
  stuff = dict()
  stuffTotal = 0
  allStuff = dict()
  allStuffTotal = 0
  for (host,port) in trade_cfg['servers']:
    stuff[host] = 0
    allStuff[host] = 0
    if host not in input:
      input[host] = {}
    for exch in input[host]:
      stuff[host] += input[host][exch]
      allStuff[host] += allInput[host][exch]
    stuffTotal += stuff[host]
    allStuffTotal += allStuff[host]

  for (host,port) in trade_cfg['servers']:
    if abs(allStuff[host]) > 0:
      percent = ('%.2f' % (100*abs(stuff[host]/float(allStuff[host]))))
    else:
      percent = '0'
    outfile.write(' | ' + str(stuff[host]) + ' (' + percent + '%)')
  if abs(allStuffTotal) > 0:
    percent = ('%.2f' % (100*abs(stuffTotal/float(allStuffTotal))))
    outfile.write(' | ' + str(stuffTotal) + ' (' + percent + '%)\n')

# assumes input of the kind input[host][exch]. Computes the aggregate for each host, across 
# exchanges, so that columns sum to 100%.
def addingPerExch(input, header):
  exchTotal = dict()
  total = 0
  for exch in exchanges:
    exchTotal[exch] = 0
    for (host,port) in trade_cfg['servers']:
      if host not in input:
        input[host] = {}
      if not (exch in input[host]):
        input[host][exch] = 0
      exchTotal[exch] += input[host][exch]
    total += exchTotal[exch]

  for exch in exchanges:
    outfile.write(header + ' ' + exch)
    for (host,port) in trade_cfg['servers']:
      if abs(exchTotal[exch]) > 0:
        percent = ('%.2f' % (100*input[host][exch]/float(exchTotal[exch])))
      else:
        percent = '0'
      outfile.write(' | ' + str(input[host][exch]) + ' (' + percent + '%)')
#    outfile.write('\n')

    if abs(total) > 0:
      percent = ('%.2f' % (100*exchTotal[exch]/float(total)))
    else:
      percent = '0'
    outfile.write(' | ' + str(exchTotal[exch]) + ' (' + percent + '%)' + '\n')

def addingCategoryPerHost(input, category, header):
  hostTotal = dict()
  exchTotal = dict()
  total = 0
  for (host,port) in trade_cfg['servers']:
    hostTotal[host] = 0
    for exch in exchanges:
      if host not in input:
        input[host] = {}
      if exch not in input[host]:
        input[host][exch] = {}
      if exch not in exchTotal:
        exchTotal[exch] = 0
      if category not in input[host][exch]:
        input[host][exch][category] = 0
      hostTotal[host] += input[host][exch][category]
      exchTotal[exch] += input[host][exch][category]
    total += hostTotal[host]

  for exch in exchanges:
    outfile.write(header + ' ' + exch)
    for (host,port) in trade_cfg['servers']:
      if abs(hostTotal[host]) > 0:
        percent = ('%.2f' % (100*input[host][exch][category]/float(hostTotal[host])))
      else:
        percent = '0'
      outfile.write(' | ' + str(input[host][exch][category]) + ' (' + percent + '%)')

    if abs(total) > 0:
      percent = ('%.2f' % (100*exchTotal[exch]/float(total)))
    else:
      percent = '0'
    outfile.write(' | ' + str(exchTotal[exch]) + ' (' + percent + '%)' + '\n')
  outfile.write('\n')

def addingPerHost(input, header):
  hostTotal = dict()
  exchTotal = dict()
  total = 0
  for (host,port) in trade_cfg['servers']:
    hostTotal[host] = 0
    if host not in input:
      input[host] = {}
    for exch in input[host]:
      if not (exch in exchTotal):
        exchTotal[exch] = 0
      hostTotal[host] += input[host][exch]
      exchTotal[exch] += input[host][exch]
    total += hostTotal[host]

  for exch in exchanges:
    outfile.write(header + ' ' + exch)
    for (host,port) in trade_cfg['servers']:
      if abs(hostTotal[host]) > 0:
        percent = ('%.2f' % (100*input[host][exch]/float(hostTotal[host])))
      else:
        percent = '0'
      outfile.write(' | ' + str(input[host][exch]) + ' (' + percent + '%)')

    if abs(total) > 0:
      percent = ('%.2f' % (100*exchTotal[exch]/float(total)))
    else:
      percent = '0'
    outfile.write(' | ' + str(exchTotal[exch]) + ' (' + percent + '%)' + '\n')
  outfile.write('\n')

totalCategoryDollars = aggrCategoryByHost(dollars, 'all', 'Total $')
totalCategoryFills = aggrCategoryByHost(numFills, 'all', '# Fills')
totalCategoryBuy = aggrCategoryByHost(dollars, 'buy', 'Buy $', totalCategoryDollars)
totalCategorySell = aggrCategoryByHost(dollars, 'sell', 'Sell $', totalCategoryDollars)
outfile.write('\n')

outfile.write('Aggregate Statistics (each column sums to 100%)\n')
outfile.write('field')
for (host,port) in trade_cfg['servers']:
  outfile.write(' | ' + host)
outfile.write(' | all \n')
categoryAggrByHost(numFills, 'liqAdd', 'Added Liq')
categoryAggrByHost(numFills, 'liqRem', 'Removed Liq')
categoryAggrByHost(numFills, 'liqOther', 'Other Liq')
outfile.write('\n')
categoryAggrByHost(dollars, 'buy', 'Buy $')
categoryAggrByHost(dollars, 'sell', 'Sell $')
outfile.write('\n')

addingCategoryPerHost(dollars, 'all', 'Total $')
addingCategoryPerHost(numFills, 'all', '# Fills')
addingCategoryPerHost(numFills, 'liqAdd', 'Added liq')
addingCategoryPerHost(numFills, 'liqRem', 'Removed liq')
addingCategoryPerHost(numFills, 'liqOther', 'Other liq')
addingCategoryPerHost(dollars, 'buy', 'Buy $')
addingCategoryPerHost(dollars, 'sell', 'Sell $')

for algo in algos:
  categoryAggrByHost(numFills, 'algo' + algo, algo)
outfile.write('\n')

for algo in algos:
  addingCategoryPerHost(numFills, 'algo' + algo, algo)

for aggr in aggrs:
  categoryAggrByHost(numFills, 'aggr' + str(aggr), 'aggr ' + str(aggr))
outfile.write('\n')

for aggr in aggrs:
  for algo in algos:
    categoryAggrByHost(numFills, 'aggralgo' + str(aggr) + ' ' + algo, 'aggr ' + str(aggr) + ' ' + algo)
outfile.write('\n')

for algo in algos:
  for liqStr in liqs:
    categoryAggrByHost(numFills, 'algoliq' + algo + ' liq ' + liqStr, algo + ' liq ' + liqStr)
outfile.write('\n')

for algo in algos:
  for liqStr in liqs:
    categoryAggrByHost(dollars, 'algoliq' + algo + ' liq ' + liqStr, algo + ' liq ' + liqStr)
outfile.write('\n')

allowed = 0
disallowed = 0
trade_cfg['servers'].extend(moc_trade_cfg['servers'])
for (host,port) in trade_cfg['servers']: 
  server_num = re.findall('[0-9]+', host)[0]
  p = subprocess.Popen('scp ase@' + host + ':' + REMOTE_LOG_DIR + '/misc.log misc.rts1_' + server_num + '.log',env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  retcode = p.wait()
  if not os.path.exists('misc.rts1_' + server_num + '.log'):
    continue
  logFile = open('misc.rts1_' + server_num + '.log', 'r')
  for line in logFile:
    fields = line.split()
    if len(fields) < 5:
      continue
    if not fields[4].startswith('CapTracker'):
      continue
    allow = True
    if fields[5] == 'Disallowing':
        allow = False
        disallowed += 1
    else:
        allowed += 1

allowedPercent = 0
if (allowed + disallowed) > 0:
  allowedPercent = (100.0*allowed)/(allowed + disallowed)
else:
  print 'ERROR: allowed + disallowed = 0'
outfile.write('\nNumber of shares allowed = ' + str(allowed*100) 
              + ' (%.2f'%allowedPercent + '%)\n')
outfile.write('Number of shares disallowed = ' + str(disallowed*100) 
              + ' (%.2f'%(100-allowedPercent) + ')%\n')

outfile.close()
