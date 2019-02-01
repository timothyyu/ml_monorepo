#!/usr/bin/env python

import sys
import numpy
import math
import openopt

import util

max_sumnot = 50.0e6
max_expnot = 0.048
max_posnot = 0.0048
max_trdnot = 1.0
max_iter = 500
min_iter = 500
#min_iter = 300
#stop_iter = 200
#stop_frac = 0.001

hard_limit = 1.02
kappa = 4.3e-5

#HAND-TWEAKED PARAMETERS TO MATCH CURRENT TRADING BEHAVIOR
slipConst = 0.0000
slipCoef = 1.5e-2
slipExp = 0.5
#FITTED PARAMETERS
#slipCoef = 4e-4
#slipExp = 0.09
execFee= 0.0006

num_secs = 0
num_factors = 0
stocks_ii = 0
factors_ii = 0
zero_start = 0

sec_ind = dict()
sec_ind_rev = dict()
factor_ind = dict()

#prefix them with g_ to avoid errors
g_positions = None
g_lbound = None
g_ubound = None
g_mu = None
g_rvar = None
g_advp = None
g_borrowRate = None
g_price = None
g_factors = None
g_fcov = None
numpy.set_printoptions(threshold=float('nan'))

p=None

class Terminator():
    def __init__(self, lookback, stopThreshold, minIter):
        self.iter = 0
        self.objValues = []
        self.maxAtLookback = None
        self.lookback = lookback
        self.stopThreshold = stopThreshold
        self.minIter = minIter
        
    def __call__(self, p):
        self.iter += 1
        #infeasible points are disregarded from computations
        if p.rk <= 0:
            self.objValues.append(p.fk)
        else:
            self.objValues.append(float('inf'))
        
        #don't start checking until we have seen at least min iters
        if self.iter <= self.lookback + self.minIter:
            return False
        #only check every 10 iterations
        if self.iter % 10 != 0:
            return False
        
        #internally it works as a minimizer, so take that into account by getting the minimum values and inverting them
        #each iteration is not guaranteed to increase the obj function values.
        curr = -min(self.objValues[-self.lookback:-1])
        prev = -min(self.objValues[0:(-self.lookback -1)])
        
        if numpy.isinf(prev):
            print "Haven't found a feasible point yet"
            return False
        elif numpy.isinf(curr):
            print "We are probably diverging, but we are staying the course for a huge comeback"
            return False
        
        if self.iter % 10 == 0:
            print "Current improvement after {} iterations is {}".format(self.lookback, float(curr-prev))
        if curr - prev < self.stopThreshold:
            print "Current improvement after {} iterations is {}".format(self.lookback, float(curr-prev))
            return True
        else:
            return False
        

def printinfo(target, kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info):
    clong=0
    cshort=0
    tlong=0
    tshort=0
    diff=0
    for ii in xrange(len(positions)):
        if positions[ii]>=0:
            clong+=positions[ii]
        else:
            cshort-=positions[ii]
    for ii in xrange(len(target)):
        if target[ii]>=0:
            tlong+=target[ii]
        else:
            tshort-=target[ii]
        diff+=abs(target[ii]-positions[ii])
    print "[CURRENT] Long: {:.0f}, Short: {:.0f}, Total: {:.0f}".format(clong,cshort,clong+cshort)
    print "[TARGET]  Long: {:.0f}, Short: {:.0f}, Total: {:.0f}".format(tlong,tshort,tlong+tshort)
    print "Dollars traded: {:.0f}".format(diff)
    __printpointinfo("Current",positions,  kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info)
    __printpointinfo("Optimum",target,  kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info)

