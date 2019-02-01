import os
import logging
from typing import List, Union
from collections import OrderedDict, namedtuple
import itertools

import numpy as np

from smac.configspace import convert_configurations_to_array
from smac.epm.rf_with_instances import RandomForestWithInstances
from smac.optimizer.objective import _cost
from smac.runhistory.runhistory2epm import RunHistory2EPM4Cost
from smac.runhistory.runhistory import RunHistory
from smac.utils.util_funcs import get_types
from smac.utils.validate import Validator
from smac.optimizer.objective import average_cost

from cave.utils.io import export_bokeh
from cave.utils.hpbandster2smac import HpBandSter2SMAC
from cave.reader.configurator_run import ConfiguratorRun
from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.utils.bokeh_routines import get_checkbox

from bokeh.plotting import figure, ColumnDataSource, show
from bokeh.embed import components
from bokeh.models import HoverTool, Range1d, Legend, CustomJS
from bokeh.models.sources import CDSView
from bokeh.models.filters import GroupFilter
from bokeh.io import output_notebook
from bokeh.palettes import Dark2_5
from bokeh.layouts import column, row, widgetbox


Line = namedtuple('Line', ['name', 'time', 'mean', 'upper', 'lower', 'config'])

class CostOverTime(BaseAnalyzer):

    def __init__(self,
                 scenario,
                 output_dir,
                 rh: RunHistory,
                 runs: List[ConfiguratorRun],
                 block_epm: bool=False,
                 bohb_result=None,
                 average_over_runs: bool=True,
                 output_fn: str="performance_over_time.png",
                 validator: Union[None, Validator]=None):
        """ Plot performance over time, using all trajectory entries
            where max_time = max(wallclock_limit, the highest recorded time)

            Parameters
            ----------
            scenario: smac.scenario.scenario.Scenario
                scenario object with necessary information
            output_dir: str
                output-directory for smac-object
            rh: smac.runhistory.runhistory.RunHistory
                runhistory to use
            runs: List[ConfiguratorRun]
                list of configurator-runs
            block_epm: bool
                if block_epm, only use given runs to estimate cost
            average_over_runs: bool
                if True, average over plots. if False, all runs are treated individually with checkboxes
            output_fn: str
                path to output-png for this analysis
            validator: Validator or None
                if given, use this epm to estimate costs for the individual incumbents (EPM)
        """

        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.scenario = scenario
        self.output_dir = output_dir
        self.rh = rh
        self.runs = runs
        self.bohb_result = bohb_result
        self.block_epm = block_epm
        self.average_over_runs = average_over_runs
        self.output_fn =output_fn
        self.validator = validator

        self.logger.debug("Initialized CostOverTime with %d runs, output to \"%s\"", len(self.runs), self.output_dir)

        # Will be set during execution:
        self.plots = []                     # List with paths to '.png's

    def _get_mean_var_time(self, validator, traj, use_epm, rh):
        """
        Parameters
        ----------
        validator: Validator
            validator (smac-based)
        traj: List[Configuraton]
            trajectory to set in validator
        use_epm: bool
            validated or not (no need to use epm if validated)
        rh: RunHistory
            ??

        Returns
        -------
        mean, var

        times: List[float]
            times to plot (x-values)
        configs

        """
        # TODO kinda important: docstrings, what is this function doing?
        if validator:
            validator.traj = traj  # set trajectory
        time, configs = [], []

        if use_epm and not self.block_epm:
            for entry in traj:
                time.append(entry["wallclock_time"])
                configs.append(entry["incumbent"])
                # self.logger.debug('Time: %d Runs: %d', time[-1], len(rh.get_runs_for_config(configs[-1])))

            self.logger.debug("Using %d samples (%d distinct) from trajectory.", len(time), len(set(configs)))

            # Initialize EPM
            if validator.epm:  # not log as validator epm is trained on cost, not log cost
                epm = validator.epm
            else:
                self.logger.debug("No EPM passed! Training new one from runhistory.")
                # Train random forest and transform training data (from given rh)
                # Not using validator because we want to plot uncertainties
                rh2epm = RunHistory2EPM4Cost(num_params=len(self.scenario.cs.get_hyperparameters()), scenario=self.scenario)
                X, y = rh2epm.transform(rh)
                self.logger.debug("Training model with data of shape X: %s, y: %s", str(X.shape), str(y.shape))

                types, bounds = get_types(self.scenario.cs, self.scenario.feature_array)
                epm = RandomForestWithInstances(types=types,
                                                bounds=bounds,
                                                instance_features=self.scenario.feature_array,
                                                # seed=self.rng.randint(MAXINT),
                                                ratio_features=1.0)
                epm.train(X, y)
            config_array = convert_configurations_to_array(configs)
            mean, var = epm.predict_marginalized_over_instances(config_array)
            var = np.zeros(mean.shape)
            # We don't want to show the uncertainty of the model but uncertainty over multiple optimizer runs
            # This variance is computed in an outer loop.
        else:
            mean, var = [], []
            for entry in traj:
                #self.logger.debug(entry)
                time.append(entry["wallclock_time"])
                configs.append(entry["incumbent"])
                costs = _cost(configs[-1], rh, rh.get_runs_for_config(configs[-1]))
                # self.logger.debug(len(costs), time[-1]
                if not costs:
                    time.pop()
                else:
                    mean.append(np.mean(costs))
                    var.append(0)  # No variance over instances
            mean, var = np.array(mean).reshape(-1, 1), np.array(var).reshape(-1, 1)
        return mean, var, time, configs

    def _get_avg(self, validator, runs, rh):
        # If there is more than one run, we average over the runs
        means, times = [], []
        for run in runs:
            # Ignore variances as we plot variance over runs
            mean, _, time, _ = self._get_mean_var_time(validator, run.traj, not run.validated_runhistory, rh)
            means.append(mean.flatten())
            times.append(time)
        all_times = np.array(sorted([a for b in times for a in b]))  # flatten times
        means = np.array(means)
        times = np.array(times)
        at = [0 for _ in runs]      # keep track at which timestep each trajectory is
        m = [np.nan for _ in runs]  # used to compute the mean over the timesteps
        mean  = np.ones((len(all_times), 1)) * -1
        var, upper, lower = np.copy(mean), np.copy(mean), np.copy(mean)
        for time_idx, t in enumerate(all_times):
            for traj_idx, entry_idx in enumerate(at):
                try:
                    if t == times[traj_idx][entry_idx]:
                        m[traj_idx] = means[traj_idx][entry_idx]
                        at[traj_idx] += 1
                except IndexError:
                    pass  # Reached the end of one trajectory. No need to check it further
            # var[time_idx][0] = np.nanvar(m)
            u, l, m_ = np.nanpercentile(m, 75), np.nanpercentile(m, 25), np.nanpercentile(m, 50)
            # self.logger.debug((mean[time_idx][0] + np.sqrt(var[time_idx][0]), mean[time_idx][0],
            #                    mean[time_idx][0] - np.sqrt(var[time_idx][0])))
            # self.logger.debug((l, m_, u))
            upper[time_idx][0] = u
            mean[time_idx][0] = m_
            lower[time_idx][0] = l

        mean = mean[:, 0]
        upper = upper[:, 0]
        lower = lower[:, 0]

        # Determine clipping point for y-axis from lowest legal value
        clip_y_lower = False
        if self.scenario.run_obj == 'runtime':  # y-axis on log -> clip plot
            clip_y_lower = min(list(lower[lower > 0]) + list(mean)) * 0.8
            lower[lower <= 0] = clip_y_lower * 0.9
        #if clip_y_lower:
        #    p.y_range = Range1d(clip_y_lower, 1.2 * max(upper))

        return Line('average', all_times, mean, upper, lower, [None for _ in range(len(mean))])

    def _get_all_runs(self, validator, runs, rh):
        """
        get a list of Line-objects
        """
        lines = []
        # TODO add configs to tooltips (first to data)
        for run in runs:
            validated = True if run.validated_runhistory else False
            mean, var, time, configs = self._get_mean_var_time(validator, run.traj, not validated, run.combined_runhistory)
            mean = mean[:, 0]

            # doubling for step-effect TODO if step works with hover in bokeh, consider changing this
            time_double = [t for sub in zip(time, time) for t in sub][1:-1]
            mean_double = [t for sub in zip(mean, mean) for t in sub][:-2]
            lines.append(Line(os.path.basename(run.folder), time_double, mean_double, mean_double, mean_double, configs))
        return lines

    def _get_bohb_avg(self, validator, runs, rh):
        if len(runs) > 1 and self.bohb_result:
            # Add bohb-specific line
            # Get collective rh
            rh_bohb = RunHistory(average_cost)
            for run in runs:
                rh_bohb.update(run.combined_runhistory)
            #self.logger.debug(rh_bohb.data)
            # Get collective trajectory
            traj = HpBandSter2SMAC().get_trajectory({'' : self.bohb_result}, '', self.scenario, rh_bohb)
            #self.logger.debug(traj)
            mean, time, configs = [], [], []
            traj_dict = self.bohb_result.get_incumbent_trajectory()

            mean, _, time, configs = self._get_mean_var_time(validator, traj, False, rh_bohb)

            configs, time, budget, mean = traj_dict['config_ids'],  traj_dict['times_finished'], traj_dict['budgets'], traj_dict['losses']
            time_double = [t for sub in zip(time, time) for t in sub][1:]
            mean_double = [t for sub in zip(mean, mean) for t in sub][:-1]
            configs_double = [c for sub in zip(configs, configs) for c in sub][:-1]
            return Line('all_budgets', time_double, mean_double, mean_double, mean_double, configs_double)

    def plot(self):
        """
        Plot performance over time, using all trajectory entries.
        max_time denotes max(wallclock_limit, highest recorded time).
        """
        rh, runs, output_fn, validator = self.rh, self.runs, self.output_fn, self.validator
        # Add lines to be plotted to lines (key-values must be zippable)
        lines = []

        # Get plotting data and create CDS
        if self.bohb_result:
            lines.append(self._get_bohb_avg(validator, runs, rh))
        else:
            lines.append(self._get_avg(validator, runs, rh))
        lines.extend(self._get_all_runs(validator, runs, rh))

        data = {'name' : [], 'time' : [], 'mean' : [], 'upper' : [], 'lower' : []}
        hp_names = self.scenario.cs.get_hyperparameter_names()
        for p in hp_names:
            data[p] = []
        for line in lines:
            for t, m, u, l, c in zip(line.time, line.mean, line.upper, line.lower, line.config):
                data['name'].append(line.name)
                data['time'].append(t)
                data['mean'].append(m)
                data['upper'].append(u)
                data['lower'].append(l)
                for p in hp_names:
                    data[p].append(c[p] if (c and p in c) else 'inactive')
        source = ColumnDataSource(data=data)


        # Create plot
        x_range = Range1d(min(source.data['time']),
                          max(source.data['time']))
        y_label = 'estimated {}'.format(self.scenario.run_obj if self.scenario.run_obj != 'quality' else 'cost')
        p = figure(plot_width=700, plot_height=500, tools=['save', 'pan', 'box_zoom', 'wheel_zoom', 'reset'],
                   x_range=x_range,
                   x_axis_type='log',
                   y_axis_type='log' if self.scenario.run_obj == 'runtime' else 'linear',
                   x_axis_label='time (sec)',
                   y_axis_label=y_label,
                   title="Cost over time")


        colors = itertools.cycle(Dark2_5)
        renderers = []
        legend_it = []
        for line, color in zip(lines, colors):
            # CDSview w GroupFilter
            name = line.name
            view = CDSView(source=source, filters=[GroupFilter(column_name='name', group=str(name))])
            renderers.append([p.line('time', 'mean',
                                    source=source, view=view,
                                    line_color=color,
                                    visible=True)])

            # Add to legend
            legend_it.append((name, renderers[-1]))

            if name == 'average':
                # Fill area (uncertainty)
                # Defined as sequence of coordinates, so for step-effect double and arange accordingly ([(t0, v0), (t1, v0), (t1, v1), ... (tn, vn-1)])
                band_x = np.append(line.time, line.time[::-1])
                band_y = np.append(line.lower, line.upper[::-1])
                renderers[-1].extend([p.patch(band_x, band_y, color='#7570B3', fill_alpha=0.2)])

        # Tooltips
        tooltips = [("estimated performance", "@mean"),
                    ("at-time", "@time")]
        p.add_tools(HoverTool(renderers=[i for s in renderers for i in s], tooltips=tooltips,))
        # MAKE hovertips stay fixed in position
        #                      callback=CustomJS(code="""
        # var tooltips = document.getElementsByClassName("bk-tooltip");
        # for (var i = 0, len = tooltips.length; i < len; i ++) {
        #     tooltips[i].style.top = ""; // unset what bokeh.js sets
        #     tooltips[i].style.left = "";
        #     tooltips[i].style.bottom = "0px";
        #     tooltips[i].style.left = "0px";
        # }
        # """)))

        # TODO optional: activate different tooltips for different renderers, doesn't work properly
        #tooltips_configs = tooltips[:] + [(p, '@'+p) for p in hp_names]
        #if 'average' in [l.name for l in lines]:
        #    p.add_tools(HoverTool(renderers=[renderers[0]], tooltips=tooltips_avg   ))#, mode='vline'))

        # Wrap renderers in nested lists for checkbox-code
        checkbox, select_all, select_none = get_checkbox(renderers, [l[0] for l in legend_it])


        # Tilt tick labels and configure axis labels
        p.xaxis.major_label_orientation = 3/4

        p.xaxis.axis_label_text_font_size = p.yaxis.axis_label_text_font_size = "15pt"
        p.xaxis.major_label_text_font_size = p.yaxis.major_label_text_font_size = "12pt"
        p.title.text_font_size = "15pt"

        legend = Legend(items=legend_it,
                        location='bottom_left', #(0, -60),
                        label_text_font_size="8pt")
        legend.click_policy="hide"

        p.add_layout(legend, 'right')

        # Assign objects and save png's
        layout = row(p, column(widgetbox(checkbox, width=100),
                               row(widgetbox(select_all, width=50), widgetbox(select_none, width=50))))

        output_path = os.path.join(self.output_dir, output_fn)
        export_bokeh(p, output_path, self.logger)
        self.plots.append(output_path)

        return layout

    def get_html(self, d=None, tooltip=None):
        script, div = components(self.plot())
        if d is not None:
            d["bokeh"] = (script, div)
            d["tooltip"] = tooltip
        return script, div

    def get_plots(self):
        return self.plots

    def get_jupyter(self):
        output_notebook()
        show(self.plot())
