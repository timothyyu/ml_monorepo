#!/usr/bin/env python

import os
import sys
from argparse import ArgumentParser, SUPPRESS
import logging
import glob
from datetime import datetime as datetime
import time

import matplotlib

matplotlib.use('agg')  # noqa

from pimp.utils.io.cmd_reader import SmartArgsDefHelpFormatter

from cave.cavefacade import CAVE
from cave.__version__ import __version__ as v

__author__ = "Joshua Marben"
__copyright__ = "Copyright 2017, ML4AAD"
__license__ = "3-clause BSD"
__maintainer__ = "Joshua Marben"
__email__ = "joshua.marben@neptun.uni-freiburg.de"


class CaveCLI(object):
    """
    CAVE command line interface.
    """

    def main_cli(self):
        """
        Main cli, implementing comparison between and analysis of Configuration-results.
        """
        # Some choice-blocks, that can be reused throughout the CLI
        p_choices = [
                     "all",
                     "ablation",
                     "forward_selection",
                     "fanova",
                     "lpi",
                     "none"
                    ]
        p_sort_by_choices = ["average"] + p_choices[1:-1]
        f_choices = [
                     "all",
                     "box_violin",
                     "correlation",
                     "clustering",
                     "importance",
                     "none"
                    ]

        parser = ArgumentParser(formatter_class=SmartArgsDefHelpFormatter, add_help=False,
                                description='CAVE: Configuration Assessment Vizualisation and Evaluation')

        req_opts = parser.add_argument_group("Required Options:" + '~' * 100)
        req_opts.add_argument("--folders",
                              required=True,
                              nargs='+',
                              # strings prefixed with raw| can be manually split with \n
                              help="raw|path(s) to SMAC output-directory/ies, "
                                   "containing each at least a runhistory\nand "
                                   "a trajectory.",
                              default=SUPPRESS)

        opt_opts = parser.add_argument_group("Optional Options:" + '~' * 100)
        opt_opts.add_argument("--verbose_level",
                              default="INFO",
                              choices=[
                                  "INFO",
                                  "DEBUG",
                                  "DEV_DEBUG",
                                  "WARNING",
                                  "OFF"
                              ],
                              help="verbose level. use DEV_DEBUG for development to filter boilerplate-logs from "
                                   "imported modules, use DEBUG for full logging. full debug-log always in "
                                   "'output/debug/debug.log' ")
        opt_opts.add_argument("--jupyter",
                              default='off',
                              choices=['on', 'off'],
                              help="output everything to jupyter, if available."
                              )
        opt_opts.add_argument("--validation",
                              default="epm",
                              choices=[
                                  "validation",
                                  "epm"
                              ],
                              help="how to complete missing runs for config/inst-pairs. epm trains random forest with "
                                   "available data to estimate missing runs, validation requires target algorithm. ",
                              type=str.lower)
        opt_opts.add_argument("--output",
                              default="CAVE_output_%s" % (
                                        datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H:%M:%S_%f')),
                              help="path to folder in which to save the HTML-report. ")
        opt_opts.add_argument("--seed",
                              default=42,
                              type=int,
                              help="random seed used throughout analysis. ")
        opt_opts.add_argument("--file_format",
                              default='SMAC3',
                              help="specify the format of the configurator-files. ",
                              choices=['SMAC2', 'SMAC3', 'CSV', 'BOHB'],
                              type=str.upper)
        opt_opts.add_argument("--validation_format",
                              default='NONE',
                              help="what format the validation-files are in",
                              choices=['SMAC2', 'SMAC3', 'CSV', 'NONE'],
                              type=str.upper)
        opt_opts.add_argument("--ta_exec_dir",
                              default='.',
                              help="path to the execution-directory of the configurator run. this is the path from "
                                   "which the scenario is loaded, so the instance-/pcs-files specified in the "
                                   "scenario, so they are relative to this path "
                                   "(e.g. 'ta_exec_dir/path_to_train_inst_specified_in_scenario.txt'). ",
                              nargs='+')
        # PIMP-configs
        opt_opts.add_argument("--pimp_max_samples",
                              default=-1,
                              type=int,
                              help="How many datapoints to use with PIMP. -1 -> use all. ")
        opt_opts.add_argument("--pimp_no_fanova_pairs",
                              action="store_false",
                              dest="fanova_pairwise",
                              help="fANOVA won't compute pairwise marginals")
        opt_opts.add_argument("--pimp_sort_table_by",
                              default="average",
                              choices=p_sort_by_choices,
                              help="raw|what kind of parameter importance method to "
                                   "use to sort the overview-table. ")
        opt_opts.add_argument("--parameter_importance",
                              default="all",
                              nargs='+',
                              help="raw|what kind of parameter importance method to "
                                   "use. Choose any combination of\n[" + ', '.join(p_choices[1:-1]) + "] or set it to "
                                                                                                      "all/none",
                              choices=p_choices,
                              type=str.lower)
        opt_opts.add_argument("--feature_analysis",
                              default="all",
                              nargs='+',
                              help="raw|what kind of feature analysis methods to use. "
                                   "Choose any combination of\n[" + ', '.join(f_choices[1:-1]) + "] or set it to "
                                                                                                 "all/none",
                              choices=f_choices,
                              type=str.lower)
        opt_opts.add_argument("--cfp_time_slider",
                              help="whether or not to have a time_slider-widget on cfp-plot"
                                   "INCREASES FILE-SIZE (and loading) DRAMATICALLY. ",
                              choices=["on", "off"],
                              default="off")
        opt_opts.add_argument("--cfp_number_quantiles",
                              help="number of quantiles that configurator footprint should plot over time. ",
                              default=3, type=int)
        opt_opts.add_argument("--cfp_max_plot",
                              help="maximum number of configurations to be plotted in configurator footprint (in case "
                                   "you run into a MemoryError). -1 -> plot all. ",
                              default=-1, type=int)
        opt_opts.add_argument("--no_tabular_analysis",
                              action='store_false',
                              help="don't create performance table.",
                              dest='tabular_analysis')
        opt_opts.add_argument("--no_ecdf",
                              action='store_false',
                              help="don't plot ecdf.",
                              dest='ecdf')
        opt_opts.add_argument("--no_scatter_plots",
                              action='store_false',
                              help="don't plot scatter plots.",
                              dest='scatter_plots')
        opt_opts.add_argument("--no_cost_over_time",
                              action='store_false',
                              help="don't plot cost over time.",
                              dest='cost_over_time')
        opt_opts.add_argument("--no_configurator_footprint",
                              action='store_false',
                              help="don't plot configurator footprint.",
                              dest='cfp')
        opt_opts.add_argument("--no_parallel_coordinates",
                              action='store_false',
                              help="don't plot parallel coordinates.",
                              dest='parallel_coordinates')
        opt_opts.add_argument("--no_algorithm_footprints",
                              action='store_false',
                              help="don't plot algorithm footprints.",
                              dest='algorithm_footprints')

        spe_opts = parser.add_argument_group("special arguments:" + '~' * 100)
        spe_opts.add_argument('-v', '--version', action='version',
                              version='%(prog)s ' + str(v), help="show program's version number and exit.")
        spe_opts.add_argument('-h', '--help', action="help", help="show this help message and exit")

        args_= parser.parse_args(sys.argv[1:])

        # Expand configs
        if "all" in args_.parameter_importance:
            param_imp = ["ablation", "forward_selection", "fanova", "lpi"]
        elif "none" in args_.parameter_importance:
            param_imp = []
        else:
            param_imp = args_.parameter_importance

        if "fanova" in param_imp:
            try:
                import fanova  # noqa
            except ImportError:
                raise ImportError('fANOVA is not installed! To install it please run '
                                  '"git+http://github.com/automl/fanova.git@master"')

        if not (args_.pimp_sort_table_by == "average" or
                args_.pimp_sort_table_by in param_imp):
            raise ValueError("Pimp comparison sorting key is {}, but this "
                             "method is deactivated or non-existent.".format(args_.pimp_sort_table_by))

        if "all" in args_.feature_analysis:
            feature_analysis = ["box_violin", "correlation", "importance", "clustering", "feature_cdf"]
        elif "none" in args_.feature_analysis:
            feature_analysis = []
        else:
            feature_analysis = args_.feature_analysis

        cfp_time_slider = True if args_.cfp_time_slider == "on" else False

        if not(args_.tabular_analysis or args_.ecdf or args_.scatter_plots or args_.cfp or
               args_.parallel_coordinates or args_.parallel_coordinates or args_.cost_over_time or
               args_.algorithm_footprints or param_imp or feature_analysis):
            raise ValueError('At least one analysis method required to run CAVE')

        output_dir = args_.output

        logging.getLogger().debug("CAVE is called with arguments: " + str(args_))

        # Configuration results to be analyzed
        folders = []
        for f in args_.folders:
            if '*' in f:
                folders.extend(list(glob.glob(f, recursive=True)))
            else:
                folders.append(f)
        # Default ta_exec_dir is cwd
        ta_exec_dir = []
        for t in args_.ta_exec_dir:
            if '*' in t:
                ta_exec_dir.extend(list(glob.glob(t, recursive=True)))
            else:
                ta_exec_dir.append(t)

        tabular_analysis = args_.tabular_analysis
        file_format = args_.file_format
        validation_format = args_.validation_format
        validation = args_.validation
        pimp_max_samples = args_.pimp_max_samples
        fanova_pairwise = args_.fanova_pairwise
        seed = args_.seed
        ecdf = args_.ecdf
        scatter_plots = args_.scatter_plots
        cfp = args_.cfp
        cfp_time_slider = args_.cfp_time_slider == 'on'
        cfp_max_plot = args_.cfp_max_plot
        cfp_number_quantiles = args_.cfp_number_quantiles
        parallel_coordinates = args_.parallel_coordinates
        cost_over_time = args_.cost_over_time
        algorithm_footprints = args_.algorithm_footprints
        pimp_sort_table_by = args_.pimp_sort_table_by
        verbose_level = args_.verbose_level
        show_jupyter = args_.jupyter == 'on'

        if file_format == 'BOHB':
            logging.getLogger().info("File format is BOHB, performing special nested analysis for budget-based optimizer!")
            validation_format = 'NONE'
            validation_method = 'epm'
            cdf = False
            scatter = False
            algo_footprint = False
            param_imp = [p for p in param_imp if not p == 'forward_selection']
            feature_analysis = []

        cave = CAVE(folders,
                    output_dir,
                    ta_exec_dir,
                    file_format=file_format,
                    validation_format=validation_format,
                    validation_method=validation,
                    pimp_max_samples=pimp_max_samples,
                    fanova_pairwise=fanova_pairwise,
                    use_budgets=file_format=='BOHB',
                    show_jupyter=show_jupyter,
                    seed=seed,
                    verbose_level=verbose_level)

        # Analyze
        cave.analyze(performance=tabular_analysis,
                     cdf=ecdf,
                     scatter=scatter_plots,
                     cfp=cfp,
                     cfp_time_slider=cfp_time_slider,
                     cfp_max_plot=cfp_max_plot,
                     cfp_number_quantiles=cfp_number_quantiles,
                     parallel_coordinates=parallel_coordinates,
                     cost_over_time=cost_over_time,
                     algo_footprint=algorithm_footprints,
                     param_importance=param_imp,
                     pimp_sort_table_by=pimp_sort_table_by,
                     feature_analysis=feature_analysis)


def entry_point():
    cave = CaveCLI()
    cave.main_cli()
