import numpy

from ols import ols

class Fit(object):
    def __init__(self, calcres, *names):
        if len(names) == 1:
            if isinstance(names[0], str):
                names = names[0].split(' ')
            elif isinstance(names[0], list):
                names = names[0]
            else:
                assert False, 'Unknown argument type'
        assert len(names) >= 2, 'Must have at least one X variable and one Y variable'
        Xnames = names[0:-1]
        Yname = names[-1]
        print 'FITTING' + str(names)
        # grab X and Y from calcres
        X = numpy.ma.masked_all((len(calcres.universe), len(calcres.dates), len(Xnames)))
        for i in range(len(Xnames)):
            try:
                X[:,:,i] = calcres.V[:,:,calcres.names_index[Xnames[i]]].copy()
            except KeyError:
                pass
        Y = numpy.ma.masked_all((len(calcres.universe), len(calcres.dates)))
        try:
            Y = calcres.V[:, :, calcres.names_index[Yname]].copy()
        except KeyError:
            pass
        # print counts
        for i in range(len(Xnames)):
            print 'X' + str(i), Xnames[i], 'count:', X[:, :, i].count()
        print 'Y ', Yname, 'count:', Y.count()
        mask = Y.mask
        for i in range(len(Xnames)):
            mask = mask | X[:, :, i].squeeze().mask
        Y.mask = mask
        Xc = numpy.zeros([numpy.sum(mask==False), len(Xnames)])
        #X.mask = numpy.tile(mask, (1, len(Xnames)))
        for i in range(len(Xnames)):
            X[:, :, i].mask = mask
            Xc[:, i] = X[:, :, i].compressed().squeeze()
        Yc = Y.compressed()
        try:
            self.m = ols(Yc, Xc, Yname, Xnames)
            self.summary()
        except:
            pass
        self.calcres = calcres
        self.X = X
        self.Y = Y
        self.Xnames = Xnames

    def summary(self):
        self.m.summary_short()

    def outliers(self, num=5):
        error_indices = numpy.argsort(numpy.abs(self.m.e))[::-1]
        compressed_indices = numpy.transpose(numpy.nonzero(self.Y.mask==False))
        for i in range(num):
            idx = tuple(compressed_indices[error_indices[i]])
            x = self.X[idx]
            y = self.Y[idx]
            yhat = numpy.dot(self.m.x[error_indices[i]], self.m.b)
            print idx, x, y, yhat, self.m.e[error_indices[i]], self.calcres.universe[idx[0]], self.calcres.dates[idx[1]], self.calcres.dates[idx[1]]

    def save(self, file):
        pass
