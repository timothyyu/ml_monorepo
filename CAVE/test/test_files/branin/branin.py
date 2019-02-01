import numpy as np

def branin(x, inst=None, inst_spec=None):
    x1 = x[0]
    x2 = x[1]
    a = 1.
    b = 5.1 / (4.*np.pi**2)
    if inst:
        a = a * float(inst) + 1
    if inst_spec:
        b = b + float(inst_spec)
    c = 5. / np.pi
    r = 6.
    s = 10.
    t = 1. / (8.*np.pi)
    ret = a*(x2-b*x1**2+c*x1-r)**2+s*(1-t)*np.cos(x1)+s
    return ret
