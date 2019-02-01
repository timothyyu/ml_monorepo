#!/usr/bin/env python
import sys
import util
import os
import os.path

def loadOrders(dir):
    secid2orders={}
    for file in os.listdir(dir):
        if not file.startswith("orders"): continue
        temp = loadOrdersFile(dir+"/"+file)
        
        for secid,orders in temp.iteritems():
            previousOrders = secid2orders.get(secid, None)
            if previousOrders is None:
                secid2orders[secid] = orders
            else:
                previousOrders.extend(orders)
    
    return secid2orders

def loadOrdersFile(filepath):
    secid2orders = {}
    with open(filepath,"r") as file:
        for row in util.csvdict(file):
            secid = int(row["secid"])
            shares = int(row["shares"])
            price = float(row["oprice"])
            
            orders = secid2orders.get(secid, None)
            if orders is None:
                orders = []
                secid2orders[secid]=orders
            
            orders.append((shares, price))
    
    return secid2orders

def loadFillsFile(filepath):
    secid2orders = {}
    with open(filepath, "r") as file:
        for row in util.csvdict(file):
            secid = int(row["secid"])
            shares = int(row["shares"])
            price = float(row["price"])
            
            orders = secid2orders.get(secid, None)
            if orders is None:
                orders = []
                secid2orders[secid]=orders
            
            orders.append((shares, price))
    return secid2orders

def loadSimFile(filepath):
    simPnl = 0.0
    simTradingPnl = 0.0
    simTradedDollars = 0.0
    simSlippageDollars = 0.0
    with open(filepath, "r") as file:
        for row in file:
            if row.startswith("Total PnL"):
                simPnl = float(row.split(":")[1].rstrip())
            elif row.startswith("Total Trading PnL"):
                simTradingPnl = float(row.split(":")[1].rstrip())
            elif row.startswith("201"):
                simTradedDollars += float(row.split("|")[6])
                simSlippageDollars += float(row.split("|")[7])
                
    return(simPnl, simTradedDollars, simSlippageDollars, simTradingPnl)

if __name__=="__main__":
    if len(sys.argv)!=6:
        print "Use as compare_sim_orders.py <sim orders file | live orders dir> <live fills file>"
        sys.exit(1)
    
    util.set_silent()
    
    ordersFile = sys.argv[1]
    fillsFile = sys.argv[2]
    simFile = sys.argv[3]
    actualPnl = float(sys.argv[4])
    tradingPnl = float(sys.argv[5])
    
    if os.path.isdir(ordersFile):
        orders = loadOrders(ordersFile)
    else:
        orders = loadOrdersFile(ordersFile)
    fills = loadFillsFile(fillsFile)
    (simPnl, simTradedDollars, simSlippageDollars, simTradingPnl) = loadSimFile(simFile)
    
    secids = set()
    secids.update(orders.iterkeys())
    secids.update(fills.iterkeys())
    
    diffs = []
    simNotTot = 0.0
    liveNotTot = 0.0
    slipTot = 0.0
    for secid in secids:
        oo = orders.get(secid, [])
        ff = fills.get(secid, [])
        
        simNotional = 0
        simAgg = 0
        simShares = 0
        for o in oo:
            simNotional += abs(o[0]) * o[1]
            simAgg += o[0] * o[1]
            simShares += o[0]
            
        avgSimPrice = simAgg/simShares if simShares != 0 else 0
            
        liveNotional = 0
        liveAgg = 0
        liveShares = 0
        for o in ff:
            liveNotional += abs(o[0]) * o[1]
            liveAgg += o[0] * o[1]
            liveShares += o[0]
        
        avgFillPrice = liveAgg/liveShares if liveShares !=0 else 0    

        slip = (avgFillPrice - avgSimPrice) * liveShares
        
        simNotTot += simNotional
        liveNotTot += liveNotional
        slipTot += slip
            
        diffs.append((secid, simNotional, liveNotional, simAgg, liveAgg, avgSimPrice, avgFillPrice, slip))
        
    print
    print "Actual Pnl: {}".format(actualPnl)
    print "Actual to Simulation Slippage: {}".format(10000.0 * (actualPnl-simPnl)/liveNotTot)
    print "Live TradingPnl Frac: {} Sim TradingPnl Frac: {}".format(10000.0 * tradingPnl/liveNotTot, 10000.0 * simTradingPnl/simNotTot)
    print "LiveTraded: {} SimTraded: {}".format(liveNotTot, simNotTot)
    print "SimSlippageDollars: {} SimSlippageBps: {}".format(simSlippageDollars, -10000.0 * simSlippageDollars/simNotTot)
    print "Fill Slip: {}".format(slipTot)
    print 
    print "secid|sim not. $|live not. $|sim agg. $|live agg. $|sim pr|live prc|slip"
    ii = 0
    for row in sorted(diffs,key=lambda x : -abs(x[2]-x[1])):
        ii += 1
        if ii > 20: break
        print "|".join([str(x) for x in row])
    
