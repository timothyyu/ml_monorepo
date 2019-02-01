

import numpy as np
import pandas as pd
import os
import glob
import re
import time
import datetime
import itertools

import matplotlib.pyplot as plt



filename = 'Sine_Long.csv'
print("Plotting Input file: ",filename)

# load dataframes and reindex
Xdf_loc = pd.read_csv(filename, sep=" ", header = None,)

# print(Xdf_loc.iloc[:3])

Xdf_loc['Milliseconds'] = Xdf_loc[0]

plt.figure()

Xdf_loc[1].plot()

plt.show()