def __printpointinfo(name,target, kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    loadings = numpy.dot(factors, target)+untradeable_loadings
    utility1 = numpy.dot(target, mu) + untradeable_mu
    utility2 = kappa * ( untradeable_rvar + numpy.dot(target * rvar, target) + numpy.dot(numpy.dot(loadings, fcov), loadings) )
    utility3 = slippageFuncAdv(target, positions, advp, slipConst, slipCoef)
    utility4 = costsFunc(target, positions, brate, price, execFee)
    print "@{}: total={:.0f}, mu={:.0f}, risk={:.0f}, slip={:.0f}, costs={:.2f}, ratio={:.3f}".format(name,utility1-utility2-utility3-utility4, utility1,utility2,utility3,utility4,utility1/utility2)

def slippageFuncAdv(target, positions, advp, slipConst, slipCoef):
    newpos_abs = abs(target-positions)
    slip = (slipConst + slipCoef*(newpos_abs / advp)**slipExp) * newpos_abs
    return slip.sum()

def slippageFunc_grad(target, positions, advp, slipConst, slipCoef):
    newpos = target-positions
    return (slipConst + slipCoef*(1+slipExp)*(abs(newpos)/advp)**slipExp) * numpy.sign(newpos)

def costsFunc(target, positions, brate, price, execFee):
    costs = execFee * numpy.dot(1.0/price, abs(target - positions))
    #ATTENTION! borrow costs are negative, negative times negative gives a positive cost
    costs += numpy.dot(brate, numpy.minimum(0.0, target))
    return costs

def costsFunc_grad(target, positions, brate, price, execFee):
    grad = execFee * numpy.sign(target - positions) / price
    for i in xrange(len(grad)):
        #ATTENTION!  borrow costs are negative, derivative is negative (more positive position, lower costs)
        if target[i] <=0 : grad[i] += brate[i]
    return grad

def objective(target, kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    # objective function to be minimized (negative utility)    
    loadings = numpy.dot(factors, target) + untradeable_loadings

    utility = 0
    utility += numpy.dot(target, mu) + untradeable_mu
    utility -= kappa * (untradeable_rvar + numpy.dot(target * rvar, target) + numpy.dot(numpy.dot(loadings, fcov), loadings) )
    utility -= slippageFuncAdv(target, positions, advp, slipConst, slipCoef)
    utility -= costsFunc(target, positions, brate, price, execFee)

    return utility

def objective_grad(target, kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, brate, price, execFee, untradeable_info):
    untradeable_mu, untradeable_rvar, untradeable_loadings = untradeable_info[0], untradeable_info[1], untradeable_info[2]
    
    F = factors
    Ft = numpy.transpose(F)
    grad = numpy.zeros(len(target))
    grad += mu
    grad -= 2 * kappa * (rvar * target + numpy.dot(Ft, numpy.dot(fcov, numpy.dot(F, target) + untradeable_loadings)))
    grad -= slippageFunc_grad(target,positions,advp,slipConst,slipCoef)
    grad -= costsFunc_grad(target, positions, brate, price, execFee)
    return grad

# constrain <= 0
def constrain_by_capital(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target).sum() - max_sumnot
    return ret

def constrain_by_capital_grad(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    return numpy.sign(target)

#def constrain_by_exposures(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
#    exposures = numpy.dot(factors, target)
#    ret = max(numpy.r_[lbexp - exposures, exposures - ubexp])
#    return ret

### UGH this is ignored!
def constrain_by_trdnot(target, positions, max_sumnot, factors, lbexp, ubexp, max_trdnot_hard):
    ret = abs(target - positions).sum() - max_trdnot_hard
    return ret

def setupProblem(positions, mu, rvar, factors, fcov, advp, borrowRate, price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, zero_start):
#def setupProblem(zero_start, lb, ub, Ac, bc, lbexp, ubexp, m_sumnot): 
    #XXX optimizer needs to move in lotsize steps
    if zero_start > 0: p = openopt.NLP(goal='max', f=objective, df=objective_grad, x0=numpy.zeros(len(positions)), lb=lb, ub=ub, A=Ac, b=bc)
    else: p = openopt.NLP(goal='max', f=objective, df=objective_grad, x0=positions, lb=lb, ub=ub, A=Ac, b=bc)
    p.args.f = (kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, borrowRate, price, execFee, untradeable_info)
    p.args.df = (kappa, slipConst, slipCoef, positions, mu, rvar, factors, fcov, advp, borrowRate, price, execFee, untradeable_info)
    p.c = [constrain_by_capital]
    p.dc = [constrain_by_capital_grad]
    p.args.c = (positions, sumnot, factors, lbexp, ubexp, sumnot)
    p.args.dc = (positions, sumnot, factors, lbexp, ubexp, sumnot)
    p.ftol = 1e-6
    p.maxFunEvals = 1e9
    p.maxIter = max_iter
    p.minIter = min_iter
    #p.callback = Terminator(50, 1, p.minIter)
    
    return p

def optimize(daily):
    global p
    
    tradeable, untradeable = getUntradeable()
    
    t_num_secs = len(tradeable)
    t_positions = numpy.copy(g_positions[tradeable])
    t_factors = numpy.copy(g_factors[:, tradeable])
    t_lbound = numpy.copy(g_lbound[tradeable])
    t_ubound = numpy.copy(g_ubound[tradeable])
    t_mu = numpy.copy(g_mu[tradeable])
    t_rvar = numpy.copy(g_rvar[tradeable])
    t_advp = numpy.copy(g_advp[tradeable])
    t_borrowRate = numpy.copy(g_borrowRate[tradeable])
    t_price = numpy.copy(g_price[tradeable]) 

    u_positions = numpy.copy(g_positions[untradeable])
    u_factors = numpy.copy(g_factors[:, untradeable])
    u_mu = numpy.copy(g_mu[untradeable])
    u_rvar = numpy.copy(g_rvar[untradeable])
        
    exposures = numpy.dot(g_factors, g_positions)
    lbexp = exposures
    lbexp = numpy.minimum(lbexp, -max_expnot * max_sumnot)
    lbexp = numpy.maximum(lbexp, -max_expnot * max_sumnot * hard_limit)
    ubexp = exposures
    ubexp = numpy.maximum(ubexp, max_expnot * max_sumnot)
    ubexp = numpy.minimum(ubexp, max_expnot * max_sumnot * hard_limit)
    #offset the lbexp and ubexp by the untradeable positions
    untradeable_exposures = numpy.dot(u_factors, u_positions)
    lbexp -= untradeable_exposures
    ubexp -= untradeable_exposures

    sumnot = abs(g_positions).sum()
    sumnot = max(sumnot, max_sumnot)
    sumnot = min(sumnot, max_sumnot * hard_limit)
    #offset sumnot by the untradeable positions
    sumnot -= abs(u_positions).sum()

    lb = numpy.maximum(t_lbound, -max_posnot * max_sumnot)
    ub = numpy.minimum(t_ubound, max_posnot * max_sumnot)
        
    #exposure constraints
    Ac = numpy.zeros((2 * num_factors, t_num_secs))
    bc = numpy.zeros(2 * num_factors)
    for i in xrange(num_factors):
        for j in xrange(t_num_secs):
            Ac[i, j] = t_factors[i, j]
            Ac[num_factors + i, j] = -t_factors[i, j]
        bc[i] = ubexp[i]
        bc[num_factors + i] = -lbexp[i]

    untradeable_mu = numpy.dot(u_mu, u_positions)
    untradeable_rvar = numpy.dot(u_positions * u_rvar, u_positions)
    untradeable_loadings = untradeable_exposures
    untradeable_info = (untradeable_mu, untradeable_rvar, untradeable_loadings) 

    p = setupProblem(t_positions, t_mu, t_rvar, t_factors, g_fcov, t_advp, t_borrowRate, t_price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, zero_start)
    r = p.solve('ralg')
    
    #XXX need to check for small number of iterations!!!
    if (r.stopcase == -1 or r.isFeasible == False) and zero_start > 0:
        #try again with zero_start = 0
        p = setupProblem(t_positions, t_mu, t_rvar, t_factors, g_fcov, t_advp, t_borrowRate, t_price, lb, ub, Ac, bc, lbexp, ubexp, untradeable_info, sumnot, 0)
        r = p.solve('ralg')
    
    if (r.stopcase == -1 or r.isFeasible == False):
        raise Exception("Optimization failed")

    #the target is the zipping of the opt result and the untradeable securities
    target = numpy.zeros(num_secs)
    opt = numpy.array(r.xf)
    targetIndex = 0
    optIndex = 0
    tradeable = set(tradeable)
    while targetIndex < num_secs:
        if targetIndex in tradeable:
            target[targetIndex] = opt[optIndex]
            optIndex += 1
        else:
            target[targetIndex] = g_positions[targetIndex]
        targetIndex += 1
            
    g_params = [kappa, slipConst, slipCoef, g_positions, g_mu, g_rvar, g_factors, g_fcov, g_advp, g_borrowRate, g_price, execFee, (0.0,0.0, numpy.zeros_like(untradeable_loadings))]
    dutil = numpy.zeros(len(target))
    dutil2 = numpy.zeros(len(target))
    dmu = numpy.zeros(len(target))
    eslip = numpy.zeros(len(target))
    costs = numpy.zeros(len(target))
    for ii in range(len(target)):
        targetwo = target.copy()
        targetwo[ii] = g_positions[ii]
        dutil[ii] = objective(target, *g_params) - objective(targetwo, *g_params)
        trade = target[ii]-g_positions[ii]
        eslip[ii] = slippageFuncAdv(target[ii], g_positions[ii], g_advp[ii], slipConst, slipCoef)
        costs[ii] = costsFunc(target, g_positions, g_borrowRate, g_price, execFee) - costsFunc(targetwo, g_positions, g_borrowRate, g_price, execFee)      
        dmu[ii] = g_mu[ii] * trade

        positions2 = g_positions.copy()
        positions2[ii] = target[ii]
        dutil2[ii] = objective(positions2, *g_params) - objective(g_positions, *g_params)

    printinfo(target, *g_params)

    return (target, dutil, eslip, dmu, costs, dutil2)

def init():
    global num_secs, num_factors, g_positions, g_lbound, g_ubound, g_mu, g_rvar, g_advp, g_borrowRate, g_price, g_factors, g_fcov, max_iter, slipConst, slipCoef, kappa, max_sumnot, max_expnot, max_trdnot, zero_start, min_iter, max_posnot
    
    min_iter = int(config["min_iter"])
    max_iter = int(config["max_iter"])
    kappa = float(config["kappa"])
    slipConst = float(config["slipConst"])
    slipCoef = float(config["slipCoef"])
    max_sumnot = float(config["max_sumnot"])
    max_expnot = float(config["max_expnot"])
    max_trdnot = float(config["max_trdnot"])
    max_posnot = float(config.get("max_posnot", 1.0))
    
    num_secs = int(config["num_secs"])
    num_factors = int(config["num_factors"])
    if "zero_start" in config: 
        zero_start = int(config["zero_start"])
    
    g_positions = numpy.zeros(num_secs)
    g_lbound = numpy.zeros(num_secs) 
    g_ubound = numpy.zeros(num_secs)
    g_mu = numpy.zeros(num_secs)
    g_rvar = numpy.zeros(num_secs)
    g_advp = numpy.zeros(num_secs)
    g_borrowRate = numpy.zeros(num_secs)
    g_price = numpy.zeros(num_secs)
    g_factors = numpy.zeros((num_factors, num_secs))
    g_fcov = numpy.zeros((num_factors, num_factors)) 
    return

def getfield(field):
    try:
        ret = float(field)
        if math.isnan(ret):
            return 0.0
        return ret
    except:
        return 0.0
 
def getfield2(field):
    try:
        ret = float(field)
        if math.isnan(ret):
            return 1.0
        return ret
    except:
        return 1.0 
    
    
def processStock(fields):
    global stocks_ii, sec_ind, g_positions, g_lbound, g_ubound, g_mu, g_rvar, g_advp, g_borrowRate, g_price
    sec_ind[fields[1]] = stocks_ii
    sec_ind_rev[stocks_ii] = fields[1];
    g_positions[stocks_ii] = getfield(fields[2])
    g_lbound[stocks_ii] = getfield(fields[3])
    g_ubound[stocks_ii] = getfield(fields[4])        
    g_mu[stocks_ii] = getfield(fields[5])
    g_rvar[stocks_ii] = getfield(fields[6]) 
    g_advp[stocks_ii] = getfield2(fields[7])
    g_borrowRate[stocks_ii] = getfield(fields[8])
    g_price[stocks_ii] = getfield(fields[9])    
        
    stocks_ii += 1
    return
        
def processFactor(fields):
    global g_factors, factor_ind, factors_ii
    factor = fields[2]
    if factor not in factor_ind:
        factor_ind[factor] = factors_ii
        factors_ii += 1
        
    sec = fields[1]
    if sec in sec_ind:
        g_factors[factor_ind[factor], sec_ind[fields[1]]] = getfield(fields[3])
    return

def processCov(fields):
    global g_fcov, factor_ind
    g_fcov[factor_ind[fields[1]], factor_ind[fields[2]]] = getfield(fields[3])
    g_fcov[factor_ind[fields[2]], factor_ind[fields[1]]] = getfield(fields[3])
    return

def getUntradeable():
    untradeable = []
    tradeable = []

    for ii in xrange(num_secs):
        if abs(g_lbound[ii] - g_ubound[ii]) < 10:
            untradeable.append(ii)
        else:
            tradeable.append(ii)
            
    return tradeable, untradeable

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
    f.close()
    
    daily = True
    (target, dutil, eslip, dmu, costs, dutil2) = optimize(daily)
    
    for ii in range(len(target)):
        print "T|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(ii, sec_ind_rev[ii], target[ii], dutil[ii], dmu[ii], eslip[ii], costs[ii], 0.0, dutil2[ii])

    print "DONE"
    sys.exit()
    
