import os
import logging
from collections import OrderedDict

from pandas import DataFrame
import numpy as np

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html

class FeatureImportance(BaseAnalyzer):
    def __init__(self, pimp, output_dir):
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.output_dir = output_dir
        self.pimp = pimp

        self.feature_importance()

    def feature_importance(self):
        self.logger.info("... plotting feature importance")

        old_values = (self.pimp.forwardsel_feat_imp, self.pimp._parameters_to_evaluate, self.pimp.forwardsel_cv)
        self.pimp.forwardsel_feat_imp = True
        self.pimp._parameters_to_evaluate = -1
        self.pimp.forwardsel_cv = False

        dir_ = os.path.join(self.output_dir, 'feature_plots/importance')
        os.makedirs(dir_, exist_ok=True)
        res = self.pimp.evaluate_scenario(['forward-selection'], dir_)
        self.feat_importance = res[0]['forward-selection']['imp']

        self.plots = [os.path.join(dir_, 'forward-selection-barplot.png'),
                      os.path.join(dir_, 'forward-selection-chng.png')]
        # Restore values
        self.pimp.forwardsel_feat_imp, self.pimp._parameters_to_evaluate, self.pimp.forwardsel_cv = old_values

    def get_plots(self):
        return self.plots

    def get_table(self):
        table = DataFrame(data=list(self.feat_importance.values()), index=list(self.feat_importance.keys()), columns=["Error"])
        return table

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["tooltip"] = tooltip
            d["Table"] = {"table": self.get_table().to_html()}
            for p in self.plots:
                name = os.path.splitext(os.path.basename(p))[0]
                d[name] = {"figure": p}
        return self.get_table().to_html() + figure_to_html(self.get_plots())

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))
