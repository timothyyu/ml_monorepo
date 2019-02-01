import os
from collections import OrderedDict
import operator
import logging

from pandas import DataFrame

from cave.analyzer.cave_parameter_importance import CaveParameterImportance
from cave.html.html_helpers import figure_to_html

class CaveForwardSelection(CaveParameterImportance):

    def __init__(self,
                 pimp,
                 incumbent,
                 output_dir,
                 marginal_threshold=0.05):
        """Wrapper for parameter_importance to save the importance-object
        """

        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        super().__init__(pimp, incumbent, output_dir)

        self.parameter_importance("forward-selection")
        self.plots = [os.path.join(output_dir, fn) for fn in ["forward-selection-barplot.png", "forward-selection-chng.png"]]

    def get_plots(self):
        return self.plots

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["figure"] = self.plots
            d["tooltip"] = tooltip
        return figure_to_html(self.plots)

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(figure_to_html(self.plots)))

