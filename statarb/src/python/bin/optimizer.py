#!/usr/bin/env python

import sys
import numpy
import math
import openopt

import util

max_sumnot = 50.0e6
max_expnot = 0.048
max_trdnot = 1.0
max_iter = 500
#min_iter = 300
#stop_iter = 200
#stop_frac = 0.001

hard_limit = 1.02
kappa = 4.3e-5
slippage = 0.0006

num_secs = 0
num_factors = 0
stocks_ii = 0
factors_ii = 0

sec_ind = dict()
sec_ind_rev = dict()
factor_ind = dict()

positions = None
lbound = None
ubound = None
mu = None
rvar = None
advp = None
borrowRate = None
factors = None
fcov = None
numpy.set_printoptions(threshold=float('nan'))
    
#def iterfn(p):
#    # because openalg seemed to ignore maxiter randomly sometimes
#    if p.iter == 0:
#        p.user.fk = []
#    else:
#        p.user.fk.append(p.fk)
#    if p.iter >= p.user.config['min_iter']:
#        if p.fk/p.user.fk[p.iter - int(p.user.config['stop_iter']) - 1] - 1.0 < p.user.config['stop_frac']:
#            return True
#        if p.iter >= p.user.config['max_iter']:
#            return True
#    return False

def printinfo(target):
    long=0
    short=0
    diff=0
    for ii in xrange(len(target)):
        if target[ii]>=0:
            long+=target[ii]
        else:
            short-=target[ii]
        diff+=abs(target[ii]-positions[ii])
    print "Long: {:.0f}, Short: {:.0f}, Total: {:.0f}".format(long,short,long+short)
    print "Dollars traded: {:.0f}".format(diff)
    __printpointinfo("Current",positions)
    __printpointinfo("Optimum",target)

def __printpointinfo(name,target):
    loadings = numpy.dot(factors, target)
    path = target - positions
    utility1 = numpy.dot(target, mu)
    utility2 = kappa * ( numpy.dot(target * rvar, target) + numpy.dot(numpy.dot(loadings, fcov), loadings) )
    utility3 = slippageFunc(slippage, abs(path).sum())
    print "@{}: mu={:.0f}, risk={:.0f}, slip={:.0f}".format(name,utility1,utility2,utility3)

def objective(target, kappa, slippage, positions, mu, rvar, factors, fcov):
    # objective function to be minimized (negative utility)    
    loadings = numpy.dot(factors, target)
    path = target - positions

    utility = numpy.dot(target, mu)
    utility -= kappa * ( numpy.dot(target * rvar, target) + numpy.dot(numpy.dot(loadings, fcov), loadings) )
    utility -= slippageFunc(slippage, abs(path).sum())

#    print "util: {}".format(utility)
#    print target
    return utility

def slippageFunc(slippage, shares):
    return abs(slippage * shares);

# constrain <= 0
def constrain_by_capital(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target).sum() - max_sumnot
#    print "cap:{}, {}".format(ret, max_sumnot)
#    print target
    return ret

