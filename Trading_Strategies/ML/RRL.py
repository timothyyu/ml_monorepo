import matplotlib.pyplot as plt
from numpy import *
import numpy as np
from scipy.optimize import minimize
import pandas as pd

def cost_function(theta, *args ):
    '''
    X_n - standardized returns
    X - returns
    theta - parameter set as [1, xt, ... xt-m, Ft-1]
    miu - number of shares to buy/sell
    delta - transaction cost
    '''
    (Xn, X) = args[0]

    M = len(theta) - 2
    T = len(X) - M

    miu = 1 # buy/sell 1 share
    delta = 0.001 # 0.1% transaction cost

    Ft, dFt = update_Ft(Xn, theta)
    Ret = reward_function(X, Ft, miu, delta)
    sharpe = sharpe_ratio(Ret[M:])
    J = sharpe * -1

    A = mean(Ret[M:])
    B = mean(Ret[M:]*Ret[M:])
    dS_dA = B / float64(power(B-A*A, 1.5))
    #     print "ds-da = {f}".format(f = dS_dA)
    dS_dB =  -0.5* A / power(B-A*A, 1.5)
    #     print "ds-db = {f}".format(f = dS_dB)

    dA_dRet = np.ones(T) / float(T)
    dB_dRet = np.ones(T) * 2 * Ret[M:]  / float(T)


    dRet_dFt = np.zeros(len(Ft))
    dRet_dFtt = np.zeros(len(Ft))
    dRet_dFt[1:] = -1 * miu * delta* sign(Ft[1:] - Ft[:-1])
    dRet_dFtt[1:] = miu * X[1:] + miu * delta * sign(Ft[1:] - Ft[:-1])


    part1 = dot(dS_dA, dA_dRet) + dot(dS_dB, dB_dRet)


    a = np.dot(dRet_dFt[M:].reshape([T,1]), np.ones([1, M+2]))
    a = a * dFt[M:]
    b = np.dot(dRet_dFtt[M:].reshape([T,1]), np.ones([1, M+2]))
    b = b * dFt[M-1:-1]

    dS_dF = np.dot(part1.reshape([T,1]), np.ones([1, M+2]))

    grad = np.sum(dS_dF*(a+b), axis=0)
    grad = grad.ravel() * -1


    ''' test 2
    dRet_dFt = np.zeros([len(Ft), len(Ft)])
    dRet_dFtt = np.zeros([len(Ft), len(Ft)])
    dr_t = -1 * miu * sign(Ft[1:] - Ft[:-1])
    dr_tt = miu * Ret[1:] + miu * delta * sign(Ft[1:] - Ft[:-1])
    for i in range(len(Ft)) :
        if i < 1:
            continue
        dRet_dFt[i,i] = dr_t[i-1]
        dRet_dFtt[i,i] = dr_tt[i-1]


    part1 = dot(dS_dA, dA_dRet) + dot(dS_dB, dB_dRet)

    a = np.dot(dRet_dFt[M:, M:], dFt[M:])
    b = np.dot(dRet_dFtt[M:, M:], dFt[M-1:-1])
    grad = np.dot(part1, (a+b))
    grad = grad * -1
    '''

    return J, grad

def cost_function_ds(theta, *args ):
    '''
    X_n - standardized returns
    X - returns
    theta - parameter set as [1, xt, ... xt-m, Ft-1]
    miu - number of shares to buy/sell
    delta - transaction cost
    '''
    (Xn, X) = args[0]

    M = len(theta) - 2
    T = len(X) - M

    miu = 1 # buy/sell 1 share
    delta = 0.001 # 0.1% transaction cost

    Ft, dFt = update_Ft(Xn, theta)
    Ret, A, B, D, dD_dRt = reward_function1(X, Ft, miu, delta)
    J = D[-1] * -1
#     J = sharpe_ratio(Ret[M:])*-1


    A = mean(Ret[M:])
    B = mean(Ret[M:]*Ret[M:])
    dS_dA = B / float64(power(B-A*A, 1.5))
    #     print "ds-da = {f}".format(f = dS_dA)
    dS_dB =  -0.5* A / power(B-A*A, 1.5)
    #     print "ds-db = {f}".format(f = dS_dB)

    dA_dRet = np.ones(T) / float(T)
    dB_dRet = np.ones(T) * 2 * Ret[M:]  / float(T)


    dRet_dFt = np.zeros(len(Ft))
    dRet_dFtt = np.zeros(len(Ft))
    dRet_dFt[1:] = -1 * miu * delta* sign(Ft[1:] - Ft[:-1])
    dRet_dFtt[1:] = miu * X[1:] + miu * delta * sign(Ft[1:] - Ft[:-1])





    a = np.dot(dRet_dFt[M:].reshape([T,1]), np.ones([1, M+2]))
    a = a * dFt[M:]
    b = np.dot(dRet_dFtt[M:].reshape([T,1]), np.ones([1, M+2]))
    b = b * dFt[M-1:-1]


