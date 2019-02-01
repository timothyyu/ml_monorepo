import unittest
import logging

import numpy as np
from pandas import DataFrame
from bokeh.models.widgets import DataTable

from cave.utils.bokeh_routines import array_to_bokeh_table

class TestCSV2RH(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.RandomState(42)

    def test_array_to_bokeh_table(self):
        dataframe = DataFrame(self.rng.rand(2, 3), columns=[str(i) for i in range(3)])
        self.assertTrue(isinstance(array_to_bokeh_table(dataframe), DataTable))
        # Pass logger
        self.assertTrue(isinstance(array_to_bokeh_table(dataframe, logger=logging.getLogger('test')), DataTable))
        # Pass sortable and width
        self.assertTrue(isinstance(array_to_bokeh_table(dataframe,
                                                        sortable={'1' : True, '2' : True},
                                                        width={'1' : 100, '0' : 200}),
                                   DataTable))
        # Pass invalid specifications
        self.assertRaises(ValueError, array_to_bokeh_table, dataframe, sortable={'7' : True, '2' : True})
        self.assertRaises(ValueError, array_to_bokeh_table, dataframe, width={'1' : 100, 10 : 200})


