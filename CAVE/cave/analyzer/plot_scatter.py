import os
import logging
from typing import List, Union

import numpy as np

from ConfigSpace.configuration_space import Configuration
from smac.runhistory.runhistory import RunHistory

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.plot.scatter import plot_scatter_plot
from cave.utils.helpers import get_cost_dict_for_config
from cave.html.html_helpers import figure_to_html

class PlotScatter(BaseAnalyzer):

    def __init__(self,
                 default: Configuration,
                 incumbent: Configuration,
                 rh: RunHistory,
                 train: List[str],
                 test: Union[List[str], None],
                 run_obj: str,
                 cutoff,
                 output_dir: int):
        """
        Creates a scatterplot of the two configurations on the given set of instances.
        Saves plot to file.

        Parameters
        ----------
        default, incumbent: Configuration
            configurations to be compared
        rh: RunHistory
            runhistory to use for cost-estimations
        output_dir: str
            output directory

        Returns
        -------
        output_fns: List[str]
            list with paths to generated plots
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        out_fn_base = os.path.join(output_dir, 'scatter_')
        self.logger.info("... plotting scatter")
        self.logger.debug("Plot scatter to %s[train|test].png", out_fn_base)

        metric = run_obj
        timeout = cutoff
        labels = ["default {}".format(run_obj), "incumbent {}".format(run_obj)]

        def_costs = get_cost_dict_for_config(rh, default).items()
        inc_costs = get_cost_dict_for_config(rh, incumbent).items()

        out_fns = []
        for insts, name in [(train, 'train'), (test, 'test')]:
            if insts == [None]:
                self.logger.debug("No %s instances, skipping scatter", name)
                continue
            default = np.array([v for k, v in def_costs if k in insts])
            incumbent = np.array([v for k, v in inc_costs if k in insts])
            min_val = min(min(default), min(incumbent))
            out_fn = out_fn_base + name + '.png'
            out_fns.append(plot_scatter_plot((default,), (incumbent,), labels, metric=metric,
                           min_val=min_val, max_val=timeout, out_fn=out_fn))
        self.output_fns = out_fns

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
