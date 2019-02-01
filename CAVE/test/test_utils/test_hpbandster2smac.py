import os
import numpy as np
import csv
import unittest

from cave.utils.hpbandster2smac import HpBandSter2SMAC

class TestHpbandster2Smac(unittest.TestCase):

    def setUp(self):
        rng = np.random.RandomState(42)
        self.path_to_result_mixed_categorical_pcs = "test/test_utils/hpbandster2smac_files/mixed_categorical_pcs/"
        self.path_to_result_mixed_categorical_json = "test/test_utils/hpbandster2smac_files/mixed_categorical_json/"
        self.path_to_result_mixed_categorical_missing = "test/test_utils/hpbandster2smac_files/mixed_categorical_missing/"

    def test_mixed_categorical(self):
        """ Having ints and bools as categoricals """
        try:
            hpbandster2smac = HpBandSter2SMAC()
            hpbandster2smac.convert(self.path_to_result_mixed_categorical_json)
            hpbandster2smac.convert(self.path_to_result_mixed_categorical_pcs)
            # Missing configfile
            self.assertRaises(ValueError, hpbandster2smac.convert, self.path_to_result_mixed_categorical_missing)
        except ImportError:
            pass

