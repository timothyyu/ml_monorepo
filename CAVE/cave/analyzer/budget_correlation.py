import os
import logging
from collections import OrderedDict
import warnings

import numpy as np
from pandas import DataFrame
from typing import List
import scipy

from ConfigSpace.configuration_space import Configuration
from smac.runhistory.runhistory import RunHistory
from smac.scenario.scenario import Scenario

from bokeh.models import ColumnDataSource, CustomJS, Range1d
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.embed import components
from bokeh.plotting import show, figure
from bokeh.io import output_notebook
from bokeh.layouts import column
from bokeh.transform import jitter

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.utils.helpers import get_cost_dict_for_config, get_timeout, combine_runhistories
from cave.utils.statistical_tests import paired_permutation, paired_t_student
from cave.utils.timing import timing

class BudgetCorrelation(BaseAnalyzer):

    def __init__(self,
                 runs):
        """
        Parameters
        ----------
        incumbents: List[Configuration]
            incumbents per budget, assuming ascending order
        budget_names: List[str]
            budget-names as strings
        epm_rhs: List[RunHistory]
            estimated runhistories for budgets, same length and order as incumbents"""
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.runs = runs

        # To be set
        self.dataframe = None

    def _get_table(self, runs):
        table = []
        for b1 in runs:
            table.append([])
            for b2 in runs:
                configs = set(b1.combined_runhistory.get_all_configs()).intersection(set(b2.combined_runhistory.get_all_configs()))
                costs = list(zip(*[(b1.combined_runhistory.get_cost(c), b2.combined_runhistory.get_cost(c)) for c in configs]))
                rho, p = scipy.stats.spearmanr(costs[0], costs[1])
                # Differentiate to generate upper diagonal
                if runs.index(b2) < runs.index(b1):
                    table[-1].append("")
                else:
                    table[-1].append("{:.2f} ({} samples)".format(rho, len(costs[0])))

        budget_names = [os.path.basename(run.folder) for run in runs]
        return DataFrame(data=table, columns=budget_names, index=budget_names)

    def plot(self):
        """Create table and plot that reacts to selection of cells by updating the plotted data to visualize
        correlation."""
        return self._plot(self.runs)

    def _plot(self, runs):
        """Create table and plot that reacts to selection of cells by updating the plotted data to visualize correlation.

        Parameters
        ----------
        runs: List[ConfiguratorRun]
            list with runs (budgets) to be compared
        """
        df = self._get_table(runs)
        # Create CDS from pandas dataframe
        columns = list(df.columns.values)
        data = dict(df[columns])
        data["Budget"] = df.index.tolist()
        table_source = ColumnDataSource(data)
        # Create bokeh-datatable
        columns = [TableColumn(field='Budget', title="Budget", sortable=False, width=20)] + [
                   TableColumn(field=header, title=header, default_sort='descending', width=10) for header in columns
                  ]
        bokeh_table = DataTable(source=table_source, columns=columns, index_position=None, sortable=False,
                               height=20 + 30 * len(data["Budget"]))

        # Create CDS for scatter-plot
        all_configs = set([a for b in [run.original_runhistory.get_all_configs() for run in runs] for a in b])
        data = {os.path.basename(run.folder) : [run.original_runhistory.get_cost(c) if c in
                                                run.original_runhistory.get_all_configs() else
                                                None for c in all_configs] for run in runs}
        data['x'] = []
        data['y'] = []

        with warnings.catch_warnings(record=True) as list_of_warnings:
            # Catch unmatching column lengths warning
            warnings.simplefilter('always')
            scatter_source = ColumnDataSource(data=data)
            for w in list_of_warnings:
                self.logger.debug("During budget correlation a %s was raised: %s", str(w.category), w.message)

        # Create figure and dynamically updating plot (linked with table)
        min_val = min([min([v for v in val if v]) for val in data.values() if len(val) > 0])
        max_val = max([max([v for v in val if v]) for val in data.values() if len(val) > 0])
        padding = (max_val - min_val) / 10  # Small padding to border (fraction of total intervall)
        min_val -= padding
        max_val += padding
        p = figure(plot_width=400, plot_height=400,
                   match_aspect=True,
                   y_range=Range1d(start=min_val, end=max_val, bounds=(min_val, max_val)),
                   x_range=Range1d(start=min_val, end=max_val, bounds=(min_val, max_val)),
                   x_axis_label='budget', y_axis_label='budget')
        p.circle(x='x', y='y',
                 #x=jitter('x', 0.1), y=jitter('y', 0.1),
                 source=scatter_source, size=5, color="navy", alpha=0.5)

        code = 'var budgets = ' + str(list(df.columns.values)) + ';'
        code += 'console.log(budgets);'
        code += """
        try {
            // This first part only extracts selected row and column!
            var grid = document.getElementsByClassName('grid-canvas')[0].children;
            var row = '';
            var col = '';
            for (var i=0,max=grid.length;i<max;i++){
                if (grid[i].outerHTML.includes('active')){
                    row=i;
                    for (var j=0,jmax=grid[i].children.length;j<jmax;j++){
                        if(grid[i].children[j].outerHTML.includes('active')){col=j}
                    }
                }
            }
            col = col - 1;
            console.log('row', row, budgets[row]);
            console.log('col', col, budgets[col]);
            table_source.selected.indices = [];  // Reset, so gets triggered again when clicked again

            // This is the actual updating of the plot
            if (row =>  0 && col > 0) {
              // Copy relevant arrays
              var new_x = scatter_source.data[budgets[row]].slice();
              var new_y = scatter_source.data[budgets[col]].slice();
              // Remove all pairs where one value is null
              while ((next_null = new_x.indexOf(null)) > -1) {
                new_x.splice(next_null, 1);
                new_y.splice(next_null, 1);
              }
              while ((next_null = new_y.indexOf(null)) > -1) {
                new_x.splice(next_null, 1);
                new_y.splice(next_null, 1);
              }
              // Assign new data to the plotted columns
              scatter_source.data['x'] = new_x;
              scatter_source.data['y'] = new_y;
              scatter_source.change.emit();
              // Update axis-labels
              xaxis.attributes.axis_label = budgets[row];
              yaxis.attributes.axis_label = budgets[col];
              // Update ranges
              var min = Math.min(...[Math.min(...new_x), Math.min(...new_y)])
                  max = Math.max(...[Math.max(...new_x), Math.max(...new_y)]);
              var padding = (max - min) / 10;
              console.log(min, max, padding);
              xr.start = min - padding;
              yr.start = min - padding;
              xr.end = max + padding;
              yr.end = max + padding;
            }
        } catch(err) {
            console.log(err.message);
        }
        """

        callback = CustomJS(args=dict(table_source=table_source,
                                      scatter_source=scatter_source,
                                      xaxis=p.xaxis[0], yaxis=p.yaxis[0],
                                      xr=p.x_range, yr=p.y_range,
                                      ), code=code)
        table_source.selected.js_on_change('indices', callback)

        layout = column(bokeh_table, p)
        return layout

    def get_html(self, d=None, tooltip=None):
        script, div = components(self.plot())
        if d is not None:
            d["bokeh"] = script, div
        return script, div

    def get_jupyter(self):
        output_notebook()
        show(self.plot())
