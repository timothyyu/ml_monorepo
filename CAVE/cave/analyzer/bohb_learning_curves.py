import os
from collections import OrderedDict
import logging
import itertools

from bokeh.io import output_notebook
from bokeh.plotting import show, figure, ColumnDataSource
from bokeh.embed import components
from bokeh.models import HoverTool, ColorBar, Range1d, LinearColorMapper, BasicTicker, CustomJS, Slider
from bokeh.models.sources import CDSView
from bokeh.models.filters import GroupFilter
from bokeh.layouts import column, row, widgetbox
from bokeh.models.widgets import CheckboxButtonGroup, CheckboxGroup, Button, Select
from bokeh.palettes import Spectral11

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.utils.timing import timing
from cave.utils.bokeh_routines import get_checkbox

class BohbLearningCurves(BaseAnalyzer):

    def __init__(self, hp_names, result_object=None, result_path=None):
        """
        Visualize hpbandster learning curves in an interactive bokeh-plot.

        Parameters
        ----------
        hp_names: List[str]
            list with hyperparameters-names
        result_object: Result
            hpbandster-result object. must be specified if result_path is not
        result_path: str
            path to hpbandster result-folder. must contain configs.json and results.json. must be specified if result_object is not
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        try:
            from hpbandster.core.result import logged_results_to_HBS_result
            from hpbandster.core.result import extract_HBS_learning_curves
        except ImportError as err:
            self.logger.exception(err)
            raise ImportError("You need to install hpbandster (e.g. 'pip install hpbandster') to analyze bohb-results.")

        if (result_path and result_object) or not (result_path or result_object):
            raise ValueError("Specify either result_path or result_object. (currently \"%s\" and \"%s\")" % (result_path, result_object))
        elif result_path:
            result_object = logged_results_to_HBS_result(result_path)

        incumbent_trajectory = result_object.get_incumbent_trajectory()

        self.hp_names = hp_names
        self.result_object = result_object
        self.lcs = result_object.get_learning_curves(lc_extractor=extract_HBS_learning_curves)

    def plot(self, reset_times=False):
        return self._plot(self.result_object, self.lcs, self.hp_names, reset_times=reset_times)

    def _plot(self, result_object, learning_curves, hyperparameter_names, reset_times=False):
        # Extract information from learning-curve-dict
        times, losses, config_ids, = [], [], []
        for conf_id, learning_curves in learning_curves.items():
            # self.logger.debug("Config ID: %s, learning_curves: %s", str(conf_id), str(learning_curves))
            for l in learning_curves:
                if len(l) == 0:
                    continue
                tmp = list(zip(*l))
                times.append(tmp[0])
                losses.append(tmp[1])
                config_ids.append(conf_id)

        if reset_times:
            times = [np.array(ts) - ts[0] for ts in times]

        # Prepare ColumnDataSource
        data = OrderedDict([
                            ('config_id', []),
                            ('config_info', []),
                            ('times', []),
                            ('losses', []),
                            ('duration', []),
                            ('HB_iteration', []),
                            ('colors', []),
                            ('colors_performance', []),
                            ('colors_iteration', []),
                           ])
        for hp in hyperparameter_names:
            data[hp] = []

        # Populate
        id2conf = result_object.get_id2config_mapping()
        for counter, c_id in enumerate(config_ids):
            if not (len(times[counter]) == len(losses[counter])):
                raise ValueError()
            longest_run = self.get_longest_run(c_id, result_object)
            if not longest_run:
                continue
            data['config_id'].append(str(c_id))
            try:
                config_info = '\n'.join([str(k) + "=" +str(v) for k,v in sorted(id2conf[c_id]['config_info'].items())])
            except:
                config_info = 'Not Available'
            data['config_info'].append(config_info)
            data['times'].append(times[counter])
            data['losses'].append(losses[counter])
            if longest_run:
                data['duration'].append(longest_run['time_stamps']['finished'] - longest_run['time_stamps']['started'])
            else:
                data['duration'].append('N/A')
            data['HB_iteration'].append(str(c_id[0]))
            for hp in hyperparameter_names:
                try:
                    data[hp].append(id2conf[c_id]['config'][hp])
                except KeyError:
                    data[hp].append("None")
            data['colors'].append(losses[counter][-1])
            data['colors_performance'].append(losses[counter][-1])
            data['colors_iteration'].append(c_id[0])

        # Tooltips
        tooltips=[(key, '@' + key) for key in data.keys() if not key in ['times', 'duration', 'colors',
                                                                         'colors_performance', 'colors_iteration']]
        tooltips.insert(4, ('duration (sec)', '@duration'))
        hover = HoverTool(tooltips=tooltips)

        # Create sources
        source_multiline = ColumnDataSource(data=data)
        # Special source for scattering points, since times and losses for multi_line are nested lists
        scatter_data = {key : [] for key in data.keys()}
        for idx, c_id in enumerate(data['config_id']):
            for t, l in zip(data['times'][idx], data['losses'][idx]):
                scatter_data['times'].append(t)
                scatter_data['losses'].append(l)
                for key in list(data.keys()):
                    if key in ['times', 'losses']:
                        continue
                    scatter_data[key].append(data[key][idx])
        source_scatter = ColumnDataSource(data=scatter_data)

        # Color
        min_perf, max_perf = min([l[-1] for l in data['losses']]), max([l[-1] for l in data['losses']])
        min_iter, max_iter = min([int(i) for i in data['HB_iteration']]), max([int(i) for i in data['HB_iteration']])
        color_mapper = LinearColorMapper(palette=Spectral11, low=min_perf, high=max_perf)

        # Create plot
        y_axis_type = "log" if len([a for a in scatter_data['losses'] if a <= 0]) == 0 else 'linear'

        x_min, x_max = min(scatter_data['times']), max(scatter_data['times'])
        x_pad = (x_max - x_min) / 10
        x_min -= x_pad
        x_max += x_pad
        y_min, y_max = min(scatter_data['losses']), max(scatter_data['losses'])
        y_pad = (y_max - y_min) / 10
        y_min -= (y_min / 10) if y_axis_type == 'log' else y_pad  # because this must not fall below 0 if it's a logscale
        y_max += y_pad * 10 if y_axis_type == 'log' else y_pad
        p = figure(plot_height=500, plot_width=600,
                   y_axis_type=y_axis_type,
                   tools=[hover, 'save', 'pan', 'wheel_zoom', 'box_zoom', 'reset'],
                   x_axis_label='Time', y_axis_label='Quality',
                   x_range=Range1d(x_min, x_max, bounds='auto'),
                   y_range=Range1d(y_min, y_max, bounds='auto'),
                   )

        # Plot per HB_iteration, each config individually
        HB_iterations = sorted(set(data['HB_iteration']))
        HB_handles = []
        self.logger.debug("Assuming config_info to be either \"model_based_pick=True\" or \"model_based_pick=False\"")
        for it in HB_iterations:
            line_handles = []
            view = CDSView(source=source_multiline, filters=[GroupFilter(column_name='HB_iteration', group=str(it))])
            line_handles.append(p.multi_line(xs='times', ys='losses',
                                          source=source_multiline,
                                          view=view,
                                          color={'field': 'colors', 'transform': color_mapper},
                                          alpha=0.5,
                                          line_width=5,
                                      ))
            # Separate modelbased and random
            view = CDSView(source=source_scatter, filters=[GroupFilter(column_name='HB_iteration', group=str(it)),
                                                           GroupFilter(column_name='config_info',
                                                           group="model_based_pick=True")])
            line_handles.append(p.circle_x(x='times', y='losses',
                                           source=source_scatter,
                                           view=view,
                                           fill_color={'field': 'colors', 'transform': color_mapper},
                                           fill_alpha=0.5,
                                           line_color='colors',
                                           size=20,
                                      ))
            view = CDSView(source=source_scatter, filters=[GroupFilter(column_name='HB_iteration', group=str(it)),
                                                           GroupFilter(column_name='config_info',
                                                           group="model_based_pick=False")])
            line_handles.append(p.circle(x='times', y='losses',
                                         source=source_scatter,
                                         view=view,
                                         fill_color={'field': 'colors', 'transform': color_mapper},
                                         fill_alpha=0.5,
                                         line_color='colors',
                                         size=20,
                                      ))
            HB_handles.append(line_handles)

        iteration_labels = sorted(['warmstart data' if l in [-1, '-1'] else '{:02d}'.format(int(l)) for l in HB_iterations])
        self.logger.debug("iteration_labels: %s", str(iteration_labels))
        self.logger.debug("HB_iterations: %s", str(HB_iterations))

        checkbox, select_all, select_none = get_checkbox(HB_handles, iteration_labels)

        callback_color = CustomJS(args=dict(source_multiline=source_multiline,
                                            source_scatter=source_scatter,
                                            cm=color_mapper), code="""
            var data_multiline = source_multiline.data;
            var data_scatter = source_scatter.data;
            var min_perf = {0};
            var max_perf = {1};
            var min_iter = {2};
            var max_iter = {3};
            if (cb_obj.value == 'performance') {{
                data_multiline['colors'] = data_multiline['colors_performance'];
                data_scatter['colors'] = data_scatter['colors_performance'];
                cm.low = min_perf;
                cm.high = max_perf;
            }} else {{
                data_multiline['colors'] = data_multiline['colors_iteration'];
                data_scatter['colors'] = data_scatter['colors_iteration'];
                cm.low = min_iter;
                cm.high = max_iter;
            }}
            source.change.emit();
            """.format(min_perf, max_perf, min_iter, max_iter))
        select_color = Select(title="Select colors", value="performance", options = ["performance", "iteration"],
                              callback=callback_color)


        # Put it all together
        layout = column(p, row(widgetbox(select_all, select_none, width=100), widgetbox(checkbox, width=500),
                               widgetbox(select_color, width=200)))
        return layout

    def get_longest_run(self, c_id, result_object):
        all_runs =  result_object.get_runs_by_id(c_id)
        longest_run = all_runs[-1]
        while longest_run.loss is None:
            all_runs.pop()
            if len(all_runs) == 0:
                return False
            longest_run = all_runs[-1]
        return longest_run


    def get_jupyter(self):
        output_notebook()
        show(self.plot())

    def get_html(self, d=None, tooltip=None):
        script, div = components(self.plot())
        if d is not None:
            d["BOHB Learning Curves"] = {"bokeh" : (script, div), "tooltip" : tooltip}
        return script, div

