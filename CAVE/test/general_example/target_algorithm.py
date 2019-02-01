import sys
import csv
import numpy as np

def get_branin(param1, param2, param3, inst, rnd):
    a, b, c = inst
    b = b / (4.*np.pi**2)
    c = c / np.pi
    r = 6.
    s = 10.
    t = 1. / (8.*np.pi)
    ret = a*(param2-b*param1**2+c*param1-r)**2+s*(1-t)*np.cos(param1)+s
    ret += rnd.normal()
    ret = ret ** 2
    return ret

if __name__ == '__main__':
    print(sys.argv)
    instances = {'0': (1., 5.1, 5.)}
    with open('test/general_example/train_and_test_feat.csv', 'r') as fh:
        for row in list(csv.reader(fh))[1:]:
            instances[row[0]] = tuple([float(i) for i in row[1:]])
    instance, instance_specific, cutoff, runlength, seed = sys.argv[1:6]
    # sys.argv[6], sys.argv[8] and sys.argv[10] are the names of the target algorithm 
    # parameters (here: "-param1", "-param2")
    x = float(sys.argv[7])
    y = float(sys.argv[9])
    z = float(sys.argv[11])
    rnd = np.random.RandomState(int(seed))
    result = get_branin(x, y, z, instances[instance], rnd)
    print('Result for SMAC: SUCCESS, %f, %f, %f, %s' % (result, result, result, seed))