#     grad= np.dot(dD_dRt[M:].reshape([1, T]), (a+b))
    grad = dD_dRt[-1] * (a[-1] + b[-1])
    grad = grad.ravel() * -1



    ''' test 2
    dRet_dFt = np.zeros([len(Ft), len(Ft)])
    dRet_dFtt = np.zeros([len(Ft), len(Ft)])
    dr_t = -1 * miu * sign(Ft[1:] - Ft[:-1])
    dr_tt = miu * Ret[1:] + miu * delta * sign(Ft[1:] - Ft[:-1])
    for i in range(len(Ft)) :
        if i < 1:
            continue
        dRet_dFt[i,i] = dr_t[i-1]
        dRet_dFtt[i,i] = dr_tt[i-1]


    part1 = dot(dS_dA, dA_dRet) + dot(dS_dB, dB_dRet)

    a = np.dot(dRet_dFt[M:, M:], dFt[M:])
    b = np.dot(dRet_dFtt[M:, M:], dFt[M-1:-1])
    grad = np.dot(part1, (a+b))
    grad = grad * -1
    '''

    return J, grad

def numeric_gradient(theta, X, Xn) :
    numgrad = np.zeros(len(theta))
    pertub = np.zeros(len(theta))
    e = 1e-5
    for i in range(len(theta)) :
        pertub[i] = e
        loss1, _ = cost_function_ds(theta - pertub, [Xn, X])
        loss2, _ = cost_function_ds(theta + pertub, [Xn, X])
        print 'loss1={i}'.format(i=loss1)
        print 'loss2={i}'.format(i=loss2)
        numgrad[i] = (loss2 - loss1) / (2*e)
    return numgrad


def cost_function1(theta, *args ):
    '''
    X_n - standardized returns
    X - returns
    theta - parameter set as [1, xt, ... xt-m, Ft-1]
    miu - number of shares to buy/sell
    delta - transaction cost
    '''
    (Xn, X) = args[0]




    miu = 1 # buy/sell 1 share
    delta = 0.001 # 0.1% transaction cost

    Ft, dFt = update_Ft(Xn, theta)
    Ret, sharpe, A, B, D = reward_function(X, Ft, miu, delta)
    J = D[-1]*-1
#     print "J={j}".format(j=J)
    return J

def update_Ft(Xn, theta) :
    '''
    update_Ft: create a series of Ft(the action decision)
    based on the theta , and the input paramters
    Ft = tanh(theta * xt), where xt = [1, X1, ... Xm, Ft-1].
    '''

    M = len(theta) - 2 # theta contains M+2 factors

    Ft = np.zeros(len(Xn))
    dFt = np.zeros([len(Xn), len(theta)])
    for i in range(len(Xn)) :
        '''
        if i < M -1 :
            continue
        xt = [1] + list(Xn[i-M+1:i+1]) + [Ft[i-1]]
        Ft[i] = tanh(np.dot(xt, theta))
        dFt[i, :] = (1-Ft[i]*Ft[i])* (xt + theta[-1] * dFt[i-1, :])
        '''

        if i < M-1:
            continue
        xt = [1] + list(Xn[i-M+1:i+1]) + [Ft[i-1]]
        Ft[i] = tanh(np.dot(xt, theta))
        dFt[i, :] = (1-Ft[i]*Ft[i])* (xt + theta[-1] * dFt[i-1, :])


    return Ft, dFt






def feature_normalization(X) :
    mu = mean(X)
    sigma = std(X, ddof=1)
    Xn = (X - mu) / sigma
    return Xn

