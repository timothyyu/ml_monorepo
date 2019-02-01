import re
import os
import shutil
import csv
import numpy as np
import pandas as pd

from ConfigSpace import Configuration, c_util
from ConfigSpace.hyperparameters import IntegerHyperparameter, FloatHyperparameter
from smac.optimizer.objective import average_cost
from smac.utils.io.input_reader import InputReader
from smac.runhistory.runhistory import RunKey, RunValue, RunHistory, DataOrigin
from smac.utils.io.traj_logging import TrajLogger
from smac.scenario.scenario import Scenario

from cave.reader.base_reader import BaseReader, changedir
from cave.reader.csv2rh import CSV2RH
from cave.utils.io import load_csv_to_pandaframe, load_config_csv

class CSVReader(BaseReader):

    def get_scenario(self):
        run_1_existed = os.path.exists('run_1')
        in_reader = InputReader()
        # Create Scenario (disable output_dir to avoid cluttering)
        scen_fn = os.path.join(self.folder, 'scenario.txt')
        scen_dict = in_reader.read_scenario_file(scen_fn)
        scen_dict['output_dir'] = ""
        with changedir(self.ta_exec_dir):
            self.logger.debug("Creating scenario from \"%s\"", self.ta_exec_dir)
            scen = Scenario(scen_dict)

        if (not run_1_existed) and os.path.exists('run_1'):
            shutil.rmtree('run_1')
        self.scen = scen
        return scen

    def _get_runhistory(self, cs, filename='runhistory.csv'):
        rh_fn = os.path.join(self.folder, filename)
        if not os.path.exists(rh_fn):
            raise FileNotFoundError("Specified format is \'CSV\', but no "
                                    "\'%s\'-file could be found "
                                    "in %s" % (filename, self.folder))
        self.logger.debug("Runhistory loaded as csv from %s", rh_fn)
        configs_fn = os.path.join(self.folder, 'configurations.csv')
        if os.path.exists(configs_fn):
            self.logger.debug("Found \'configurations.csv\' in %s." % self.folder)
            self.id_to_config = load_config_csv(configs_fn, cs, self.logger)[1]
        else:
            self.logger.debug("No \'configurations.csv\' in %s." % self.folder)
            self.id_to_config = {}

        rh = CSV2RH().read_csv_to_rh(rh_fn,
                                     cs=cs,
                                     id_to_config=self.id_to_config,
                                     train_inst=self.scen.train_insts,
                                     test_inst=self.scen.test_insts,
                                     instance_features=self.scen.feature_dict,
                                     )
        if not self.id_to_config:
            self.id_to_config = rh.ids_config

        return rh

    def get_runhistory(self, cs):
        """Reads runhistory in csv-format:

        +--------------------+--------------------+------+------+------+--------+
        |      config_id     |  instance_id       | cost | time | seed | status |
        +====================+====================+======+======+======+========+
        | name of config 1   | name of instance 1 | ...  |  ... | ...  |  ...   |
        +--------------------+--------------------+------+------+------+--------+
        |         ...        |          ...       | ...  |  ... | ...  |  ...   |
        +--------------------+--------------------+------+------+------+--------+

        where config_id and instance_id can also be replaced by columns for the
        individual parameters/instance features

        Returns
        -------
        rh: RunHistory
            runhistory
        """
        return self._get_runhistory(cs, 'runhistory.csv')

    def get_validated_runhistory(self, cs):
        """Reads runhistory in csv-format:

        +--------------------+--------------------+------+------+------+--------+
        |      config_id     |  instance_id       | cost | time | seed | status |
        +====================+====================+======+======+======+========+
        | name of config 1   | name of instance 1 | ...  |  ... | ...  |  ...   |
        +--------------------+--------------------+------+------+------+--------+
        |         ...        |          ...       | ...  |  ... | ...  |  ...   |
        +--------------------+--------------------+------+------+------+--------+

        where config_id and instance_id can also be replaced by columns for the
        individual parameters/instance features

        Returns
        -------
        rh: RunHistory
            validated runhistory
        """
        return self._get_runhistory(cs, 'validated_runhistory.csv')

    def get_trajectory(self, cs):
        """Reads `self.folder/trajectory.csv`, expected format:

        +----------+------+----------------+-------------+-----------+
        | cpu_time | cost | wallclock_time | evaluations | config_id |
        +==========+======+================+=============+===========+
        | ...      | ...  | ...            | ...         | ...       |
        +----------+------+----------------+-------------+-----------+

        or

        +----------+------+----------------+-------------+------------+------------+-----+
        | cpu_time | cost | wallclock_time | evaluations | parameter1 | parameter2 | ... |
        +==========+======+================+=============+============+============+=====+
        | ...      | ...  | ...            | ...         | ...        | ...        | ... |
        +----------+------+----------------+-------------+------------+------------+-----+
        """
        traj_fn = os.path.join(self.folder, 'trajectory.csv')
        if not os.path.exists(traj_fn):
            self.logger.warning("Specified format is \'CSV\', but no "
                                "\'../trajectory\'-file could be found "
                                "at %s" % traj_fn)

        csv_data = load_csv_to_pandaframe(traj_fn, self.logger,
                                          apply_numeric=False)
        traj = []
        csv_data, configs = CSV2RH().extract_configs(csv_data, cs, self.id_to_config)
        def add_to_traj(row):
            new_entry = {}
            new_entry['cpu_time'] = float(row['cpu_time'])
            new_entry['total_cpu_time'] = None
            new_entry["wallclock_time"] = float(row['wallclock_time'])
            new_entry["evaluations"] = int(row['evaluations'])
            new_entry["cost"] = float(row["cost"])
            new_entry["incumbent"] = self.id_to_config[row["config_id"]]
            traj.append(new_entry)
        csv_data.apply(add_to_traj, axis=1)
        return traj
