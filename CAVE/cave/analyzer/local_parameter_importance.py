import os
from collections import OrderedDict
import operator
import logging

from pandas import DataFrame

from cave.analyzer.cave_parameter_importance import CaveParameterImportance
from cave.html.html_helpers import figure_to_html

class LocalParameterImportance(CaveParameterImportance):

    def __init__(self,
                 pimp,
                 incumbent,
                 output_dir,
                 marginal_threshold=0.05):
        """Wrapper for parameter_importance to save the importance-object
        """

        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        super().__init__(pimp, incumbent, output_dir)

        self.parameter_importance("lpi")
        self.plots = OrderedDict([])
        for p, i in [(k, v) for k, v in sorted(self.param_imp['lpi'].items(),
                     key=operator.itemgetter(1), reverse=True)]:
            self.plots[p] = os.path.join(self.output_dir, 'lpi', p + '.png')

    def get_plots(self):
        return list(self.plots.values())

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["tooltip"] = tooltip
            for param, plot in self.plots.items():
                d[param] = {"figure": plot}
        return figure_to_html(self.get_plots())

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(figure_to_html(self.get_plots(), max_in_a_row=3, true_break_between_rows=True)))

