import sys
import os
import logging
from collections import OrderedDict
from contextlib import contextmanager
from importlib import reload
import typing
from typing import Union, List
import copy
from functools import wraps
import shutil
import inspect

import numpy as np
from pandas import DataFrame

from smac.optimizer.objective import average_cost
from smac.runhistory.runhistory import RunHistory, DataOrigin
from smac.utils.io.input_reader import InputReader
from smac.utils.validate import Validator

from pimp.importance.importance import Importance

from cave.__version__ import __version__ as v
from cave.analyzer.algorithm_footprint import AlgorithmFootprint
from cave.analyzer.bohb_incumbents_per_budget import BohbIncumbentsPerBudget
from cave.analyzer.bohb_learning_curves import BohbLearningCurves
from cave.analyzer.box_violin import BoxViolin
from cave.analyzer.budget_correlation import BudgetCorrelation
from cave.analyzer.cave_ablation import CaveAblation
from cave.analyzer.cave_fanova import CaveFanova
from cave.analyzer.cave_forward_selection import CaveForwardSelection
from cave.analyzer.compare_default_incumbent import CompareDefaultIncumbent
from cave.analyzer.configurator_footprint import ConfiguratorFootprint
from cave.analyzer.cost_over_time import CostOverTime
from cave.analyzer.feature_clustering import FeatureClustering
from cave.analyzer.feature_correlation import FeatureCorrelation
from cave.analyzer.feature_importance import FeatureImportance
from cave.analyzer.local_parameter_importance import LocalParameterImportance
from cave.analyzer.overview_table import OverviewTable
from cave.analyzer.parallel_coordinates import ParallelCoordinates
from cave.analyzer.performance_table import PerformanceTable
from cave.analyzer.pimp_comparison_table import PimpComparisonTable
from cave.analyzer.plot_ecdf import PlotECDF
from cave.analyzer.plot_scatter import PlotScatter
from cave.html.html_builder import HTMLBuilder
from cave.reader.configurator_run import ConfiguratorRun
from cave.utils.helpers import scenario_sanity_check, combine_runhistories
from cave.utils.hpbandster2smac import HpBandSter2SMAC
from cave.utils.timing import timing

__author__ = "Joshua Marben"
__copyright__ = "Copyright 2017, ML4AAD"
__license__ = "3-clause BSD"
__maintainer__ = "Joshua Marben"
__email__ = "joshua.marben@neptun.uni-freiburg.de"


@contextmanager
def _changedir(newdir):
    """ Helper function to change directory, for example to create a scenario
    from file, where paths to the instance- and feature-files are relative to
    the original SMAC-execution-directory. Same with target algorithms that need
    be executed for validation. """
    olddir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(olddir)

def _analyzer_type(f):
    @wraps(f)
    def wrap(self, *args, d=None, **kw):
        run = kw.pop('run', None)
        if self.use_budgets and not f.__name__ in self.always_aggregated:
            if run:
                # Use the run-specific cave instance
                try:
                    cave = self.folder_to_run[run].cave
                except KeyError as err:
                    raise KeyError("You specified '%s' as folder-name. This folder is not either not existent "
                                   "or not included in this CAVE-object. Following folders are included in the analysis: %s" %
                                   (run, str(list(self.folder_to_run.keys()))))
                self.logger.debug("Using %s as cave-instance", run)
                if not cave:
                    raise ValueError("Using budgets, but didn't initialize CAVE-instances per run. "
                                     "Please run your example with '--verbose_level DEBUG' and "
                                     "report this issue with the debug.log (output_dir/debug/debug.log) "
                                     "on https://github.com/automl/CAVE/issues")
            else:
                raise ValueError("You are using a configurator that uses budgets. Please specify one of the following "
                                 "runs as a 'run=' keyword-argument: %s" % (str(list(self.folder_to_run.keys()))),)
        else:
            # Use aggregated objects
            self.logger.debug("Using aggregated cave-instance")
            cave = self
        self.logger.debug("Args: %s, Kwargs: %s", str(args), str(kw))
        try:
            analyzer = f(self, cave, *args, **kw)
        except Exception as err:
            self.logger.exception(err)
            raise
        else:
            if self.show_jupyter:
                try:
                    analyzer.get_jupyter()
                except ImportError as err:
                    self.logger.debug(err)
                    self.logger.info("Assuming that jupyter is not installed. Disable for rest of report.")
                    self.show_jupyter = False
            if isinstance(d, dict):
                analyzer.get_html(d, tooltip=self._get_tooltip(f))
        self._build_website()
        return analyzer
    return wrap