def reward_function1(X, Ft,  miu, delta):
    '''
    reward_function: calcualte R - the wealth gain during each
    decision Ft. Rt = mu * (Ft-1 * Xt - delta * abs(Ft - Ft-1))
    '''
    Ret = np.zeros(len(Ft))
    Ret[1:] = miu * (Ft[:-1] * X[1:] - delta * abs(Ft[1:] - Ft[:-1]))

    T = len(Ft)

    A = np.zeros(T)
    B = np.zeros(T)
    D = np.zeros(T)
    dD_dRt = np.zeros(T)

    seta = 0.05
    for i in range(T) :
        if i < 1:
            continue
        A[i] = A[i-1] + seta * (Ret[i] - A[i-1])
        B[i] = B[i-1] + seta * (Ret[i] * Ret[i] - B[i-1])
        D[i] = B[i-1] * (Ret[i] - A[i-1]) - 0.5 * A[i-1] * (Ret[i]*Ret[i] - B[i-1])
        D[i] = D[i] / power(B[i-1] - A[i-1]*A[i-1], 1.5)
        if isnan(D[i]) :
            D[i] = 0

        dD_dRt[i] = (B[i-1] - A[i-1]*Ret[i]) / power(B[i-1] - A[i-1]*A[i-1], 1.5)
    return Ret, A, B, seta*D, dD_dRt

def reward_function(X, Ft, miu, delta):
    Ret = np.zeros(len(Ft))
    Ret[1:] = miu * (Ft[:-1] * X[1:] - delta * abs(Ft[1:] - Ft[:-1]))

    return Ret



def sharpe_ratio(X) :
    return mean(X)/std(X)


def ARIMA_Data(k=3, alpha = 0.5, len=10000) :
    beta = np.ones(len)
    p = np.ones(len)
    eps = np.random.normal(0, 1.0, len)
    v = np.random.normal(0, 1.0, len)
    z = np.zeros(len)
    for i in range(len) :
        if i < 1:
            continue
        beta[i] = alpha * beta[i-1] + v[i]
        p[i] =  p[i-1] + beta[i-1] + k*eps[i]
        z[i] = np.exp(p[i] / (np.max(p) - np.min(p)))
    z = np.exp(p / (np.max(p) - np.min(p)))
    return z

z = ARIMA_Data(len=1000)
X = z[1:] / z[:-1] -1
plt.figure(figsize=[20,10])
plt.plot(np.cumprod(1+array(X)))

import numpy as np
from scipy.optimize import minimize



# X = X[4000:]
Xn = feature_normalization(X)

LB = 100
LF = 2
T = len(X)
M = 3
miu = 1
delta = 0.001
rho = 1

Ret = []
inRet = []
Ft = []
plt.figure(figsize=[20,10])
init_theta =  np.ones(M+2)
theta = init_theta
for i in range(T) :
    if i < (LB+M+2):
        continue
    if (i+1)%LF == 0: # time to train the data and invest
        print "i={i}".format(i=i)
        t_start = i+1 - LB -M
        t_end = i
        i_start = i+1
        i_end = i+LF

        theta = theta + np.random.normal(1,1, M+2)
        output= minimize(cost_function, theta, args=[Xn[t_start:t_end+1], X[t_start:t_end+1]], jac=True,
                         options={'xtol': 1e-5, 'disp': True})
        theta = output.x


#         e = 1
#         J0 = 0
#         #theta = init_theta
#         count = 0
#         while count < 100:
#             count += 1
#             J, g = cost_function_ds(theta, [Xn[t_start:t_end+1], X[t_start:t_end+1]])
#             e = abs(J - J0)

#             J0 = J
#             if e < 1e-8:
#                 break
#             theta = theta + rho * g
#         print "Nr={n}:J0={jj}:J={j}:e={e}".format(n=count, jj=J0, j=J, e=e)


        Ft_i, _ = update_Ft(Xn[i_start-M:i_end+1], theta)
        Ret_i = reward_function(X[i_start-M:i_end+1], Ft_i, miu, delta)

        Ft_in, _ = update_Ft(Xn[t_start:t_end+1], theta)
        Ret_in = reward_function(X[t_start:t_end+1], Ft_in, miu, delta)
        inRet = inRet + list(Ret_in)
        print "in sharpe={s}".format(s=sharpe_ratio(Ret_in))
        print "oos sharpe={s}".format(s=(Ret_i[M:]))
        Ret = Ret + list(Ret_i[M:])
        Ft = Ft + list(Ft_i[M:])


        plt.plot(np.cumprod(1+np.array(Ret)), 'g')
plt.plot(np.cumprod(1+X),'r')
#plt.plot(np.cumprod(1+X)*(Ft<0), 'ro')