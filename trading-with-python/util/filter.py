import numpy as np

def movingaverage(interval, window_size=14, pad=True):
    ''' padded moving average '''
    window = np.ones(int(window_size))/float(window_size)
    ma= np.convolve(interval, window, 'same')
    
    # pad the end properly
    if pad:
        w = window_size
        x = np.array(interval)
        n = len(ma)
        start = n-w
        # padding end
        for i in range(start, start+w):
            seq=x[i-w:i]
            ma[i]=seq.sum()/len(seq)
        # padding begining
        for i in range(w):
            seq=x[i-w:i]
            ma[i]=seq.sum()/len(seq)

    return ma
