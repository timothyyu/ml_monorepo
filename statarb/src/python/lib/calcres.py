import numpy
from gzip import GzipFile

#loads a calcres into memory

def parse_calcres_line(line):
    secid, name, datatype, datetime, value, currency, born = line.split("|")
    datetime = int(datetime)
    secid = int(secid)
    if datatype == "N":
        value = float(value)
    return secid, name, datetime, value

class CalcRes(object):
    def __init__(self, filename, unifile = None):
        universe = set()
        dates = set()
        names = set()
        names0 = set()

        if unifile is not None:
            filtuni = set()
            for line in file(unifile):
                ticker, secid = line.split("|")
                filtuni.add(int(secid))

        cnt = 0
        for line in GzipFile(filename):
            cnt += 1
            if cnt > 1000: continue
            if line.startswith("FCOV"): continue
            secid, name, datetime, value = parse_calcres_line(line)
            dates.add(datetime)            
            if unifile is None or secid in filtuni:
                universe.add(secid)
                names.add(name)
            else:
                names0.add(name)

        self.universe = list(universe)
        self.universe.sort()
        self.universe_index = dict(zip(self.universe, range(len(universe))))
        self.dates = list(dates)
        self.dates.sort()
        self.dates_index = dict(zip(self.dates, range(len(dates))))
        self.names = list(names)
        self.names.sort()
        self.names_index = dict(zip(self.names, range(len(names))))
        self.names0 = list(names0)
        self.names0.sort()
        self.names0_index = dict(zip(self.names0, range(len(names0))))
        
        V = numpy.ma.masked_all((len(self.universe), len(self.dates), len(self.names)))
        V0 = numpy.ma.masked_all((len(self.dates), len(self.names0)))
        for line in GzipFile(filename):
            secid, name, datetime, value = parse_calcres_line(line)
            if unifile is None or secid in filtuni:
                V[self.universe_index[secid], self.dates_index[datetime], self.names_index[name]] = value
            else:
                V0[self.dates_index[datetime], self.names0_index[name]] = value
        self.V = V
        self.V0 = V0

    def get_universe_index(self, sec, must_exist = True):
        try:
            return self.universe_index[sec]
        except KeyError:
            if must_exist:
                raise
            else:
                return self.universe_index[0]

    def get_names_index(self, name, must_exist = True):
        try:
            return self.names_index[name]
        except KeyError:
            if must_exist:
                raise
            else:
                return []

    def get_factor_names(self):
        factor_names = set()
        for name, value in self.names0_index.iteritems():
            if name[0:2] == 'F:':
                name1, name2 = name.split('::')
                factor_names.add(name1)
                factor_names.add(name2)
        return sorted(factor_names)
