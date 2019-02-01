import sys
import os
import numpy as np
import logging
import shutil
from contextlib import contextmanager

import unittest
from unittest import mock

from smac.optimizer.objective import average_cost
from smac.scenario.scenario import Scenario
from smac.runhistory.runhistory import RunHistory
from smac.utils.io.traj_logging import TrajLogger
from smac.utils.validate import Validator

from cave.cave_cli import CaveCLI
from cave.cavefacade import CAVE

@contextmanager
def changedir(newdir):
    olddir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(olddir)

class TestCLI(unittest.TestCase):

    def setUp(self):
        base_directory = os.path.split(__file__)[0]
        base_directory = os.path.abspath(
            os.path.join(base_directory, '..', '..'))
        self.current_dir = os.getcwd()
        os.chdir(base_directory)

        self.cavecli = CaveCLI()
        self.cave_output_dir = "test/test_files/output_tmp"
        self.def_args_off = ["--parameter_importance", "none", "--feature_analysis", "none",
                             #"--no_tabular_analysis",
                             "--no_ecdf", "--no_scatter_plots", "--no_cost_over_time",
                             "--no_configurator_footprint", "--no_parallel_coordinates", "--no_algorithm_footprints",
                             "--output", self.cave_output_dir]

        self.output_dirs = [self.cave_output_dir]

    def tearDown(self):
        for output_dir in self.output_dirs:
            if output_dir:
                shutil.rmtree(output_dir, ignore_errors=True)
        os.chdir(self.current_dir)

    def test_run_from_base(self):
        """
        Testing basic CLI from base.
        """
        test_folders = [["test/example_output/example_output/*"],
                        ["test/example_output/example_output/run_1",
                         "test/example_output/example_output/run_2"],
                        ["test/example_output/example_output/* ",
                         "test/example_output/example_output/run_2"]
                       ]

        for folders in test_folders:
            # Run from base-path
            testargs = ["scripts/cave", "--folders"]
            testargs.extend(folders)
            testargs.extend(self.def_args_off)
            # No ta_exec -> scenario cannot be loaded
            with mock.patch.object(sys, 'argv', testargs):
                self.assertRaises(SystemExit, self.cavecli.main_cli)
            testargs.extend(["--ta_exec", "test/example_output"])
            with mock.patch.object(sys, 'argv', testargs):
                with mock.patch.object(CAVE, '__init__', lambda *x, **y: None):
                    with mock.patch.object(CAVE, 'analyze', lambda *x, **y: None):
                        self.cavecli.main_cli()

    def test_run_from_relative(self):
        """
        Testing basic CLI from relative folder
        """
        test_folders = [["example_output/*"],
                        ["example_output/run_1",
                         "example_output/run_2"],
                        ["example_output/* ",
                         "example_output/run_2"]
                       ]

        with changedir("test/example_output"):
            for folders in test_folders:
                # Run from base-path
                testargs = ["../../scripts/cave", "--folders"]
                testargs.extend(folders)
                testargs.extend(self.def_args_off)
                with mock.patch.object(sys, 'argv', testargs):
                    with mock.patch.object(CAVE, '__init__', lambda *x, **y: None):
                        with mock.patch.object(CAVE, 'analyze', lambda *x, **y: None):
                            self.cavecli.main_cli()
                # Wrong ta_exec -> scenario cannot be loaded
                testargs.extend(["--ta_exec", "example_output"])
                with mock.patch.object(sys, 'argv', testargs):
                    self.assertRaises(SystemExit, self.cavecli.main_cli)

    def test_exceptions(self):
        test_folder = "test/example_output/example_output/run_1"

        testargs = ["scripts/cave",
                    "--folders", test_folder,
                    "--ta_exec", "test/example_output",
                    "--pimp_sort_table_by", "fanova",
                    "--parameter_importance", "ablation"]
        with mock.patch.object(sys, 'argv', testargs):
            self.assertRaises(ValueError, self.cavecli.main_cli)
