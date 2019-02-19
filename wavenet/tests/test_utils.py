'''Test utility functions'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import numpy as np

import wavenet.utils as utils


def test_sample_from():
    distr = np.array([
        [0.1, 0.2, 0.7],
        [0.4, 0.5, 0.1],
        [0.1, 0.1, 0.8],
        [0.9, 0.05, 0.05],
        [0.33, 0.33, 0.34],
    ])
    labels = utils.sample_from(distr)
    assert labels.shape == (5, )
    assert np.all(labels < 3)
    assert np.all(labels >= 0)
