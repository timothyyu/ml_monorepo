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

class PerformanceTable(BaseAnalyzer):

    def __init__(self,
                 instances: List[str],
                 validated_rh: RunHistory,
                 default: Configuration, incumbent: Configuration,
                 epm_rh: RunHistory,
                 scenario: Scenario,
                 rng: np.random.RandomState):
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        self.instances = instances
        self.validated_rh = validated_rh
        self.default, self.incumbent = default, incumbent
        self.epm_rh = epm_rh
        self.scenario = scenario
        self.rng = rng

        oracle = self.get_oracle(instances, epm_rh)
        # To be set
        self.table = None
        self.dataframe = None
        self.create_performance_table(default, incumbent, epm_rh, oracle)

    def create_performance_table(self, default, incumbent, epm_rh, oracle):
        """Create table, compare default against incumbent on train-,
        test- and combined instances. Listing PAR10, PAR1 and timeouts.
        Distinguishes between train and test, if available."""
        self.logger.info("... create performance table")
        cost_dict_def = get_cost_dict_for_config(epm_rh, default)
        cost_dict_inc = get_cost_dict_for_config(epm_rh, incumbent)

        def_par1, inc_par1 = self.get_parX(cost_dict_def, 1), self.get_parX(cost_dict_inc, 1)
        def_par10, inc_par10 = self.get_parX(cost_dict_def, 10), self.get_parX(cost_dict_inc, 10)
        ora_par1, ora_par10 = self.get_parX(oracle, 1), self.get_parX(oracle, 10)

        def_timeouts = get_timeout(epm_rh, default, self.scenario.cutoff)
        inc_timeouts = get_timeout(epm_rh, incumbent, self.scenario.cutoff)
        def_timeouts_tuple = self.timeouts_to_tuple(def_timeouts)
        inc_timeouts_tuple = self.timeouts_to_tuple(inc_timeouts)
        if self.scenario.cutoff:
            ora_timeout = self.timeouts_to_tuple({i: c < self.scenario.cutoff for i, c in oracle.items()})
            data1, data2 = zip(*[(int(def_timeouts[i]), int(inc_timeouts[i])) for i in def_timeouts.keys()])
            p_value_timeouts = "%.5f" % paired_permutation(data1, data2, self.rng,
                                                           num_permutations=10000, logger=self.logger)
        else:
            ora_timeout = self.timeouts_to_tuple({})
            p_value_timeouts = "N/A"
        # p-values (paired permutation)
        p_value_par10 = self._permutation_test(epm_rh, default, incumbent, 10000, 10)
        p_value_par10 = "%.5f" % p_value_par10 if np.isfinite(p_value_par10) else 'N/A'
        p_value_par1 = self._permutation_test(epm_rh, default, incumbent, 10000, 1)
        p_value_par1 = "%.5f" % p_value_par1 if np.isfinite(p_value_par1) else 'N/A'

        dec_place = 3

        metrics = []
        if self.scenario.run_obj == 'runtime':
            metrics.append('PAR10')
            metrics.append('PAR1')
        else:
            metrics.append('Quality')
        if self.scenario.cutoff:
            metrics.append('Timeouts')

        train, test = len(self.scenario.train_insts) > 1, len(self.scenario.test_insts) > 1
        oracle = train or test  # oracle only makes sense with instances
        # Create table
        array = []
        if 'PAR10' in metrics:
            if train and test:
                values = [def_par10[0], inc_par10[0], ora_par10[0], def_par10[1], inc_par10[1], ora_par10[1]]
            elif oracle:
                values = [def_par10, inc_par10, ora_par10]  # oracle only with instances
            else:
                values = [def_par10, inc_par10]
            values = [round(value, dec_place) if np.isfinite(value) else 'N/A' for value in values]
            if train or test:
                values.append(p_value_par10)
            array.append(values)
        if 'PAR1' in metrics or 'Quality' in metrics:
            if train and test:
                values = [def_par1[0], inc_par1[0], ora_par1[0], def_par1[1], inc_par1[1], ora_par1[1]]
            elif oracle:
                values = [def_par1, inc_par1, ora_par1]  # oracle only with instances
            else:
                values = [def_par1, inc_par1]
            values = [round(value, dec_place) if np.isfinite(value) else 'N/A' for value in values]
            if train or test:
                values.append(p_value_par1)
            array.append(values)
        if 'Timeouts' in metrics:
            if train and test:
                values = ["{}/{}".format(def_timeouts_tuple[0][0], def_timeouts_tuple[0][1]),
                          "{}/{}".format(inc_timeouts_tuple[0][0], inc_timeouts_tuple[0][1]),
                          "{}/{}".format(ora_timeout[0][0], ora_timeout[0][1]),
                          "{}/{}".format(def_timeouts_tuple[1][0], def_timeouts_tuple[1][1]),
                          "{}/{}".format(inc_timeouts_tuple[1][0], inc_timeouts_tuple[1][1]),
                          "{}/{}".format(ora_timeout[1][0], ora_timeout[1][1]),
                          ]
            elif oracle:
                values = ["{}/{}".format(def_timeouts_tuple[0], def_timeouts_tuple[1]),
                          "{}/{}".format(inc_timeouts_tuple[0], inc_timeouts_tuple[1]),
                          "{}/{}".format(ora_timeout[0], ora_timeout[1])]
            else:
                values = ["{}/{}".format(def_timeouts_tuple[0], def_timeouts_tuple[1]),
                          "{}/{}".format(inc_timeouts_tuple[0], inc_timeouts_tuple[1]),]
            if train or test:
                values.append(p_value_timeouts)
            array.append(values)

        array = np.array(array)
        columns = ['Default', 'Incumbent']
        if oracle:
            columns.append('Oracle')
        if train and test:
            columns = columns + columns
        if train or test:
           columns.append('p-value')
        self.logger.debug(array)
        self.logger.debug(columns)
        df = DataFrame(data=array, index=metrics, columns=columns)
        table = df.to_html()
        if train and test:
            # Insert two-column-header
            table = table.split(sep='</thead>', maxsplit=1)[1]
            new_table = "<table border=\"3\" class=\"dataframe\">\n"\
                        "  <col>\n"\
                        "  <colgroup span=\"2\"></colgroup>\n"\
                        "  <colgroup span=\"2\"></colgroup>\n"\
                        "  <thead>\n"\
                        "    <tr>\n"\
                        "      <td rowspan=\"2\"></td>\n"\
                        "      <th colspan=\"3\" scope=\"colgroup\">Train</th>\n"\
                        "      <th colspan=\"3\" scope=\"colgroup\">Test</th>\n"\
                        "      <th colspan=\"1\" scope=\"colgroup\">p-value</th>\n"\
                        "    </tr>\n"\
                        "    <tr>\n"\
                        "      <th scope=\"col\">Default</th>\n"\
                        "      <th scope=\"col\">Incumbent</th>\n"\
                        "      <th scope=\"col\">Oracle</th>\n"\
                        "      <th scope=\"col\">Default</th>\n"\
                        "      <th scope=\"col\">Incumbent</th>\n"\
                        "      <th scope=\"col\">Oracle</th>\n"\
                        "    </tr>\n"\
                        "</thead>\n"
            table = new_table + table

        self.table = table
        self.dataframe = df
        return df

    def get_parX(self, cost_dict, par=10):
        """Calculate parX-values from given cost_dict.
        First determine PAR-timeouts for each run on each instances,
        Second average over train/test if available, else just average.

        Parameters
        ----------
        cost_dict: Dict[inst->cost]
            mapping instances to costs
        par: int
            par-factor to use

        Returns
        -------
        (train, test) OR average -- tuple<float, float> OR float
            PAR10 values for train- and test-instances, if available as tuple
            else the general average
        """
        insts = [i for i in self.scenario.train_insts + self.scenario.test_insts if i]
        missing = set(insts) - set(cost_dict.keys())
        if missing:
            self.logger.debug("Missing instances in cost_dict for parX: %s", str(missing))
        # Catch wrong config
        if par != 1 and not self.scenario.cutoff:
            self.logger.debug("No par%d possible, since scenario has not specified cutoff-time", par)
            if len(self.scenario.train_insts) > 1 and len(self.scenario.test_insts) > 1:
                return (np.nan, np.nan)
            else:
                return np.nan

        # Penalize
        if self.scenario.cutoff and self.scenario.run_obj == 'runtime':
            cost_dict = [(k, cost_dict[k]) if cost_dict[k] < self.scenario.cutoff else
                         (k, self.scenario.cutoff * par) for k in cost_dict]
        else:
            cost_dict = [(k, cost_dict[k]) for k in cost_dict]
            self.logger.info("Calculating penalized average runtime without cutoff...")

        # Average
        if len(self.scenario.train_insts) > 1 and len(self.scenario.test_insts) > 1:
            train = np.mean([c for i, c in cost_dict if i in self.scenario.train_insts])
            test = np.mean([c for i, c in cost_dict if i in self.scenario.test_insts])
            return (train, test)
        else:
            return np.mean([c for i, c in cost_dict])

    def timeouts_to_tuple(self, timeouts):
        """ Get number of timeouts in config

        Parameters
        ----------
        timeouts: dict[i -> bool]
            mapping instances to whether timeout was on that instance

        Returns
        -------
        timeouts: tuple(int, int)
            tuple (timeouts, total runs)
        """
        cutoff = self.scenario.cutoff
        train = self.scenario.train_insts
        test = self.scenario.test_insts
        if len(train) > 1 and len(test) > 1:
            if not cutoff:
                return (("N", "A"), ("N", "A"))
            train_timeout = len([i for i in timeouts if (not timeouts[i] and i in train)])
            test_timeout = len([i for i in timeouts if (not timeouts[i] and i in test)])
            return ((train_timeout, len([i for i in timeouts if i in train])),
                    (test_timeout, len([i for i in timeouts if i in test])))
        else:
            if not cutoff:
                return ("N", "A")
            timeout = len([i for i in timeouts if not timeouts[i]])
            return (timeout, len([i for i in timeouts if i in train]))

    @timing
    def get_oracle(self, instances, rh):
        """Estimation of oracle performance. Collects best performance seen for each instance in any run.

        Parameters
        ----------
        instances: List[str]
            list of instances in question
        rh: RunHistory or List[RunHistory]
            runhistory or list of runhistories (will be combined)

        Results
        -------
        oracle: dict[str->float]
            best seen performance per instance {inst : performance}
        """
        if isinstance(rh, list):
            rh = combine_runhistories(rh)
        self.logger.debug("Calculating oracle performance")
        oracle = {}
        for c in rh.get_all_configs():
            costs = get_cost_dict_for_config(rh, c)
            for i in costs.keys():
                if i not in oracle:
                    oracle[i] = costs[i]
                elif oracle[i] > costs[i]:
                    oracle[i] = costs[i]
        return oracle

    @timing
    def _permutation_test(self, epm_rh, default, incumbent, num_permutations, par=1):
        if par != 1 and not self.scenario.cutoff:
            return np.nan
        cutoff = self.scenario.cutoff
        def_cost = get_cost_dict_for_config(epm_rh, default, par=par, cutoff=cutoff)
        inc_cost = get_cost_dict_for_config(epm_rh, incumbent, par=par, cutoff=cutoff)
        data1, data2 = zip(*[(def_cost[i], inc_cost[i]) for i in def_cost.keys()])
        p = paired_permutation(data1, data2, self.rng, num_permutations=num_permutations, logger=self.logger)
        self.logger.debug("p-value for def/inc-difference: %f (permutation test "
                          "with %d permutations and par %d)", p, num_permutations, par)
        return p

    def _paired_t_test(self, epm_rh, default, incumbent, num_permutations):
        def_cost, inc_cost = get_cost_dict_for_config(epm_rh, default), get_cost_dict_for_config(epm_rh, incumbent)
        data1, data2 = zip(*[(def_cost[i], inc_cost[i]) for i in def_cost.keys()])
        p = paired_t_student(data1, data2, logger=self.logger)
        self.logger.debug("p-value for def/inc-difference: %f (paired t-test)", p)
        return p

    def get_html(self, d=None, tooltip=None):
        if d is not None:
            d["table"] = self.table
            d["tooltip"] = tooltip
        return "", self.table

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.table))