class CAVE(object):
    def __init__(self,
                 folders: typing.List[str],
                 output_dir: str,
                 ta_exec_dir: typing.List[str],
                 file_format: str='SMAC3',
                 validation_format='NONE',
                 validation_method: str='epm',
                 pimp_max_samples: int=-1,
                 fanova_pairwise: bool=True,
                 use_budgets: bool=False,
                 seed: int=42,
                 show_jupyter: bool=True,
                 verbose_level: str='OFF'):
        """
        Initialize CAVE facade to handle analyzing, plotting and building the report-page easily.
        During initialization, the analysis-infrastructure is built and the data is validated, the overall best
        incumbent is found and default+incumbent are evaluated for all instances for all runs, by default using an EPM.

        In the internal data-management the we have three types of runhistories: *original*, *validated* and *epm*.

        - *original_rh* contain only runs that have been gathered during the optimization-process.
        - *validated_rh* may contain original runs, but also data that was not gathered iteratively during the
          optimization, but systematically through external validation of interesting configurations.
          Important: NO ESTIMATED RUNS IN `validated` RUNHISTORIES!
        - *epm_rh* contain runs that are gathered through empirical performance models.

        Runhistories are organized as follows:

        - each ConfiguratorRun has an *original_runhistory*- and a *combined_runhistory*-attribute
        - if available, each ConfiguratorRun's *validated_runhistory* contains
          a runhistory with validation-data gathered after the optimization
        - *combined_runhistory* always contains as many real runs as possible

        Arguments
        ---------
        folders: list<strings>
            paths to relevant SMAC runs
        output_dir: string
            output for cave to write results (figures + report)
        ta_exec_dir: string
            execution directory for target algorithm (to find instance.txt specified in scenario, ..)
        file_format: str
            what format the rundata is in, options are [SMAC3, SMAC2, BOHB and CSV]
        file_format: str
            what format the validation rundata is in, options are [SMAC3, SMAC2, CSV and None]
        validation_method: string
            from [validation, epm], how to estimate missing runs
        pimp_max_samples: int
            passed to PIMP for configuration
        fanova_pairwise: bool
            whether to calculate pairwise marginals for fanova
        use_budgets: bool
            if true, individual runs are treated as different budgets. they are not evaluated together, but compared
            against each other. runs are expected in ascending budget-size.
        seed: int
            random seed for analysis (e.g. the random forests)
        show_jupyter: bool
            default True, tries to output plots and tables to jupyter-frontend, if available
        verbose_level: str
            from [OFF, INFO, DEBUG, DEV_DEBUG and WARNING]
        """
        self.logger = logging.getLogger(self.__module__ + '.' + self.__class__.__name__)
        self.output_dir = output_dir
        self.set_verbosity(verbose_level.upper())
        self.logger.debug("Running CAVE version %s", v)
        self.show_jupyter = show_jupyter
        if self.show_jupyter:
            # Reset logging module
            logging.shutdown()
            reload(logging)

        # Methods that are never per-run, because they are inter-run-analysis by nature
        self.always_aggregated = ['bohb_learning_curves', 'bohb_incumbents_per_budget', 'configurator_footprint',
                                  'budget_correlation', 'cost_over_time',
                                  'overview_table']  # these function-names will always be aggregated

        self.verbose_level = verbose_level
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.use_budgets = use_budgets
        self.ta_exec_dir = ta_exec_dir
        self.file_format = file_format
        self.validation_format = validation_format
        self.validation_method = validation_method
        self.pimp_max_samples = pimp_max_samples
        self.fanova_pairwise = fanova_pairwise

        # To be set during execution (used for dependencies of analysis-methods)
        self.param_imp = OrderedDict()
        self.feature_imp = OrderedDict()
        self.evaluators = []
        self.validator = None

        self.feature_names = None

        self.bohb_result = None  # only relevant for bohb_result

        # Create output_dir if necessary
        self.logger.info("Saving results to '%s'", self.output_dir)
        if not os.path.exists(output_dir):
            self.logger.debug("Output-dir '%s' does not exist, creating", self.output_dir)
            os.makedirs(output_dir)

        if file_format == 'BOHB':
            self.use_budgets = True
            self.bohb_result, folders, budgets = HpBandSter2SMAC().convert(folders, output_dir)
            if "DEBUG" in self.verbose_level:
                for f in folders:
                    debug_f = os.path.join(output_dir, 'debug', os.path.basename(f))
                    shutil.rmtree(debug_f, ignore_errors=True)
                    shutil.copytree(f, debug_f)

            file_format = 'SMAC3'

        # Save all relevant configurator-runs in a list
        self.logger.debug("Folders: %s; ta-exec-dirs: %s", str(folders), str(ta_exec_dir))
        self.runs = []
        if len(ta_exec_dir) < len(folders):
            for i in range(len(folders) - len(ta_exec_dir)):
                ta_exec_dir.append(ta_exec_dir[0])
        for ta_exec_dir, folder in zip(ta_exec_dir, folders):
            try:
                self.logger.debug("Collecting data from %s.", folder)
                self.runs.append(ConfiguratorRun(folder, ta_exec_dir, file_format=file_format,
                                                 validation_format=validation_format))
            except Exception as err:
                self.logger.warning("Folder %s could with ta_exec_dir %s not be loaded, failed with error message: %s",
                                    folder, ta_exec_dir, err)
                self.logger.exception(err)
                continue
        if not self.runs:
            raise ValueError("None of the specified folders could be loaded.")
        self.folder_to_run = {os.path.basename(run.folder) : run for run in self.runs}

        # Use scenario of first run for general purposes (expecting they are all the same anyway!
        self.scenario = self.runs[0].solver.scenario
        scenario_sanity_check(self.scenario, self.logger)
        self.feature_names = self._get_feature_names()
        self.default = self.scenario.cs.get_default_configuration()

        # All runs that have been actually explored during optimization
        self.global_original_rh = None
        # All original runs + validated runs if available
        self.global_validated_rh = None
        # All validated runs + EPM-estimated for def and inc on all insts
        self.global_epm_rh = None
        self.pimp = None
        self.model = None

        if self.use_budgets:
            self._init_helper_budgets()
        else:
            self._init_helper_no_budgets()

        # Builder for html-website
        custom_logo = './custom_logo.png'
        if self.use_budgets:
            logo_fn = 'BOHB_logo.png'
        elif file_format.startswith('SMAC'):
            logo_fn = 'SMAC_logo.png'
        elif os.path.exists(custom_logo):
            logo_fn = custom_logo
        else:
            logo_fn = 'automl-logo.png'
            self.logger.info("No suitable logo found. You can use a custom logo simply by having a file called '%s' "
                             "in the directory from which you run CAVE.", custom_logo)
        self.builder = HTMLBuilder(self.output_dir, "CAVE", logo_fn=logo_fn, logo_custom=custom_logo==logo_fn)
        self.website = OrderedDict([])

    def _init_helper_budgets(self):
        """
        Each run gets it's own CAVE-instance. This way, we can simply use the individual objects (runhistories,
        output-dirs, etc)
        """
        for run in self.runs:
            sub_sec = os.path.basename(run.folder)
            # Set paths for each budget individual to avoid path-conflicts
            sub_output_dir = os.path.join(self.output_dir, 'content', sub_sec)
            os.makedirs(sub_output_dir, exist_ok=True)
            run.cave = CAVE(folders=[run.folder],
                            output_dir=sub_output_dir,
                            ta_exec_dir=[run.ta_exec_dir],
                            file_format=run.file_format,
                            validation_format=run.validation_format,
                            validation_method=self.validation_method,
                            pimp_max_samples=self.pimp_max_samples,
                            fanova_pairwise=self.fanova_pairwise,
                            use_budgets=False,
                            show_jupyter=False,
                            seed=self.seed,
                            verbose_level='OFF')
        self.incumbent = self.runs[-1].incumbent

    def _init_helper_no_budgets(self):
        """
        No budgets means using global, aggregated runhistories to analyze the Configurator's behaviour.
        Also it creates an EPM using all available information, since all runs are "equal".
        """
        self.global_original_rh = RunHistory(average_cost)
        self.global_validated_rh = RunHistory(average_cost)
        self.global_epm_rh = RunHistory(average_cost)
        self.logger.debug("Update original rh with all available rhs!")
        for run in self.runs:
            self.global_original_rh.update(run.original_runhistory, origin=DataOrigin.INTERNAL)
            self.global_validated_rh.update(run.original_runhistory, origin=DataOrigin.INTERNAL)
            if run.validated_runhistory:
                self.global_validated_rh.update(run.validated_runhistory, origin=DataOrigin.EXTERNAL_SAME_INSTANCES)

        self._init_pimp_and_validator(self.global_validated_rh)

        # Estimate missing costs for [def, inc1, inc2, ...]
        self._validate_default_and_incumbents(self.validation_method, self.ta_exec_dir)
        self.global_epm_rh.update(self.global_validated_rh)

        for rh_name, rh in [("original", self.global_original_rh),
                            ("validated", self.global_validated_rh),
                            ("epm", self.global_epm_rh)]:
            self.logger.debug('Combined number of RunHistory data points for %s runhistory: %d '
                              '# Configurations: %d. # Configurator runs: %d',
                              rh_name, len(rh.data), len(rh.get_all_configs()), len(self.runs))

        # Sort runs (best first)
        self.runs = sorted(self.runs, key=lambda run: self.global_epm_rh.get_cost(run.solver.incumbent))
        self.best_run = self.runs[0]

        self.incumbent = self.pimp.incumbent = self.best_run.solver.incumbent
        self.logger.debug("Overall best run: %s, with incumbent: %s", self.best_run.folder, self.incumbent)

    def _init_pimp_and_validator(self, rh, alternative_output_dir=None):
        """Create ParameterImportance-object and use it's trained model for  validation and further predictions
        We pass validated runhistory, so that the returned model will be based on as much information as possible

        Parameters
        ----------
        rh: RunHistory
            runhistory used to build EPM
        alternative_output_dir: str
            e.g. for budgets we want pimp to use an alternative output-dir (subfolders per budget)
        """
        self.logger.debug("Using '%s' as output for pimp", alternative_output_dir if alternative_output_dir else
                self.output_dir)
        self.pimp = Importance(scenario=copy.deepcopy(self.scenario),
                               runhistory=rh,
                               incumbent=self.default,  # Inject correct incumbent later
                               parameters_to_evaluate=4,
                               save_folder=alternative_output_dir if alternative_output_dir else self.output_dir,
                               seed=self.rng.randint(1, 100000),
                               max_sample_size=self.pimp_max_samples,
                               fANOVA_pairwise=self.fanova_pairwise,
                               preprocess=False,
                               verbose=self.verbose_level != 'OFF',  # disable progressbars
                               )
        self.model = self.pimp.model

        # Validator (initialize without trajectory)
        self.validator = Validator(self.scenario, None, None)
        self.validator.epm = self.model

    @timing
    def _validate_default_and_incumbents(self, method, ta_exec_dir):
        """Validate default and incumbent configurations on all instances possible.
        Either use validation (physically execute the target algorithm) or EPM-estimate and update according runhistory
        (validation -> self.global_validated_rh; epm -> self.global_epm_rh).

        Parameters
        ----------
        method: str
            epm or validation
        ta_exec_dir: str
            path from where the target algorithm can be executed as found in scenario (only used for actual validation)
        """
        for run in self.runs:
            self.logger.debug("Validating %s using %s!", run.folder, method)
            self.validator.traj = run.traj
            if method == "validation":
                with _changedir(ta_exec_dir):
                    # TODO determine # repetitions
                    new_rh = self.validator.validate('def+inc', 'train+test', 1, -1, runhistory=self.global_validated_rh)
                self.global_validated_rh.update(new_rh)
            elif method == "epm":
                # Only do test-instances if features for test-instances are available
                instance_mode = 'train+test'
                if (any([i not in self.scenario.feature_dict for i in self.scenario.test_insts]) and
                    any([i in self.scenario.feature_dict for i in self.scenario.train_insts])):  # noqa
                    self.logger.debug("No features provided for test-instances (but for train!). "
                                      "Cannot validate on \"epm\".")
                    self.logger.warning("Features detected for train-instances, but not for test-instances. This is "
                                        "unintended usage and may lead to errors for some analysis-methods.")
                    instance_mode = 'train'

                new_rh = self.validator.validate_epm('def+inc', instance_mode, 1, runhistory=self.global_validated_rh)
                self.global_epm_rh.update(new_rh)
            else:
                raise ValueError("Missing data method illegal (%s)", method)
            self.validator.traj = None  # Avoid usage-mistakes

    @timing
    def analyze(self,
                performance=True,
                cdf=True,
                scatter=True,
                cfp=True,
                cfp_time_slider=False,
                cfp_max_plot=-1,
                cfp_number_quantiles=10,
                param_importance=['forward_selection', 'ablation', 'fanova'],
                pimp_sort_table_by: str="average",
                feature_analysis=["box_violin", "correlation", "importance", "clustering", "feature_cdf"],
                parallel_coordinates=True,
                cost_over_time=True,
                algo_footprint=True):
        """Analyze the available data and build HTML-webpage as dict.
        Save webpage in 'self.output_dir/CAVE/report.html'.
        Analyzing is performed with the analyzer-instance that is initialized in
        the __init__

        Parameters
        ----------
        performance: bool
            whether to calculate par10-values
        cdf: bool
            whether to plot cdf
        scatter: bool
            whether to plot scatter
        cfp: bool
            whether to perform configuration visualization
        cfp_time_slider: bool
            whether to include an interactive time-slider in configuration footprint
        cfp_max_plot: int
            limit number of configurations considered for configuration footprint (-1 -> all configs)
        cfp_number_quantiles: int
            number of steps over time generated in configuration footprint
        param_importance: List[str]
            containing methods for parameter importance
        pimp_sort_table: str
            in what order the parameter-importance overview should be organized
        feature_analysis: List[str]
            containing methods for feature analysis
        parallel_coordinates: bool
            whether to plot parallel coordinates
        cost_over_time: bool
            whether to plot cost over time
        algo_footprint: bool
            whether to plot algorithm footprints
        """
        # Check arguments
        for p in param_importance:
            if p not in ['forward_selection', 'ablation', 'fanova', 'lpi']:
                raise ValueError("%s not a valid option for parameter importance!" % p)
        for f in feature_analysis:
            if f not in ["box_violin", "correlation", "importance", "clustering", "feature_cdf"]:
                raise ValueError("%s not a valid option for feature analysis!" % f)

        # Deactivate pimp for less configs than parameters
        num_configs = len(combine_runhistories([r.original_runhistory for r in self.runs]).get_all_configs())
        num_params = len(self.scenario.cs.get_hyperparameters())
        if num_configs < num_params:
            self.logger.info("Deactivating parameter importance, since there are less configs than parameters (%d < %d)"
                             % (num_configs, num_params))
            param_importance = []


        # Start analysis
        headings = ["Meta Data",
                    "Best Configuration",
                    "Performance Analysis",
                    "Configurators Behavior",
                    "Parameter Importance",
                    "Feature Analysis",
                    "BOHB Plot",
                    ]
        for h in headings:
            self.website[h] = OrderedDict()

        if self.use_budgets:
            # The individual configurator runs are not directory comparable and cannot be aggregated.
            # Nevertheless they need to be combined in one comprehensive report and some metrics are to be compared over
            # the individual runs.
            # TODO: Currently, the code below is configured for bohb... if we extend to other budget-driven configurators, review!

            # Perform analysis for each run
            if self.bohb_result:
                self.website["Budget Correlation"] = OrderedDict()
                self.budget_correlation(d=self.website["Budget Correlation"])
                self.bohb_learning_curves(d=self.website)
                self.website["Incumbents Over Budgets"] = OrderedDict()
                self.bohb_incumbents_per_budget(d=self.website["Incumbents Over Budgets"])
                # Move to second position
                self.website.move_to_end("Budget Correlation", last=False)
                self.website.move_to_end("BOHB Learning Curves", last=False)
                self.website.move_to_end("Incumbents Over Budgets", last=False)
                self.website.move_to_end("Meta Data", last=False)

            # Configurator Footprint always aggregated
            if cfp:  # Configurator Footprint
                self.configurator_footprint(d=self._get_dict(self.website["Configurators Behavior"], "Configurator Footprint"),
                                            run=None,
                                            use_timeslider=cfp_time_slider,
                                            max_confs=cfp_max_plot,
                                            num_quantiles=cfp_number_quantiles)
                self.website["Configurators Behavior"]["Configurator Footprint"]["tooltip"] = self._get_tooltip(self.configurator_footprint)
            if cost_over_time:
                self.cost_over_time(d=self._get_dict(self.website["Configurators Behavior"], "Cost Over Time"), run=None)
                self.website["Configurators Behavior"]["Cost Over Time"]["tooltip"] = self._get_tooltip(self.cost_over_time)
            self.overview_table(d=self._get_dict(self.website, "Meta Data"), run=None)
            self.website["Meta Data"]["tooltip"] = self._get_tooltip(self.overview_table)

            for run in self.runs:
                sub_sec = os.path.basename(run.folder)
                # Set paths for each budget individual to avoid path-conflicts
                sub_output_dir = os.path.join(self.output_dir, 'content', sub_sec)
                os.makedirs(sub_output_dir, exist_ok=True)
                # Set runhistories
                self.global_original_rh = run.original_runhistory
                self.global_validated_rh = run.combined_runhistory
                self.global_epm_rh = RunHistory(average_cost)
                # Train epm and stuff
                self._init_pimp_and_validator(run.combined_runhistory, alternative_output_dir=sub_output_dir)
                self._validate_default_and_incumbents(self.validation_method, run.ta_exec_dir)
                self.pimp.incumbent = run.incumbent
                self.incumbent = run.incumbent
                run.epm_rh = self.global_epm_rh
                self.best_run = run
                # Perform analysis
                self.website["Meta Data"]["tooltip"] = self._get_tooltip(self.overview_table)
                self.parameter_importance(self.website["Parameter Importance"], sub_sec,
                                          ablation=False, #'ablation' in param_importance,
                                          fanova='fanova' in param_importance,
                                          forward_selection='forward_selection' in param_importance,
                                          lpi='lpi' in param_importance,
                                          pimp_sort_table_by=pimp_sort_table_by)
                self.configurators_behavior(self.website["Configurators Behavior"], sub_sec,
                                            False,
                                            False, cfp_max_plot, cfp_time_slider, cfp_number_quantiles,
                                            parallel_coordinates)
                if self.feature_names:
                    self.feature_analysis(self.website["Feature Analysis"], sub_sec,
                                          box_violin='box_violin' in feature_analysis,
                                          correlation='correlation' in feature_analysis,
                                          clustering='clustering' in feature_analysis,
                                          importance='importance' in feature_analysis)
        else:
            self.overview_table(d=self.website["Meta Data"], run=None)
            self.compare_default_incumbent(d=self.website["Best Configuration"], run=None)
            self.performance_analysis(self.website["Performance Analysis"], None,
                                      performance, cdf, scatter, algo_footprint)
            self.parameter_importance(self.website["Parameter Importance"], None,
                                      ablation='ablation' in param_importance,
                                      fanova='fanova' in param_importance,
                                      forward_selection='forward_selection' in param_importance,
                                      lpi='lpi' in param_importance,
                                      pimp_sort_table_by=pimp_sort_table_by)
            self.configurators_behavior(self.website["Configurators Behavior"], None,
                                        cost_over_time,
                                        cfp, cfp_max_plot, cfp_time_slider, cfp_number_quantiles,
                                        parallel_coordinates)
            if self.feature_names:
                self.feature_analysis(self.website["Feature Analysis"], None,
                                      box_violin='box_violin' in feature_analysis,
                                      correlation='correlation' in feature_analysis,
                                      clustering='clustering' in feature_analysis,
                                      importance='importance' in feature_analysis)

        self._build_website()

        self.logger.info("CAVE finished. Report is located in %s",
                         os.path.join(self.output_dir, 'report.html'))

    def _get_dict(self, d, layername, run=None):
        """ Get the appropriate sub-dict for this layer (or layer-run combination) and create it if necessary """
        if not isinstance(d, dict):
            raise ValueError("Pass a valid dict to _get_dict!")
        if not layername in d:
            d[layername] = OrderedDict()
        if run is not None and not run in d[layername] and self.use_budgets:
            d[layername][run] = OrderedDict()
        if run is not None:
            return d[layername][run]
        return d[layername]

    @_analyzer_type
    def overview_table(self, cave):
        """ Meta data, i.e. number of instances and parameters as well as configuration budget. Statistics apply to the
        best run, if multiple configurator runs are compared.
        """
        return OverviewTable(cave.runs,
                             cave.output_dir)

    @_analyzer_type
    def compare_default_incumbent(self, cave):
        """ Comparing parameters of default and incumbent.  Parameters that differ from default to incumbent are presented first."""
        return CompareDefaultIncumbent(cave.default, cave.incumbent)

    def performance_analysis(self, d, run,
                             performance, cdf, scatter, algo_footprint):
        """Generate performance analysis.

        Parameters
        ----------
        d: dictionary
            dictionary to add entries to
        performance, cdf, scatter, algo_footprint: bool
            what analysis-methods to perform
        """

        if performance:
            self.performance_table(d=self._get_dict(d, "Performance Table", run=run), run=run)
            d["Performance Table"]["tooltip"] = self._get_tooltip(self.performance_table)
        if cdf:
            self.plot_ecdf(d=self._get_dict(d, "empirical Cumulative Distribution Function (eCDF)", run=run), run=run)
            d["empirical Cumulative Distribution Function (eCDF)"]["tooltip"] = self._get_tooltip(self.plot_ecdf)
        if scatter:
            self.plot_scatter(d=self._get_dict(d, "Scatterplot", run=run), run=run)
            d["Scatterplot"]["tooltip"] = self._get_tooltip(self.plot_scatter)
        if algo_footprint and self.scenario.feature_dict:
            self.algorithm_footprints(d=self._get_dict(d, "Algorithm Footprints", run=run), run=run)
            d["Algorithm Footprints"]["tooltip"] = self._get_tooltip(self.algorithm_footprints)

    @_analyzer_type
    def performance_table(self, cave):
        """
        If the run-objective is 'runtime': PAR stands for Penalized Average Runtime. If there is a timeout in the
        scenario, runs that were thus cut off can be penalized with a factor (because we do not know how long it would
        have run). PAR1 is no penalty, PAR10 will count all cutoffs with a factor of 10.

        For timeouts: if there are multiple runs on the same configuration-instance pair (with different seeds), some
        resulting in timeouts and some not, the majority decides here.

        P-value (between 0 and 1) results from comparing default and incumbent using a paired permutation test with 10000 iterations
        (permuting instances) and tests against the null-hypothesis that the mean of performance between default and
        incumbent is equal.

        Oracle performance searches for the best single run per instance (so the best seed/configuration-pair that was
        seen) and aggregates over them.
        """
        instances = [i for i in cave.scenario.train_insts + cave.scenario.test_insts if i]
        return PerformanceTable(instances, cave.global_validated_rh, cave.default, cave.incumbent,
                                  cave.global_epm_rh, cave.scenario, cave.rng)

    @_analyzer_type
    def plot_scatter(self, cave):
        """
        Scatter plots show the costs of the default and optimized parameter configuration on each instance. Since this
        looses detailed information about the individual cost on each instance by looking at aggregated cost values in
        tables, scatter plots provide a more detailed picture. They provide insights whether overall performance
        improvements can be explained only by some outliers or whether they are due to improvements on the entire
        instance set. On the left side the training-data is scattered, on the right side the test-data is scattered.
        """

        return PlotScatter(default=cave.default,
                           incumbent=cave.incumbent,
                           rh=cave.global_epm_rh,
                           train=cave.scenario.train_insts,
                           test=cave.scenario.test_insts,
                           run_obj=cave.scenario.run_obj,
                           cutoff=cave.scenario.cutoff,
                           output_dir=cave.output_dir,
                           )

    @_analyzer_type
    def plot_ecdf(self, cave):
        """
        Depicts cost distributions over the set of instances.  Since these are empirical distributions, the plots show
        step functions. These plots provide insights into how well configurations perform up to a certain threshold. For
        runtime scenarios this shows the probability of solving all instances from the set in a given timeframe. On the
        left side the training-data is scattered, on the right side the test-data is scattered."""
        return PlotECDF(cave.default, cave.incumbent, cave.global_epm_rh,
                        cave.scenario.train_insts, cave.scenario.test_insts, cave.scenario.cutoff,
                        cave.output_dir)


    @_analyzer_type
    def algorithm_footprints(self, cave):
        """
        The instance features are projected into a two/three dimensional space using principal component analysis (PCA)
        and the footprint of each algorithm is plotted, i.e., on which instances the default or the optimized
        configuration performs well. In contrast to the other analysis methods in this section, these plots allow
        insights into which of the two configurations performs well on specific types or clusters of instances. Inspired
        by Smith-Miles.
        """
        return AlgorithmFootprint(algorithms=[(cave.default, "default"), (cave.incumbent, "incumbent")],
                                  epm_rh=cave.global_epm_rh,
                                  train=cave.scenario.train_insts,
                                  test=cave.scenario.test_insts,
                                  features=cave.scenario.feature_dict,
                                  cutoff=cave.scenario.cutoff,
                                  output_dir=cave.output_dir,
                                  rng=cave.rng,
                                  )

    @_analyzer_type
    def cost_over_time(self, cave):
        """
        Depicts the average cost of the best so far found configuration (using all trajectory data) over the time spent
        by the configurator (including target algorithm runs and the overhead generated by the configurator) If the
        curve flattens out early, it indicates that too much time was spent for the configurator run; whereas a curve
        that is still improving at the end of the budget indicates that one should increase the configuration budget.
        The plotted standard deviation gives the uncertainty over multiple configurator runs.
        """
        return CostOverTime(cave.scenario,
                            cave.output_dir,
                            cave.global_validated_rh,
                            self.runs,
                            block_epm=self.use_budgets,  # blocking epms if bohb is analyzed
                            bohb_result=self.bohb_result,
                            validator=cave.validator)

    @_analyzer_type
    def parallel_coordinates(self, cave,
                             params: Union[int, List[str]]=5,
                             n_configs: int=100,
                             max_runs_epm: int=300000):
        """
        Previously used by Golovin et al.  to study the frequency of chosen parameter settings in
        black-box-optimization.  Each line corresponds to one configuration in the runhistory and shows the parameter
        settings and the corresponding (estimated) average cost. To handle large configuration spaces with hundreds of
        parameters, the (at most) 10 most important parameters based on a fANOVA parameter importance analysis are
        plotted.  To emphasize better configurations, the performance is encoded in the color of each line, ranging from
        blue to red. These plots provide insights into whether the configurator focused on specific parameter values and
        how these correlate to their costs.

        NOTE: the given runhistory should contain only optimization and no
        validation to analyze the explored parameter-space.

        Parameters
        ----------
        params: List[str] or int
            if int, plot at most params parameters, trying to determine with parameter importance.
            if List of strings, the names of the parameters to be plotted
        n_configs: int
            number of configs. will try to find most interesting configs to plot
        max_runs_epm: int
            this is a maximum of runs to be used for training of the epm. use to avoid MemoryErrors
        """
        self.logger.info("    plotting %s parameters for (max) %s configurations", params, n_configs)

        return ParallelCoordinates(original_rh=cave.global_original_rh,
                                   validated_rh=cave.global_validated_rh,
                                   validator=cave.validator,
                                   scenario=cave.scenario,
                                   default=cave.default, incumbent=cave.incumbent,
                                   param_imp=cave.param_imp,
                                   params=params,
                                   n_configs=n_configs,
                                   max_runs_epm=max_runs_epm,
                                   output_dir=cave.output_dir,
                                   cs=cave.scenario.cs,
                                   runtime=(cave.scenario.run_obj == 'runtime'))

    @_analyzer_type
    def configurator_footprint(self, cave,
                               use_timeslider=False, max_confs=1000, num_quantiles=8):
        """
        Analysis of the iteratively sampled configurations during the optimization procedure.  Multi-dimensional scaling
        (MDS) is used to reduce dimensionality of the search space and plot the distribution of evaluated
        configurations. The larger the dot, the more often the configuration was evaluated on instances from the set.
        Configurations that were incumbents at least once during optimization are marked as red squares.  Configurations
        acquired through local search are marked with a 'x'.  The downward triangle denotes the final incumbent, whereas
        the orange upward triangle denotes the default configuration.  The heatmap and the colorbar correspond to the
        predicted performance in that part of the search space.

        Parameters
        ----------
        use_timeslider: bool
            whether to generate time-slíder widget in bokehplot (cool, but time-consuming)
        max_confs: int
            maximum number of configurations to consider for the plot
        num_quantiles: int
            number of quantiles for evolution over time (number of time-steps to look at)
        """
        self.logger.info("... visualizing explored configspace (this may take "
                         "a long time, if there is a lot of data - deactive with --no_configurator_footprint)")

        return ConfiguratorFootprint(
                 cave.scenario,
                 cave.runs,
                 cave.global_original_rh,
                 final_incumbent=self.incumbent,
                 output_dir=cave.output_dir,
                 max_confs=max_confs,
                 use_timeslider=use_timeslider,
                 num_quantiles=num_quantiles)

    def configurators_behavior(self,
                               d,
                               run,
                               cost_over_time=False,
                               cfp=False,
                               cfp_max_plot=-1,
                               cfp_time_slider=False,
                               cfp_number_quantiles=1,
                               parallel_coordinates=False):

        if cost_over_time:
            self.cost_over_time(d=self._get_dict(d, "Cost Over Time", run=run), run=run)
            d["Cost Over Time"]["tooltip"] = self._get_tooltip(self.cost_over_time)
        if cfp:  # Configurator Footprint
            self.configurator_footprint(d=self._get_dict(d, "Configurator Footprint", run=run), run=run,
                                        use_timeslider=cfp_time_slider, max_confs=cfp_max_plot, num_quantiles=cfp_number_quantiles)
            d["Configurator Footprint"]["tooltip"] = self._get_tooltip(self.configurator_footprint)
        if parallel_coordinates:
            # Should be after parameter importance, if performed.
            self.parallel_coordinates(d=self._get_dict(d, "Parallel Coordinates", run=run), run=run)
            d["Parallel Coordinates"]["tooltip"] = self._get_tooltip(self.parallel_coordinates)

    @_analyzer_type
    def cave_fanova(self, cave):
        """
        fANOVA (functional analysis of variance) computes the fraction of the variance in the cost space explained by
        changing a parameter by marginalizing over all other parameters, for each parameter (or for pairs of
        parameters). Parameters with high importance scores will have a large impact on the performance.  To this end, a
        random forest is trained as an empirical performance model on the available empirical data from the available
        runhistories.
        """
        try:
            fanova = CaveFanova(cave.pimp, cave.incumbent, cave.output_dir)
        except IndexError as err:
            self.logger.debug("Error in fANOVA", exc_info=1)
            raise IndexError("Error in fANOVA - please run with --pimp_no_fanova_pairs (this is due to a known issue "
                             "with ints and bools in categorical hyperparameters, see issue #192).")
        cave.evaluators.append(cave.pimp.evaluator)
        cave.param_imp["fanova"] = cave.pimp.evaluator.evaluated_parameter_importance

        return fanova

    @_analyzer_type
    def cave_ablation(self, cave):
        """ Ablation Analysis is a method to determine parameter importance by comparing two parameter configurations,
        typically the default and the optimized configuration.  It uses a greedy forward search to determine the order
        of flipping the parameter settings from default configuration to incumbent such that in each step the cost is
        maximally decreased."""

        ablation = CaveAblation(cave.pimp, cave.incumbent, cave.output_dir)
        cave.evaluators.append(cave.pimp.evaluator)
        cave.param_imp["ablation"] = cave.pimp.evaluator.evaluated_parameter_importance

        return ablation

    @_analyzer_type
    def pimp_forward_selection(self, cave):
        """
        Forward Selection is a generic method to obtain a subset of parameters to achieve the same prediction error as
        with the full parameter set.  Each parameter is scored by how much the out-of-bag-error of an empirical
        performance model based on a random forest is decreased."""
        forward = CaveForwardSelection(cave.pimp, cave.incumbent, cave.output_dir)
        cave.evaluators.append(cave.pimp.evaluator)
        cave.param_imp["forward-selection"] = cave.pimp.evaluator.evaluated_parameter_importance

        return forward

    @_analyzer_type
    def local_parameter_importance(self, cave):
        """ Using an empirical performance model, performance changes of a configuration along each parameter are
        calculated. To quantify the importance of a parameter value, the variance of all cost values by changing that
        parameter are predicted and then the fraction of all variances is computed. This analysis is inspired by the
        human behaviour to look for improvements in the neighborhood of individual parameters of a configuration."""

        lpi = LocalParameterImportance(cave.pimp, cave.incumbent, cave.output_dir)
        cave.evaluators.append(cave.pimp.evaluator)
        cave.param_imp["lpi"] = cave.pimp.evaluator.evaluated_parameter_importance

        return lpi

    @_analyzer_type
    def pimp_comparison_table(self, cave,
                              pimp_sort_table_by="average"):
        """
        Parameters are initially sorted by pimp_sort_table_by. Only parameters with an importance greater than 5 in any
        of the methods are shown.  Note, that the values of the used methods are not directly comparable. For more
        information on the metrics, see respective tooltips."""
        return PimpComparisonTable(cave.pimp,
                                   cave.evaluators,
                                   sort_table_by=pimp_sort_table_by,
                                   cs=cave.scenario.cs,
                                   out_fn=os.path.join(cave.output_dir, 'pimp.tex'),
                                   )

    def parameter_importance(self,
                             d, run,
                             ablation=False, fanova=False,
                             forward_selection=False, lpi=False, pimp_sort_table_by='average'):
        """Perform the specified parameter importance procedures. """
        sum_ = 0
        if fanova:
            self.logger.info("fANOVA...")
            self.cave_fanova(d=self._get_dict(d, "fANOVA", run=run), run=run)
            d["fANOVA"]["tooltip"] = self._get_tooltip(self.cave_fanova)
            sum_ += 1

        if ablation:
            self.logger.info("Ablation...")
            self.cave_ablation(d=self._get_dict(d, "Ablation", run=run), run=run)
            d["Ablation"]["tooltip"] = self._get_tooltip(self.cave_ablation)
            sum_ += 1

        if forward_selection:
            self.logger.info("Forward Selection...")
            self.pimp_forward_selection(d=self._get_dict(d, "Forward Selection", run=run), run=run)
            d["Forward Selection"]["tooltip"] = self._get_tooltip(self.pimp_forward_selection)
            sum_ += 1

        if lpi:
            self.logger.info("Local EPM-predictions around incumbent...")
            self.local_parameter_importance(d=self._get_dict(d, "Local Parameter Importance (LPI)", run=run), run=run)
            d["Local Parameter Importance (LPI)"]["tooltip"] = self._get_tooltip(self.local_parameter_importance)
            sum_ += 1

        if sum_ >= 2:
            self.pimp_comparison_table(d=self._get_dict(d, "Importance Table", run=run), run=run)
            d.move_to_end("Importance Table", last=False)
            d["Importance Table"]["tooltip"] = self._get_tooltip(self.pimp_comparison_table).replace('pimp_sort_table_by', pimp_sort_table_by)

    @_analyzer_type
    def feature_importance(self, cave):
        res = FeatureImportance(cave.pimp, cave.output_dir)
        cave.feature_imp = res.feat_importance
        return res

    @_analyzer_type
    def box_violin(self, cave):
        """
        Box and Violin Plots show the distribution of each feature value across the instances.  Box plots show the
        quantiles of the distribution and violin plots show the approximated probability density of the feature values.
        Such plots are useful to inspect the instances and to detect characteristics of the instances. For example, if
        the distributions have two or more modes, it could indicate that the instance set is heterogeneous which could
        cause problems in combination with racing strategies configurators typically use. NaN values are removed from
        the data."""
        return BoxViolin(cave.output_dir,
                         cave.scenario,
                         cave.feature_names,
                         cave.feature_imp)


    @_analyzer_type
    def feature_correlation(self, cave):
        """
        Correlation of features based on the Pearson product-moment correlation. Since instance features are used to train an
        empirical performance model in model-based configurators, it can be important to remove correlated features in a
        pre-processing step depending on the machine-learning algorithm.  Darker fields corresponds to a larger correlation
        between the features."""
        return FeatureCorrelation(cave.output_dir,
                                  cave.scenario,
                                  cave.feature_names,
                                  cave.feature_imp)


    @_analyzer_type
    def feature_clustering(self, cave):
        """ Clustering instances in 2d; the color encodes the cluster assigned to each cluster. Similar to ISAC, we use
        a k-means to cluster the instances in the feature space. As pre-processing, we use standard scaling and a PCA to
        2 dimensions. To guess the number of clusters, we use the silhouette score on the range of 2 to 12 in the number
        of clusters"""
        return FeatureClustering(cave.output_dir,
                                 cave.scenario,
                                 cave.feature_names,
                                 cave.feature_imp)

    def feature_analysis(self, d, run,
                         box_violin=False, correlation=False, clustering=False, importance=False):
        # feature importance using forward selection
        if importance:
            self.feature_importance(d=self._get_dict(d, "Feature Importance", run=run), run=run)
            d["Feature Importance"]["tooltip"] = self._get_tooltip(self.feature_importance)
        if box_violin:
            self.box_violin(d=self._get_dict(d, "Violin and Box Plots", run=run), run=run)
            d["Violin and Box Plots"]["tooltip"] = self._get_tooltip(self.box_violin)
        if correlation:
            self.feature_correlation(d=self._get_dict(d, "Correlation", run=run), run=run)
            d["Correlation"]["tooltip"] = self._get_tooltip(self.feature_correlation)
        if clustering:
            self.feature_clustering(d=self._get_dict(d, "Clustering", run=run), run=run)
            d["Clustering"]["tooltip"] = self._get_tooltip(self.feature_clustering)

    @_analyzer_type
    def bohb_learning_curves(self, cave):
        """Visualizing the learning curves of the individual Hyperband-iterations. Model based picks are marked with a
        cross. The config-id tuple denotes (iteration, stage, id_within_stage), where the iteration is a hyperband
        iteration and the stage is the index of the budget used. It can be interpreted as a nested index-identifier.
        """
        return BohbLearningCurves(self.scenario.cs.get_hyperparameter_names(), result_object=self.bohb_result)

    @_analyzer_type
    def bohb_incumbents_per_budget(self, cave):
        """
        Show the incumbents for each budget (i.e. the best configuration by kernel-estimation using data from that
        budget).
        """
        return BohbIncumbentsPerBudget([b.incumbent for b in self.runs],
                                       [b.folder for b in self.runs],
                                       [b.epm_runhistory for b in self.runs])

    @_analyzer_type
    def budget_correlation(self, cave):
        """
        Use spearman correlation, to get a correlation-value and a p-value for every pairwise combination of budgets.
        First value is the correlation, second is the p-value (the p-value roughly estimates the likelihood to obtain
        this correlation coefficient with uncorrelated datasets).
        """
        return BudgetCorrelation(self.runs)


