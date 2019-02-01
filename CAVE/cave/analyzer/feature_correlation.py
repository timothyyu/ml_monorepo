import os
import logging

from pandas import DataFrame
import numpy as np

from cave.feature_analysis.feature_analysis import FeatureAnalysis
from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html

class FeatureCorrelation(BaseAnalyzer):
    def __init__(self, output_dir, scenario, feat_names, feat_importance):
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.output_dir = output_dir

        self.feat_analysis = FeatureAnalysis(output_dn=output_dir,
                                             scenario=scenario,
                                             feat_names=feat_names,
                                             feat_importance=feat_importance)

        self.feat_analysis.correlation_plot()
        self.correlation_plot = self.feat_analysis.correlation_plot(imp=False)

    def get_plots(self):
        return [self.correlation_plot]

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["figure"] = self.correlation_plot
            d["tooltip"] = tooltip
        return figure_to_html(self.get_plots())

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))
