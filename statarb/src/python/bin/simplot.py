#!/usr/bin/env python

import datetime
import argparse
import matplotlib.pyplot as plt

colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
line_types = ['-', '--']

def getLineType(i):
    t = i / len(colors)   
    c = i % len(colors)
    
    return colors[c]+line_types[t]

def parseFile(path):
    x=[]
    y=[]
    
    with open(path) as file:
        for line in file:
            tokens = line.strip().split("|")
            if len(tokens) < 11:
                continue
            tokens = [xx.strip() for xx in tokens]
            if tokens[0] == "ts":
                continue
            
            date = tokens[0]
            cumpnl = float(tokens[3])
            x.append(date)
            y.append(cumpnl)
            
    return x, y

def parsePerf(start):
    x=[]
    y=[]
    
    with open("/apps/ase/reports/useq-live/various/perf.txt") as file:
        for line in file:
            tokens = line.strip().split("|")
            if len(tokens) < 8:
                continue
            tokens = [xx.strip() for xx in tokens]
            if tokens[0] == "ts":
                continue
            
            date = tokens[0]
            if date < start: continue
            cumpnl = float(tokens[3])
            x.append(date)
            y.append(cumpnl)
            
    return x, y

def getTicks(x, type = "all"):
    assert type in ("hour", "day", "month", "all")
            
    dates = []
    for date in x:
        d = datetime.datetime.strptime(date, "%Y%m%d %H:%M:%S")
        dates.append(d)
        
    positions = []
    ticks = []
    n = len(dates)
    for i in xrange(1, n):
        d1 = dates[i-1].strftime("%Y%m%d")
        d2 = dates[i].strftime("%Y%m%d")
        m1 = dates[i-1].strftime("%Y%m")
        m2 = dates[i].strftime("%Y%m")
        h1 = dates[i-1].strftime("%Y%m%d%H")
        h2 = dates[i].strftime("%Y%m%d%H")
        
        if type == "all":
            positions.append(i)
            ticks.append(dates[i].strftime("%Y%m%d %H:%M"))
        elif type == "hour" and (h1 != h2 or i == n-1 or i == 1):
            positions.append(i)
            ticks.append(dates[i].strftime("%Y%m%d %H:%M"))
        elif type == "day" and (d1 != d2 or i == n-1 or i == 1):
            positions.append(i)
            ticks.append(dates[i].strftime("%Y%m%d"))
        elif type == "month" and (m1 != m2 or i == n-1 or i == 1):
            positions.append(i)
            ticks.append(dates[i].strftime("%Y%m%d"))
    
    return positions, ticks

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", action = "store")
    parser.add_argument("forecasts", nargs="+")
    parser.add_argument('--ticks',action="store",dest="ticksType", default="all")
    parser.add_argument('--norm', action="store_const", const=True,dest="norm", default = False)
    parser.add_argument('--actual', action="store",dest="actual", default = 0)
    
    args = parser.parse_args()
    dir = args.dir
    forecasts = args.forecasts
    ticksType = args.ticksType
    normalize = args.norm
    actuals = args.actual
    
    raw_data_points = []

    if actuals > 0:
        x, y = parsePerf(actuals)
        raw_data_points.append((x,y,"actual"))
    
    for fc in forecasts:
        x, y = parseFile(dir+"/"+fc+".txt")
        raw_data_points.append((x, y, fc))
    
    #get the set of all x values
    all_xs = set()
    for x,y,fc in raw_data_points:
        all_xs.update(x)
    all_xs = sorted(all_xs)
    
    #now align the data points
    aligned_data_points = []
    for x,y,fc in raw_data_points:
        data = dict(zip(x,y))
        ya =[]
        for xa in all_xs:
            ya.append(data.get(xa, None))
        aligned_data_points.append((ya, fc))
            
    #print the lines
    for i in xrange(len(aligned_data_points)):
        y, fc = aligned_data_points[i]
        plt.plot(y, getLineType(i), label = fc)
        
    pos, ticks = getTicks(all_xs, ticksType)
    plt.xticks(pos, ticks, rotation = 70)
    for p in pos:
        plt.axvline(p, ls = '--', color = 'k')
    plt.legend(loc = 2)   
        
    plt.show()
