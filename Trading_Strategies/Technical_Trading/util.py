import pandas as pd


### out-of-sample test types = fixed, sliding, and rolling
def is_oos_data(data, type = 'sliding', n_lookback = 0, n_sliding = 0):
    n_total = len(data)
    
    data_is = []
    data_oos = []
    
    ## type = 1: single train set defined by n_lookback, single test set from n_lookback:n_total
    if type == 'fixed':
        data_is.append(data[0:(n_lookback - 1)])
        data_oos.append(data[n_lookback::])
    ## type 2: sliding insample window, defined by n_lookback and sliding forward. The test set window is defined as n_      
    if type == 'sliding':
        k = n_lookback
        while k < n_total-1 :
            data_is.append(data[0:(k - 1)])
            if (k+n_sliding) <= n_total :
                k2 = k + n_sliding - 1
            else :
                k2 = n_total - 1
            data_oos.append(data[k:k2])
            k = k2
    ## type 3: sliding insample window, defined by n_lookback and sliding forward. The test set window is defined as n_      
    if type == 'rolling':
        k = n_lookback
        while k < n_total-1 :
            data_is.append(data[(k-n_lookback):(k - 1)])
            if (k+n_sliding) <= n_total :
                k2 = k + n_sliding - 1
            else :
                k2 = n_total - 1
            data_oos.append(data[k:k2])
            k = k2   
    return data_is, data_oos