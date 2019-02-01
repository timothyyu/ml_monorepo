import numpy as np
import logging
import unittest

from cave.utils.statistical_tests import paired_permutation, paired_t_student


class TestStatisticalTests(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestStatisticalTests")

    def test_paired_permutation(self):
        """ Testing paired permutation test. """
        rng = np.random.RandomState(42)
        a, b = rng.normal(loc=0, size=100), rng.normal(loc=0, size=100)
        result = paired_permutation(a, a, rng, 100, self.logger)
        self.assertGreater(result, 0.9999)
        result = paired_permutation(a, b, rng, 100, self.logger)
        self.assertGreater(result, 0.3)
        a, b = rng.normal(loc=-1, size=100), rng.normal(loc=1, size=100)
        result = paired_permutation(a, b, rng, 1000, self.logger)
        self.assertLess(result, 0.001)

    def test_t_student(self):
        """ Testing paired t-test. """
        rng = np.random.RandomState(42)
        a, b = rng.normal(loc=0, size=100), rng.normal(loc=0, size=100)
        result = paired_t_student(a, b, self.logger)
        self.assertGreater(result, 0.3)
        a, b = rng.normal(loc=-1, size=100), rng.normal(loc=1, size=100)
        result = paired_t_student(a, b, self.logger)
        self.assertLess(result, 0.001)
