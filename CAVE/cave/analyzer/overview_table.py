import os
import logging
from collections import OrderedDict

from pandas import DataFrame
import numpy as np

from cave.analyzer.base_analyzer import BaseAnalyzer
from cave.html.html_helpers import figure_to_html
from cave.utils.helpers import get_config_origin
from cave.utils.bokeh_routines import array_to_bokeh_table

class OverviewTable(BaseAnalyzer):
    def __init__(self, runs, output_dir):
        """ Create overview-table.

        Parameters
        ----------
        runs: List[ConfiguratorRun]
            list with all runs
        output_dir: str
            output-directory for CAVE
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        self.output_dir = output_dir
        self.runs = runs

        self.html_table_general, self.html_table_specific = self.run()

    def run(self):
        """ Generate tables. """
        scenario = self.runs[0].scenario

        general_dict = self._general_dict(scenario)
        html_table_general = DataFrame(data=OrderedDict([('General', general_dict)]))
        html_table_general = html_table_general.reindex(list(general_dict.keys()))
        html_table_general = html_table_general.to_html(escape=False, header=False, justify='left')

        runspec_dict = self._runspec_dict(self.runs)
        order_spec = list(list(runspec_dict.values())[0].keys())  # Get keys of any sub-dict for order
        html_table_specific = DataFrame(runspec_dict)
        html_table_specific = html_table_specific.reindex(order_spec)
        html_table_specific = html_table_specific.to_html(escape=False, justify='left')

        return html_table_general, html_table_specific

    def _general_dict(self, scenario):
        """ Generate the meta-information that holds for all runs (scenario info etc) """
        # general stores information that holds for all runs, runspec holds information on a run-basis
        general = OrderedDict()

        # TODO with multiple BOHB-run-integration
        #    overview['Run with best incumbent'] = os.path.basename(best_run.folder)
        #if num_conf_runs != 1:
        #    overview['Number of configurator runs'] = num_conf_runs

        # Scenario related
        general['# parameters'] = len(scenario.cs.get_hyperparameters())
        general['Deterministic target algorithm'] = scenario.deterministic
        general['Optimized run objective'] = scenario.run_obj
        if scenario.cutoff or scenario.run_obj == 'runtime':
            general['Cutoff'] = scenario.cutoff
        if any([str(lim)!='inf' for lim in [scenario.wallclock_limit, scenario.ta_run_limit, scenario.algo_runs_timelimit]]):
            general['Walltime budget'] = scenario.wallclock_limit
            general['Runcount budget'] = scenario.ta_run_limit
            general['CPU budget'] = scenario.algo_runs_timelimit
        # Instances
        num_train, num_test = [len([i for i in insts if i]) for insts in [scenario.train_insts, scenario.test_insts]]
        if num_train > 0 or num_test > 0:
            general['# instances (train/test)'] = "{} / {}".format(num_train, num_test)
        # Features
        num_feats = scenario.n_features if scenario.feature_dict else 0
        num_dup_feats = 0
        if scenario.feature_dict:
            dup_feats = DataFrame(scenario.feature_array)
            num_dup_feats = len(dup_feats[dup_feats.duplicated()])  # only contains train instances
        if num_feats > 0:
            general['# features (duplicates)'] = "{} ({})".format(num_feats, num_dup_feats)

        return general

    def _runspec_dict(self, runs):
        runspec = OrderedDict()

        for run in runs:
            name = os.path.basename(run.folder)  # TODO this should be changed with multiple BOHB-folder suppor (no basename should be necessary)
            runspec[name] = self._stats_for_run(run.original_runhistory,
                                                run.scenario,
                                                run.incumbent)
        return runspec


    def _stats_for_run(self, rh, scenario, incumbent):
        result = OrderedDict()

        all_configs = rh.get_all_configs()
        default = scenario.cs.get_default_configuration()

        # Runtime statistics
        all_ta_runtimes = [run_value.time for run_value in rh.data.values()]
        result['Total time spent evaluating configurations'] = "{:.2f} sec".format(np.sum(all_ta_runtimes))
        result['Average time per configuration (mean / std)'] = '{:5.2f} sec (± {:5.2f})'.format(np.mean(all_ta_runtimes),
                                                                                                 np.std(all_ta_runtimes))

        # Number of evaluations
        ta_evals = [len(rh.get_runs_for_config(c)) for c in all_configs]
        result['# evaluated configurations'] = len(all_configs)
        if not scenario.deterministic:
            result['# evaluations in total'] = np.sum(ta_evals)
            result['# evaluations for default/incumbent'] = "{}/{}".format(len(rh.get_runs_for_config(default)),
                                                                           len(rh.get_runs_for_config(incumbent)))
            result['# runs per configuration (min, mean and max)'] = "{}/{:.2f}/{}".format(
                            np.min(ta_evals), np.mean(ta_evals), np.max(ta_evals))
        # Info about configurations
        num_changed_params = len([p for p in scenario.cs.get_hyperparameter_names() if default[p] != incumbent[p]])
        result['# changed parameters (default to incumbent)'] = num_changed_params
        # Origins
        origins = [get_config_origin(c) for c in all_configs]
        origins = {o : origins.count(o) for o in set(origins)}
        if not (list(origins.keys()) == ["Unknown"]):
            result['Configuration origins'] = ", ".join(['{} : {}'.format(o, n) for o, n in origins.items()])

        return result


    def get_html(self, d=None, tooltip=None, budget=None):
        if d is not None:
            d["General"] = {"table" : self.html_table_general,
                            "tooltip" : "General information about the optimization scenario."}
            d["Run-Specific"] = {"table" : self.html_table_specific,
                                 "tooltip" : "Information to specific runs (if there are multiple runs). Interesting "
                                             "for parallel optimizations or usage of budgets/fidelities."}
            d["tooltip"] = tooltip
        return ' '.join([self.html_table_general, self.html_table_specific])

    def get_jupyter(self):
        from IPython.core.display import HTML, display
        display(HTML(self.get_html()))

