from distutils.core import setup
from Cython.Build import cythonize

import numpy as np   

setup(
    name = 'opt app',
    ext_modules = cythonize("opt.pyx"),
    include_dirs = [np.get_include()],
)
