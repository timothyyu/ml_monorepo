import ystockquote
from yahoo_finance import Share 
import regex
from argparse import ArgumentParser
from datetime import date, timedelta

#argument to get tomorrow's pivots based on today's closing price
#argument to get today's pivots based on yesterday's closing price

#Using yesterday's closing information (provided by ystockquote), this tool leverages several algorithims to calculate support and resistenance pivot points for the current day's session.  
#The formulas available are the Floor/Classic formula (-f), the Woodie's forumla (-w), and Kirk's formula (-k).  Current pricing uses the yahoo_finance module to get current pricing and insert it into 
#into the support and resistance levels (-c) when returning Floor/Class, or Woodie's forumula.
#Feature request list:
# - argument to use today's closing information instead of yesterday's closing information (calculate tomorrow's pivots after the close instead of waiting until tomorrow)
# - add current price calculation to Kirk's forumla levels and present in a manner that makes sense (e.g. where it fits in ranges?)

def last_weekday(adate):
	adate -= timedelta(days=1)
	while adate.weekday() > 4:
		adate -= timedelta(days=1)
	return adate
	
def y_high(self):
	yesterday_high = newlist[2]
	yesterday_high_float = round(float(regex.findall("\d+.\d{1,4}", yesterday_high)[0]), 3)
	return yesterday_high_float

def y_low(self):
	yesterday_low = newlist[3]
	yesterday_low_float = round(float(regex.findall("\d+.\d{1,4}", yesterday_low)[0]),3)
	return yesterday_low_float

def y_open(self):
	yesterday_open = newlist[5]
	yesterday_open_float = round(float(regex.findall("\d+.\d{1,4}", yesterday_open)[0]),3)
	return yesterday_open_float

def y_close(self):
	yesterday_close = newlist[4]
	yesterday_close_float = round(float(regex.findall("\d+.\d{1,4}", yesterday_close)[0]),3)
	return yesterday_close_float

def floor_classic(a1, a2, a3, a4):
	pp = ((pivot_high + pivot_low + pivot_close) / 3)
	r1 = (2 * pp) - pivot_low
	r2 = (pp + pivot_high - pivot_low)
	r3 = (pivot_high + 2*(pp - pivot_low))
	s1 = (2*pp) - pivot_high
	s2 = pp - pivot_high + pivot_low
	s3 = pivot_low - 2*(pivot_high - pp)
	#return pp, r1, r2, r3, s1, s2, s3
	fc_values = [pp, r1, r2, r3, s1, s2, s3]
	return fc_values

def woodie_formula(a1, a2, a3, a4):
	pp = ((pivot_high + pivot_low + 2 * pivot_close)/4)
	r1 = (2*pp) - pivot_low
	r2 = (pp + pivot_high - pivot_low)
	s1 = (2 * pp) - pivot_high
	s2 = pp - pivot_high + pivot_low
	wf_values = [pp, r1, r2, s1, s2]
	return wf_values

def kirk_formula (a1, a2, a3):
	k_pp = pivot_close
	k_r3 = int(fc_values[3])
	k_s3 = int(fc_values[6])
	k_r2 = [int(fc_values[2]), int(wf_values[2])]
	k_s2 = [int(fc_values[5]), int(wf_values[4])]
	k_s1 = [int(fc_values[4]), int(wf_values[3])]
	k_r1 = [int(fc_values[1]), int(wf_values[1])]
	k_values = [k_pp, k_r1, k_r2, k_r3, k_s1, k_s2, k_s3]
	return k_values

	
mylastweekday = last_weekday(date.today())
stringdate = mylastweekday.strftime('%Y-%m-%d')

