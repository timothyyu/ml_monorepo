import os
from typing import List
import logging

import numpy as np

from ConfigSpace.configuration_space import Configuration
from smac.runhistory.runhistory import RunHistory

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.utils.helpers import get_cost_dict_for_config
from cave.plot.cdf import plot_cdf
from cave.html.html_helpers import figure_to_html

class PlotECDF(BaseAnalyzer):

    def __init__(self,
                 default: Configuration,
                 incumbent: Configuration,
                 rh: RunHistory,
                 train: List[str],
                 test: List[str],
                 cutoff,
                 output_dir: str):
        """
        Plot the cumulated distribution functions for given configurations,
        plots will share y-axis and if desired x-axis.
        Saves plot to file.

        Parameters
        ----------
        default, incumbent: Configuration
            configurations to be compared
        rh: RunHistory
            runhistory to use for cost-estimations
        train, test: List[str]
            lists with corresponding instances
        cutoff: Union[None, int]
            cutoff for target algorithms, if set
        output_dir: str
            directory to save plots in

        Returns
        -------
        output_fns: List[str]
            list with paths to generated plots
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.output_dir = output_dir

        out_fn = os.path.join(output_dir, 'cdf')
        self.logger.info("... plotting eCDF")
        self.logger.debug("Plot CDF to %s_[train|test].png", out_fn)

        def prepare_data(x_data):
            """ Helper function to keep things easy, generates y_data and manages x_data-timeouts """
            x_data = sorted(x_data)
            y_data = np.array(range(len(x_data))) / (len(x_data) - 1)
            for idx in range(len(x_data)):
                if (cutoff is not None) and (x_data[idx] >= cutoff):
                    x_data[idx] = cutoff
                    y_data[idx] = y_data[idx - 1]
            return (x_data, y_data)

        # Generate y_data
        def_costs = get_cost_dict_for_config(rh, default).items()
        inc_costs = get_cost_dict_for_config(rh, incumbent).items()

        output_fns = []

        for insts, name in [(train, 'train'), (test, 'test')]:
            if insts == [None]:
                self.logger.debug("No %s instances, skipping cdf", name)
                continue
            data = [prepare_data(np.array([v for k, v in costs if k in insts])) for costs in [def_costs, inc_costs]]
            x, y = (data[0][0], data[1][0]), (data[0][1], data[1][1])
            labels = ['default ' + name, 'incumbent ' + name]
            output_fns.append(plot_cdf(x, y, labels, timeout=cutoff,
                                       out_fn=out_fn + '_{}.png'.format(name)))

        self.output_fns = output_fns

    def get_html(self, d=None, tooltip=None):
        if d is not None and self.output_fns:
            d["figure"] = self.output_fns
            d["tooltip"] = tooltip
        return figure_to_html(self.output_fns)

    def get_plots(self):
        return self.output_fns

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))
