def KDJ_forward(data,x,y) :
    """
    x : periods for choosing best parameter
    y : oos 
    """
    r = pd.Series()   
    for z in range(int(math.ceil((data.shape[0]-x)/np.float(y)))):
        train_data = data[y*z:y*z+x].copy()
        test_data = data[y*z:y*z+x+y].copy()
        def f(n, m, l, s):
            returns = Backtest(train_data, KDJ(train_data, int(n), int(m), int(l), int(s))['2'])
            return pf.timeseries.sharpe_ratio(returns)
        params, info, _ = optunity.maximize(f, num_evals=50, n=[10, 20], m=[2, 5], l=[2, 5], s=[2,5])    
        signal = KDJ(test_data,n = int(params['n']), m = int(params['m']), l = int(params['l']), s = int(params['s']))    
        r = r.append(signal['2'][x:])
    return r

def f_forward(x,y):
    returns = Backtest(data[int(x):], KDJ_forward(data, int(x), int(y)))
    return pf.timeseries.sharpe_ratio(returns)
   
#params_forward, info_forward, _ = optunity.maximize(f_forward, num_evals=50, x=[200, 500], y=[1, 500]) 



from pyevolve import *
import math

def gp_add(a, b): return a+b
def gp_sub(a, b): return a-b
def gp_mul(a, b): return a*b

def qp_div(a, b): 
    if b==0: return 0
    else: return a/b
    
def qp_sqrt(a): return math.sqrt(abs(a))
def qp_exp(a): return math.exp(a)
def qp_power(a, b): return math.pow(a, b)

def qp_and(x, y): return (x and y)
def qp_or(x, y): return (x or y)
def qp_xor(x,y): return not (x or y)
def qp_gt(a, b): return (a > b)


rmse_accum = Util.ErrorAccumulator()

def eval_func(chromosome):
    global rmse_accum
    rmse_accum.reset()
    code_comp = chromosome.getCompiledCode()
    for a in xrange(0, 5):
        for b in xrange(0, 5):
            evaluated = eval(code_comp)
            target = math.sqrt((a*a)+(b*b))
            rmse_accum += (target, evaluated)
    return rmse_accum.getRMSE()

def main_run():
    genome = GTree.GTreeGP()
    genome.setParams(max_depth=4, method="ramped")
    genome.evaluator += eval_func
    
    ga = GSimpleGA.GSimpleGA(genome)
    ga.setParams(gp_terminals = ['a', 'b'], 
                 gp_function_prefix = "gp")
    ga.setMinimax(Consts.minimaxType["minimize"])
    ga.setGenerations(300)
    ga.setCrossoverRate(1.0)
    ga.setMutationRate(0.25)
    ga.setPopulationSize(800)
    
    ga.stepCallback.set(step_callback)
    ga(freq_stats=10)
    best = ga.bestIndividual()
    print best
    
def step_callback(gp_engine):
    if gp_engine.getCurrentGeneration() == 0:
        GTree.GTreeGP.writePopulationDot(gp_engine, "trees.jpg", start=0, end=1)

if __name__ == "__main__":
    main_run()
