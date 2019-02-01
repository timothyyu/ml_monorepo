import os
import logging
import random

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use(os.path.join(os.path.dirname(__file__), 'mpl_style'))  # noqa
from matplotlib import ticker
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.patheffects as path_efx
from matplotlib.pyplot import setp

from ConfigSpace.hyperparameters import CategoricalHyperparameter, IntegerHyperparameter, FloatHyperparameter, Constant

__author__ = "Joshua Marben"
__copyright__ = "Copyright 2017, ML4AAD"
__license__ = "3-clause BSD"
__maintainer__ = "Joshua Marben"
__email__ = "joshua.marben@neptun.uni-freiburg.de"


class ParallelCoordinatesPlotter():
    def __init__(self, config_to_cost, output_dir, cs, runtime=True):
        """ Plotting a parallel coordinates plot, visualizing the explored PCS.
        Inspired by: http://benalexkeen.com/parallel-coordinates-in-matplotlib/

        Parameters
        ----------
        config_to_cost: Dict[Configuration -> float]
            configurations to be considered for plotting mapped to estimated costs
        output_dir: str
            output-filepath
        cs: ConfigurationSpace
            configspace of this scenario
        runtime: bool
            if True, the run_objective of this configurator run is runtime-optimization, if false it's quality
        """
        self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)
        self.config_to_cost = config_to_cost
        self.output_dir = output_dir
        self.cs = cs  # type ConfigSpace.configuration_space.ConfigurationSpace
        self.runtime = runtime

        # Will be set during execution
        self.plots = []

    def _get_log_spaced_ids(self, all_configs, num_configs):
        """
        Method that produces integer indices in the logspace.
        Useful to visualize all of the best and the worst

        Parameters
        ----------
        all_configs: List[Configuration]
            list with all configs
        num_configs: int
            number of configs
        """
        # Calculate the constant between values in log-space
        ratio = np.e**(np.log(len(all_configs)) / (num_configs - 1))
        ids, i, gaps = [0], 0, []
        while len(ids) < num_configs:  # Sample until the wanted number of values is reached
            n = ratio ** i  # draw the next value on the logscale
            n_int = int(n)
            if n_int - ids[-1] < 1:  # if that value is too close to another drawn value i.e. rounded to the same int
                n_int = n_int + int((i - 1) * ratio)  # jump a few steps forward
            if gaps and n_int >= len(all_configs):  # if we overshot we have to go back to one gap and fill it with
                # values that have not been taken yet
                n_int = gaps.pop(0) + 1
            if abs(n_int - ids[-1]) > 1:
                gaps.append(n_int)
            i += 1
            if n_int != ids[-1]:  # Only necessary for the first few indices
                ids.append(n_int)
        # filter all values that are out of scope (happens sometimes)
        ids = list(filter(lambda x: x < len(all_configs), set(ids)))
        if len(all_configs) - 1 not in ids:  # in case the worst one is not plotted add it.
            ids[-1] = len(all_configs) - 1
        return ids

    def _fun(self, a, logy):
        res = np.log10(a) if logy else a
        return res

    def plot_n_configs(self, num_configs, params):
        """
        Parameters
        ----------
        num_configs: int
            number of configs to be plotted
        params: List[str]
            parameters to be plotted
        """
        all_configs = list(self.config_to_cost.keys())
        if len(all_configs) < 5:
            raise ValueError("At least five configurations necessary for parallel coordinates!")
        # Get n most run configs
        if num_configs == -1:
            num_configs = len(all_configs)
        self.logger.debug("Plotting %d configs.", min(num_configs, len(all_configs)))

        pngs = {}
        for log_cost in [False, True]:
            for log_sample in [False, True]:
                configs_to_plot = list(sorted(all_configs, key=lambda x: self._fun(self.config_to_cost[x], log_cost)))
                self.best_config_performance = self._fun(min(self.config_to_cost.values()), log_cost)
                self.worst_config_performance = self._fun(max(self.config_to_cost.values()), log_cost)

                # Determine configs to be plotted
                if num_configs < len(configs_to_plot):
                    if log_sample:
                        ids = self._get_log_spaced_ids(configs_to_plot, num_configs)
                    else:
                        ids = list(sorted(random.sample(range(len(configs_to_plot)), num_configs)))
                else:
                    ids = list(range(len(configs_to_plot)))
                # Best five and worst five always plotted
                ids[0:5] = list(range(0, 5))
                ids[-5:] = list(range(len(configs_to_plot) - 6, len(configs_to_plot) - 1))
                configs_to_plot = np.array(configs_to_plot)[ids]

                out_base = os.path.join(self.output_dir, "parallel_coordinates")
                out_ext = "_{:s}_{:s}_".format('log_cost' if log_cost else 'linear_cost',
                                               'log_sampling' if log_sample else 'uniform_sampling') + str(len(ids)) + '.png'
                out_fn = out_base + out_ext
                self.logger.debug("Saving to %s", out_fn)

                path = self._plot(configs_to_plot, params, fn=out_fn, logy=log_cost)
                pngs[('log_cost' if log_cost else 'linear_cost',
                      'log_sampling' if log_sample else 'uniform_sampling')] = path
        return_path = pngs[('log_cost', 'log_sampling')] if self.runtime else pngs[('linear_cost', 'log_sampling')]
        self.plots.append(return_path)
        return return_path

    def _plot(self, configs, params, fn=None, log_c=False, logy=False):
        """
        Parameters
        ----------
        configs: List[Configuration]
            configs to be plotted
        params: List[str]
            parameters to be plotted
        fn: str
            filename to save plot in
        log_c: bool
            whether to use log-scaled colormap
        logy: bool
            whether the cost-axis should be logscale
        Returns
        -------
        output: str
        """
        if fn is None:
            filename = os.path.join(self.output_dir, "parallel_coordinates_" + str(len(configs)) + '.png')
        else:
            filename = fn

        if len(params) < 3:
            self.logger.info("Only two parameters, skipping parallel coordinates.")
            return

        # Create dataframe with configs
        cost_str = ('log-' if logy else '') + ('runtime' if self.runtime else 'quality')
        data = []
        for conf in configs:
            conf_dict = conf.get_dictionary()
            new_entry = {}
            # Add cost-column
            new_entry[cost_str] = self._fun(self.config_to_cost[conf], logy)
            # Add parameters
            for p in params:
                # Catch key-errors (implicate unused hyperparameter)
                value = conf_dict.get(p)
                if value is None:
                    # Value is None, parameter unused # TODO
                    new_entry[p] = 0
                    continue
                param = self.cs.get_hyperparameter(p)
                if isinstance(param, IntegerHyperparameter):
                    new_entry[p] = int(value)
                elif isinstance(param, FloatHyperparameter):
                    new_entry[p] = float(value)
                elif isinstance(param, CategoricalHyperparameter):
                    new_entry[p] = param.choices.index(value)
                elif isinstance(param, Constant):
                    new_entry[p] = float(value)
                else:
                    raise RuntimeError('No rule for parametertype %s' % str(type(param)))
            data.append(pd.Series(new_entry))
        data = pd.DataFrame(data)

        # Add 'cost' to params, params serves as index for dataframe
        params = [cost_str] + params

        # Select only parameters we want to plot (specified in index)
        data = data[params]

        # Create subplots
        fig, axes = plt.subplots(1, len(params) - 1, sharey=False, figsize=(15, 5))

        # Normalize the data for each parameter, so the displayed ranges are
        # meaningful. Note that the ticklabels are set to original data.
        min_max_diff = {}
        for p in params:
            # TODO enable full parameter scale
            # hyper = self.cs.get_hyperparameter(p)
            # if isinstance(hyper, CategoricalHyperparameter):
            #    lower = 0
            #    upper = len(hyper.choices)-1
            # else:
            #    lower, upper = self.cs.get_hyperparameter(p).lower, self.cs.get_hyperparameter(p).upper
            # min_max_diff[p] = [lower, upper, upper - lower]
            # data[p] = np.true_divide(data[p] - lower, upper - lower)

            # Check if explored values are more than one
            min_max_diff[p] = [data[p].min(), data[p].max(), np.ptp(data[p])]
            if len(np.unique(data[p])) <= 1:
                self.logger.debug("%s has only one explored value (%s)", p, np.unique(data[p]))
                data[p] = np.ones(data[p].shape)
            else:
                data[p] = np.true_divide(data[p] - data[p].min(), np.ptp(data[p]))

        # setup colormap
        cm = plt.get_cmap('winter')
        scaler = colors.LogNorm if log_c else colors.Normalize
        if self.worst_config_performance < self.best_config_performance:
            normedC = scaler(vmin=self.worst_config_performance,
                             vmax=self.best_config_performance)
        else:
            normedC = scaler(vmax=self.worst_config_performance,
                             vmin=self.best_config_performance)
        scale = cmx.ScalarMappable(norm=normedC, cmap=cm)

        # Plot data
        for i, ax in enumerate(axes):  # Iterate over params
            for idx in data.index[::-1]:  # Iterate over configs
                cval = scale.to_rgba(self._fun(self.config_to_cost[configs[idx]], logy))
                cval = (cval[2], cval[0], cval[1])
                zorder = idx - 5 if idx > len(data) // 2 else len(data) - idx  # -5 to have the best on top of the worst
                alpha = (zorder / len(data)) - 0.25
                alpha = np.clip(alpha, 0, 1)
                path_effects = [path_efx.Normal()]
                if idx in [0, 1, 2, 3, 4, len(data) - 1, len(data) - 2, len(data) - 3, len(data) - 4, len(data) - 5]:
                    alpha = 1
                    path_effects = [path_efx.withStroke(linewidth=5, foreground='k')]
                #self.logger.debug(data.loc[idx, params])
                ax.plot(range(len(params)), data.loc[idx, params], color=cval,
                        alpha=alpha, linewidth=3, zorder=zorder, path_effects=path_effects)
            ax.set_xlim([i, i + 1])

        def set_ticks_for_axis(p, ax, num_ticks=10):
            minimum, maximum, param_range = min_max_diff[params[p]]
            # self.logger.debug("Ticks for parameter %s: Min %f, Max %f, Range %f", p, minimum, maximum, param_range)
            hyper = p
            if p > 0:
                # First column not a parameter, but cost...
                hyper = self.cs.get_hyperparameter(params[p])
            if isinstance(hyper, CategoricalHyperparameter):
                num_ticks = len(hyper.choices)
                step = 1
                tick_labels = hyper.choices
                norm_min = data[params[p]].min()
                norm_range = np.ptp(data[params[p]])
                if num_ticks > 1:
                    norm_step = norm_range / float(num_ticks - 1)
                    ticks = [round(norm_min + norm_step * i, 2) for i in range(num_ticks)]
                else:
                    ticks = [1]
            elif isinstance(hyper, Constant):
                ticks = [1]
                tick_labels = [hyper.value]
            else:
                step = param_range / float(num_ticks)
                if isinstance(hyper, IntegerHyperparameter):
                    tick_labels = [int(minimum + step * i) for i in
                                   range(num_ticks + 1)]
                else:
                    tick_labels = [round(minimum + step * i, 2) for i in
                                   range(num_ticks + 1)]
                norm_min = data[params[p]].min()
                norm_range = np.ptp(data[params[p]])
                norm_step = norm_range / float(num_ticks)
                ticks = [round(norm_min + norm_step * i, 2) for i in
                         range(num_ticks + 1)]
            ax.yaxis.set_ticks(ticks)
            ax.set_yticklabels(tick_labels)

        # TODO adjust tick-labels to unused ranges of parameters and maybe even log?
        plt.xticks(rotation=5)
        for p, ax in enumerate(axes):
            ax.xaxis.set_major_locator(ticker.FixedLocator([p]))
            set_ticks_for_axis(p, ax, num_ticks=6)
            ax.set_xticklabels([params[p]], rotation=5)
            setp(ax.get_yticklabels(), fontsize=15)
            setp(ax.get_xticklabels(), fontsize=15)

        # Move the final axis' ticks to the right-hand side
        ax = plt.twinx(axes[-1])
        dim = len(axes)
        ax.xaxis.set_major_locator(ticker.FixedLocator([len(params) - 2, len(params) - 1]))
        set_ticks_for_axis(dim, ax, num_ticks=6)
        ax.set_xticklabels([params[-2], params[-1]])
        ax.set_ylim(axes[-1].get_ylim())
        setp(ax.get_yticklabels(), fontsize=15)

        # Remove spaces between subplots
        plt.subplots_adjust(wspace=0)
        plt.tight_layout()
        plt.subplots_adjust(wspace=0)
        fig.savefig(filename)
        plt.close(fig)

        return filename

