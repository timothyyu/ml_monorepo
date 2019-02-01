import os
from collections import OrderedDict
import operator
import logging

from pandas import DataFrame
import numpy as np

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html
from cave.utils.bokeh_routines import array_to_bokeh_table

from bokeh.embed import components
from bokeh.plotting import show
from bokeh.io import output_notebook

class PimpComparisonTable(BaseAnalyzer):

    def __init__(self,
                 pimp,
                 evaluators,
                 sort_table_by,
                 cs,
                 out_fn,
                 threshold=0.05):
        """Create a html-table over all evaluated parameter-importance-methods.
        Parameters are sorted after their average importance."""
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)

        self.pimp = pimp
        self.evaluators = evaluators
        self.sort_table_by = sort_table_by
        self.cs = cs
        self.out_fn = out_fn
        self.threshold = threshold


    def plot(self):
        self.pimp.table_for_comparison(self.evaluators, self.out_fn, style='latex')
        self.logger.info('Creating pimp latex table at %s' % self.out_fn)

        parameters = [p.name for p in self.cs.get_hyperparameters()]
        index, values, columns = [], [], []
        columns = [e.name for e in self.evaluators]
        columns_lower = [c.lower() for c in columns]

        # SORT
        self.logger.debug("Sort pimp-table by %s" % self.sort_table_by)
        if self.sort_table_by == "average":
            # Sort parameters after average importance
            p_avg = {}
            for p in parameters:
                imps = [e.evaluated_parameter_importance[p] for e in self.evaluators if p in e.evaluated_parameter_importance]
                p_avg[p] = np.mean(imps) if imps else  0
            p_order = sorted(parameters, key=lambda p: p_avg[p], reverse=True)
        elif self.sort_table_by in columns_lower:
            def __get_key(p):
                imp = self.evaluators[columns_lower.index(self.sort_table_by)].evaluated_parameter_importance
                return imp[p] if p in imp else 0
            p_order = sorted(parameters, key=__get_key, reverse=True)
        else:
            raise ValueError("Trying to sort importance table after {}, which "
                             "was not evaluated.".format(self.sort_table_by))

        # PREPROCESS
        for p in p_order:
            values_for_p = [p]
            add_parameter = False  # Only add parameters where at least one evaluator shows importance > threshold
            for e in self.evaluators:
                if p in e.evaluated_parameter_importance:
                    # Check for threshold
                    value_to_add = e.evaluated_parameter_importance[p]
                    if value_to_add > self.threshold:
                        add_parameter = True
                    # All but forward-selection use values between 0 and 1
                    if e.name != 'Forward-Selection':
                        value_to_add = value_to_add * 100
                    # Create string and add uncertainty, if available
                    value_to_add = format(value_to_add, '05.2f')  # (leading zeros for sorting!)
                    if (hasattr(e, 'evaluated_parameter_importance_uncertainty') and
                        p in e.evaluated_parameter_importance_uncertainty):
                        value_to_add += ' +/- ' + format(e.evaluated_parameter_importance_uncertainty[p] * 100, '.2f')
                    values_for_p.append(value_to_add)
                else:
                    values_for_p.append('-')
            if add_parameter:
                values.append(values_for_p)

        # CREATE TABLE
        self.comp_table = DataFrame(values, columns=['Parameters'] + columns)
        sortable = {c : True for c in columns}
        width = {**{'Parameters' : 150}, **{c : 100 for c in columns}}

        bokeh_table = array_to_bokeh_table(self.comp_table, sortable=sortable, width=width, logger=self.logger)
        return bokeh_table

    def get_html(self, d=None, tooltip=None):
        script, div = components(self.plot())
        if d is not None:
            d["bokeh"] = script, div
        return script, div

    def get_jupyter(self):
        output_notebook()
        show(self.plot())

