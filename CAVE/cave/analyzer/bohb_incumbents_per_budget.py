import logging
from collections import OrderedDict

import numpy as np
from pandas import DataFrame
from typing import List

from ConfigSpace.configuration_space import Configuration
from smac.runhistory.runhistory import RunHistory
from smac.scenario.scenario import Scenario

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.utils.helpers import get_cost_dict_for_config, get_timeout, combine_runhistories
from cave.utils.statistical_tests import paired_permutation, paired_t_student
from cave.utils.timing import timing

class BohbIncumbentsPerBudget(BaseAnalyzer):

    def __init__(self,
                 incumbents,
                 budget_names,
                 epm_rhs):
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

        # To be set
        self.table = None
        self.dataframe = None
        self.create_table(incumbents, budget_names, epm_rhs)

    def create_table(self, incumbents, budget_names, epm_rhs):
        """Create table.

        Parameters
        ----------
        incumbents: List[Configuration]
            incumbents per budget, assuming ascending order
        budget_names: List[str]
            budget-names as strings
        epm_rhs: List[RunHistory]
            estimated runhistories for budgets, same length and order as incumbents"""
        self.logger.info("... create performance table")
        if not (len(incumbents) == len(epm_rhs) and len(incumbents) == len(budget_names)):
            raise ValueError("Number of incumbents must equal number of names and runhistories")

        budget_names = [b.split('/')[-1] for b in budget_names]
        dec_place = 3

        # Get costs
        costs = []
        for inc, epm_rh in zip(incumbents, epm_rhs):
            cost_dict_inc = get_cost_dict_for_config(epm_rh, inc)
            costs.append(np.mean([float(v) for v in cost_dict_inc.values()]))

        keys = [k for k in incumbents[0].keys() if any([inc[k] for inc in incumbents])]
        values = []
        for inc, c in zip(incumbents, costs):
            new_values = [inc[k] if inc[k] is not None else "inactive" for k in keys]
            new_values.append(str(round(c, dec_place)))
            values.append(new_values)

        keys.append('Cost')
        table = list(zip(keys, *values))
        keys, table = [k[0] for k in table], [k[1:] for k in table]
        self.table = df = DataFrame(data=table, columns=budget_names, index=keys)
        self.html_table = df.to_html()

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["table"] = self.html_table
            d["tooltip"] = tooltip if tooltip else "Compare hyperparameters and estimated cost of incumbents over budget-steps."
        return "", self.html_table

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.html_table))