def constrain_by_exposures(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    exposures = numpy.dot(factors, target)
    ret = max(numpy.r_[lbexp - exposures, exposures - ubexp])
#    print "exp:", ret
#    print target
    return ret

def constrain_by_trdnot(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target - positions).sum() - max_trdnot_hard
#    print "trd: ", ret
    return ret

def optimize(daily):
    global max_sumnot
    
    exposures = numpy.dot(factors, positions)
    lbexp = exposures
    lbexp = numpy.minimum(lbexp, -max_expnot * max_sumnot)
    lbexp = numpy.maximum(lbexp, -max_expnot * max_sumnot * hard_limit)
    ubexp = exposures
    ubexp = numpy.maximum(ubexp, max_expnot * max_sumnot)
    ubexp = numpy.minimum(ubexp, max_expnot * max_sumnot * hard_limit)

    sumnot = abs(positions).sum()
    max_sumnot = max(max_sumnot, sumnot)
    max_sumnot = min(max_sumnot, max_sumnot * hard_limit)

    #XXX optimizer needs to move in lotsize steps
    p = openopt.NLP(goal='max', f=objective, x0=positions, lb=lbound, ub=ubound)
    p.args.f = (kappa, slippage, positions, mu, rvar, factors, fcov)
    p.c = [constrain_by_capital, constrain_by_exposures]
    
    if not daily:
        p.c.append(constrain_by_trdnot)
        
    p.args.c = (positions, max_sumnot, factors, lbexp, ubexp, max_trdnot * max_sumnot * hard_limit)
    p.ftol = 1e-7
    
    p.maxIter = max_iter
    #p.maxCPUTime = 360
    #p.maxTime = 240
    
#    config['max_iter'] = max_iter
#    config['stop_iter'] = stop_iter
#    config['min_iter'] = min_iter
#    config['stop_frac'] = stop_frac
#    p.user.config = config
#    p.callback = iterfn
    
#    p.plot = 1

#    print "pos: "
#    print positions
#    print "max_sumnot: "
#    print max_sumnot
#    print "factors: " 
#    print  factors
#    print "lbexp: " 
#    print  lbexp
#    print "ubexp: " 
#    print ubexp
#    print "max_tradenot: " 
#    print  max_trdnot
#    print "hard_limit: " 
#    print hard_limit

    r = p.solve('ralg')
    
#    r = p.solve('algencan')
    #r = p.solve('scipy_slsqp')
    #r = p.solve('scipy_lbfgsb')
    #r = p.solve('scipy_tnc')
#    r = p.solve('scipy_cobyla')
    
    #XXX need to check for small number of iterations!!!
    if r.stopcase == -1 or r.isFeasible == False:
        raise Exception("Optimization failed")

    target = r.xf
    dutil = numpy.zeros(len(target))
    dmu = numpy.zeros(len(target))
    eslip = numpy.zeros(len(target))
    for ii in range(len(target)):
        targetwo = target.copy()
        targetwo[ii] = positions[ii]
        dutil[ii] = objective(target, *p.args.f) - objective(targetwo, *p.args.f)
        trade = target[ii]-positions[ii]
        eslip[ii] = slippageFunc(slippage, trade)     
        dmu[ii] = mu[ii] * trade

    printinfo(target)

    return (target, dutil, eslip, dmu)

def init():
    global num_secs, num_factors, positions, lbound, ubound, mu, rvar, advp, borrowRate, factors, fcov, max_iter, slippage, kappa, max_sumnot, max_expnot, max_trdnot
    
    max_iter = int(config["max_iter"])
    kappa = float(config["kappa"])
    slippage = float(config["slippage"])
    max_sumnot = float(config["max_sumnot"])
    max_expnot = float(config["max_expnot"])
    max_trdnot = float(config["max_trdnot"])
    
    num_secs = int(config["num_secs"])
    num_factors = int(config["num_factors"])
    
    positions = numpy.zeros(num_secs)
    lbound = numpy.zeros(num_secs) 
    ubound = numpy.zeros(num_secs)
    mu = numpy.zeros(num_secs)
    rvar = numpy.zeros(num_secs)
    advp = numpy.zeros(num_secs)
    borrowRate = numpy.zeros(num_secs)
    factors = numpy.zeros((num_factors, num_secs))
    fcov = numpy.zeros((num_factors, num_factors)) 
    return

def getfield(field):
    try:
        ret = float(field)
        if math.isnan(ret):
            return 0.0
        return ret
    except:
        return 0.0
    
def processStock(fields):
    global stocks_ii, sec_ind, positions, lbound, ubound, my, rvar, advp, borrowRate
    sec_ind[fields[1]] = stocks_ii
    sec_ind_rev[stocks_ii] = fields[1];
    positions[stocks_ii] = getfield(fields[2])
    lbound[stocks_ii] = getfield(fields[3])
    ubound[stocks_ii] = getfield(fields[4])
    mu[stocks_ii] = getfield(fields[5])
    rvar[stocks_ii] = getfield(fields[6]) 
    advp[stocks_ii] = getfield(fields[7])
    borrowRate[stocks_ii] = getfield(fields[8])
        
    stocks_ii += 1
    return
        
def processFactor(fields):
    global factors, factor_ind, factors_ii
    factor = fields[2]
    if factor not in factor_ind:
        factor_ind[factor] = factors_ii
        factors_ii += 1
        
    sec = fields[1]
    if sec in sec_ind:
        factors[factor_ind[factor], sec_ind[fields[1]]] = getfield(fields[3])
    return

def processCov(fields):
    global fcov, factor_ind
    fcov[factor_ind[fields[1]], factor_ind[fields[2]]] = getfield(fields[3])
    fcov[factor_ind[fields[2]], factor_ind[fields[1]]] = getfield(fields[3])
    return

if __name__ == "__main__":
    print("Optimizing...")
    config = dict()
    for arg in sys.argv:
        (k,d,v) = arg.partition(":")
        print "param: ", k, v
        config[k] = v

    init();

    f = open(config["optfile"], 'r')
    for line in f:
        if line.startswith("S"):
            processStock(line.split("|"))
        elif line.startswith("F"):
            processFactor(line.split("|"))
        elif line.startswith("C"):
            processCov(line.split("|"))
        else:
            util.error("Unreadable line: " + line)
    
    daily = True
    (target, dutil, eslip, dmu) = optimize(daily)
    
    for ii in range(len(target)):
        print "T|{}|{}|{}|{}|{}|{}".format(ii, sec_ind_rev[ii], target[ii], dutil[ii], dmu[ii], eslip[ii])
    
    print "DONE"
    sys.exit()

            