parser = ArgumentParser(description = 'Get Pivots for ticker from ystockquote')
parser.add_argument("-t", "--ticker", required=True, dest="ticker", help="ticker for lookup", metavar="ticker")
parser.add_argument("-f", "--floor", action="store_true", dest="floor", default = False, help="using floor/classic pivots")
parser.add_argument("-w", "--woodie", action="store_true", dest="woodie", default = False, help="using woodie's forumla pivots")
parser.add_argument("-k", "--kirk", action="store_true", dest="kirk", default = False, help="using Kirk formula")
parser.add_argument("-c", "--current", action="store_true", dest="current", default = False, help="show current ticker pricing in pivot output")
args = parser.parse_args()


ticker = args.ticker
historicalinfo = ystockquote.get_historical_prices(ticker, stringdate, stringdate)
string_historical_info = str(historicalinfo)
newlist = string_historical_info.split(',')

pivot_high = y_high(newlist)
pivot_low = y_low(newlist)
pivot_open = y_open(newlist)
pivot_close = y_close(newlist)
pointer = "->"

mysymbol = Share(ticker)
myprice = float(mysymbol.get_price())


if args.floor:
	fc_values = floor_classic(pivot_high, pivot_low, pivot_open, pivot_close)
	print "Floor/Classic Pivots for %s, using closing prices from %s" %(ticker, mylastweekday)
	if (args.current) and (myprice > fc_values[3]):
		print myprice
	print "R3:", fc_values[3]
	if (args.current) and (myprice > fc_values[2]) and (myprice < fc_values[3]):
		print pointer, myprice
	print "R2:", fc_values[2]
	if (args.current) and (myprice > fc_values[1]) and (myprice < fc_values[2]):
		print pointer, myprice
	print "R1:", fc_values[1]
	if (args.current) and (myprice > fc_values[0]) and (myprice < fc_values[1]):
		print pointer, myprice
	print "Pivot Point:", fc_values[0]
	if (args.current) and (myprice > fc_values[4]) and (myprice < fc_values[0]):
		print pointer, myprice
	print "S1:", fc_values[4]
	if (args.current) and (myprice > fc_values[5]) and (myprice < fc_values[4]):
		print pointer, myprice
	print "S2:", fc_values[5]
	if (args.current) and (myprice > fc_values[6]) and (myprice < fc_values[5]):
		print pointer, myprice
	print "S3:", fc_values[6]
	if (args.current) and (myprice < fc_values[6]):
		print pointer, myprice

if args.woodie:
	wf_values = woodie_formula(pivot_high, pivot_low, pivot_open, pivot_close)
	print "Woodie's Formula Pivots for %s, using closing prices from %s" %(ticker, mylastweekday)
	if (args.current) and (myprice > wf_values[2]):
		print pointer, myprice
	print "R2:", wf_values[2]
	if (args.current) and (myprice > wf_values[1]) and (myprice < wf_values[2]):
		print pointer, myprice
	print "R1:", wf_values[1]
	if (args.current) and (myprice > wf_values[0]) and (myprice < wf_values[1]):
		print pointer, myprice
	print "Pivot Point:", wf_values[0]
	if (args.current) and (myprice > wf_values[3]) and (myprice < wf_values[0]):
		print pointer, myprice
	print "S1:", wf_values[3]
	if (args.current) and (myprice > wf_values[4]) and (myprice < wf_values[3]):
		print pointer, myprice
	print "S2:", wf_values[4]
	if (args.current) and (myprice < wf_values[4]):
		print pointer, myprice

if args.kirk:
	fc_values = floor_classic(pivot_high, pivot_low, pivot_open, pivot_close)
	wf_values = woodie_formula(pivot_high, pivot_low, pivot_open, pivot_close)
	kr_values = kirk_formula(pivot_close, fc_values, wf_values)
	print "Kirk's Pivots for %s, using closing prices from %s" %(ticker, mylastweekday)
	print "R3:", kr_values[3]
	print "R2:", kr_values[2]
	print "R1:", kr_values[1]
	print "Close:", kr_values[0]
	print "S1:", kr_values[4]
	print "S2:", kr_values[5]
	print "S3:", kr_values[6]