###########################################################################
# HELPERS HELPERS HELPERS HELPERS HELPERS HELPERS HELPERS HELPERS HELPERS #
###########################################################################

    def print_budgets(self):
        """If the analyzed configurator uses budgets, print a list of available budgets."""
        if self.use_budgets:
            print(list(self.folder_to_run.keys()))
        else:
            raise NotImplementedError("This CAVE instance does not seem to use budgets.")

    def _get_tooltip(self, f):
        """Extract tooltip from function-docstrings"""
        tooltip = inspect.getdoc(f)
        tooltip = tooltip.split("Parameters\n----------")[0] if tooltip is not None else ""
        tooltip = tooltip.replace("\n", " ")
        return tooltip

    def _get_feature_names(self):
        if not self.scenario.feature_dict:
            self.logger.info("No features available. Skipping feature analysis.")
            return
        feat_fn = self.scenario.feature_fn
        if not self.scenario.feature_names:
            self.logger.debug("`scenario.feature_names` is not set. Loading from '%s'", feat_fn)
            with _changedir(self.ta_exec_dir if self.ta_exec_dir else '.'):
                if not feat_fn or not os.path.exists(feat_fn):
                    self.logger.warning("Feature names are missing. Either provide valid feature_file in scenario "
                                        "(currently %s) or set `scenario.feature_names` manually." % feat_fn)
                    self.logger.error("Skipping Feature Analysis.")
                    return
                else:
                    # Feature names are contained in feature-file and retrieved
                    feat_names = InputReader().read_instance_features_file(feat_fn)[0]
        else:
            feat_names = copy.deepcopy(self.scenario.feature_names)
        return feat_names

    def _build_website(self):
        self.builder.generate_html(self.website)

    def set_verbosity(self, level):
        # TODO add custom level with logging.addLevelName (e.g. DEV_DEBUG)
        # Log to stream (console)
        logging.getLogger().setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        stdout_handler = logging.StreamHandler()
        stdout_handler.setFormatter(formatter)
        if level == "INFO":
            stdout_handler.setLevel(logging.INFO)
        elif level == "WARNING":
            stdout_handler.setLevel(logging.WARNING)
        elif level == "OFF":
            stdout_handler.setLevel(logging.ERROR)
        elif level in ["DEBUG", "DEV_DEBUG"]:
            stdout_handler.setLevel(logging.DEBUG)
            if level == "DEV_DEBUG":
                # Disable annoying boilerplate-debug-logs from foreign modules
                disable_loggers = ["smac.scenario",
                                   # pimp logging
                                   "pimp.epm.unlogged_epar_x_rfwi.UnloggedEPARXrfi",
                                   "Forward-Selection",
                                   "LPI",
                                   # Other (mostly bokeh)
                                   "PIL.PngImagePlugin",
                                   "matplotlib.font_manager",
                                   "matplotlib.ticker",
                                   "matplotlib.axes",
                                   "matplotlib.colorbar",
                                   "urllib3.connectionpool",
                                   "selenium.webdriver.remote.remote_connection"]
                for logger in disable_loggers:
                    logging.getLogger().debug("Setting logger \'%s\' on level INFO", logger)
                    logging.getLogger(logger).setLevel(logging.INFO)
        else:
            raise ValueError("%s not recognized as a verbosity level. Choose from DEBUG, DEV_DEBUG. INFO, OFF.".format(level))

        logging.getLogger().addHandler(stdout_handler)
        # Log to file
        if not os.path.exists(os.path.join(self.output_dir, "debug")):
            os.makedirs(os.path.join(self.output_dir, "debug"))
        fh = logging.FileHandler(os.path.join(self.output_dir, "debug/debug.log"), "w")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logging.getLogger().addHandler(fh)
