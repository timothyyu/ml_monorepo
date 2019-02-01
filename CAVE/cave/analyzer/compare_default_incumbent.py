import os
import logging
from collections import OrderedDict

from pandas import DataFrame
import numpy as np

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html

class CompareDefaultIncumbent(BaseAnalyzer):
    def __init__(self, default, incumbent):
        """ Create comparison table of default and incumbent
        Removes unused parameters.

        Parameters
        ----------
        default, incumbent: Configuration
            configurations to be compared
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        # Remove unused parameters
        keys = [k for k in default.keys() if default[k] or incumbent[k]]
        default = [default[k] if default[k] is not None else "inactive" for k in keys]
        incumbent = [incumbent[k] if incumbent[k] is not None else "inactive" for k in keys]
        zipped = list(zip(keys, default, incumbent))
        # Show first parameters that changed
        same = [x for x in zipped if x[1] == x[2]]
        diff = [x for x in zipped if x[1] != x[2]]
        table = []
        if len(diff) > 0:
            table.extend([(15 * '-' + ' Changed parameters: ' + 15 * '-', 5 * '-', 5 * '-')])
            table.extend(diff)
        if len(same) > 0:
            table.extend([(15 * '-' + ' Unchanged parameters: ' + 15 * '-', 5 * '-', 5 * '-')])
            table.extend(same)
        keys, table = [k[0] for k in table], [k[1:] for k in table]
        self.table = df = DataFrame(data=table, columns=["Default", "Incumbent"], index=keys)
        self.html_table = df.to_html()

    def get_table(self):
        return self.table

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["table"] = self.html_table
            d["tooltip"] = tooltip
        return self.html_table

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))

