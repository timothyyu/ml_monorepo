import os
import logging
from collections import OrderedDict

from pandas import DataFrame
import numpy as np

from cave.feature_analysis.feature_analysis import FeatureAnalysis
from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html

class BoxViolin(BaseAnalyzer):
    def __init__(self, output_dir, scenario, feat_names, feat_importance):
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.output_dir = output_dir

        feat_analysis = FeatureAnalysis(output_dn=output_dir,
                                        scenario=scenario,
                                        feat_names=feat_names,
                                        feat_importance=feat_importance)
        self.name_plots = feat_analysis.get_box_violin_plots()

    def get_plots(self):
        return [x[1] for x in self.name_plots]

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["tooltip"] = tooltip
            for plot_tuple in self.name_plots:
                key = "%s" % (plot_tuple[0])
                d[key] = {"figure": plot_tuple[1]}
        return figure_to_html(self.get_plots(), max_in_a_row=3, true_break_between_rows=True)

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))
