#!/usr/bin/env python 

from util import *
from regress import *
from loaddata import *

start = dateparser.parse("20110101")
end = dateparser.parse("20130101")
factor = 'growth'

plt.figure()
df = load_factor_cache(start, end)
df = df.unstack()
df.columns = df.columns.droplevel(0)
df[factor].cumsum().plot()
plt.savefig(factor + ".png")


