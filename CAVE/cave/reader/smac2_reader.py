import re
import os
import shutil
import csv
import numpy as np
import pandas as pd

from ConfigSpace import Configuration, c_util
from ConfigSpace.hyperparameters import IntegerHyperparameter, FloatHyperparameter
from ConfigSpace.util import deactivate_inactive_hyperparameters, fix_types
from smac.optimizer.objective import average_cost
from smac.utils.io.input_reader import InputReader
from smac.runhistory.runhistory import RunKey, RunValue, RunHistory, DataOrigin
from smac.utils.io.traj_logging import TrajLogger
from smac.scenario.scenario import Scenario

from cave.reader.base_reader import BaseReader, changedir
from cave.reader.csv2rh import CSV2RH
from cave.utils.io import load_csv_to_pandaframe

class SMAC2Reader(BaseReader):
    """Reader for SMAC2-output.
    The expected output-structure in the specified folder is:
     self.folder/
      smac-output/
       aclib/
         state-run1/
           - scenario.txt                # scenario
           - runs_and_results(...).csv   # runhistory
           - paramstrings(...).csv       # runhistory
           - traj-run-(...)              # trajectory
      validate-time-train/              # optional, if validation has been beformed
       - validationCallStrings(...).csv
       - validationRunResultLineMatrix(...).csv
      validate-time-test/               # optional, if validation has been beformed
       - validationCallStrings(...).csv
       - validationRunResultLineMatrix(...).csv
    """

    def get_scenario(self):
        run_1_existed = os.path.exists('run_1')
        in_reader = InputReader()
        # Create Scenario (disable output_dir to avoid cluttering)
        scen_fn = os.path.join(self.folder, 'smac-output/aclib/state-run1/scenario.txt')
        scen_dict = in_reader.read_scenario_file(scen_fn)
        scen_dict['output_dir'] = ""
        with changedir(self.ta_exec_dir):
            self.logger.debug("Creating scenario from \"%s\"", self.ta_exec_dir)
            scen = Scenario(scen_dict)

        if (not run_1_existed) and os.path.exists('run_1'):
            shutil.rmtree('run_1')
        self.scen = scen
        return scen

    def get_runhistory(self, cs):
        """
        Expects the following files:

        - `self.folder/smac-output/aclib/state-run1/runs_and_results(...).csv`
        - `self.folder/smac-output/aclib/state-run1/paramstrings(...).csv`

        Returns
        -------
        rh: RunHistory
            runhistory
        """
        folder = os.path.join(self.folder, 'smac-output/aclib/state-run1')
        rh_fn = re.search(r'runs\_and\_results.*?\.csv', str(os.listdir(folder)))
        if not rh_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'runs_and_results\'-file could be found "
                                    "in %s" % folder)
        rh_fn = os.path.join(folder, rh_fn.group())
        self.logger.debug("Runhistory loaded as csv from %s", rh_fn)
        configs_fn = re.search(r'paramstrings.*?\.txt', str(os.listdir(folder)))
        if not configs_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'paramstrings\'-file could be found "
                                    "in %s" % folder)
        configs_fn = os.path.join(folder, configs_fn.group())
        self.logger.debug("Configurations loaded from %s", configs_fn)
        # Translate smac2 to csv
        csv_data = load_csv_to_pandaframe(rh_fn, self.logger)
        data = pd.DataFrame()
        data["config_id"] = csv_data["Run History Configuration ID"]
        data["instance_id"] = csv_data["Instance ID"].apply(lambda x:
                self.scen.train_insts[x-1])
        data["seed"] = csv_data["Seed"]
        data["time"] = csv_data["Runtime"]
        if self.scen.run_obj == 'runtime':
            data["cost"] = csv_data["Runtime"]
        else:
            data["cost"] = csv_data["Run Quality"]
        data["status"] = csv_data["Run Result"]

        # Load configurations
        with open(configs_fn, 'r') as csv_file:
            csv_data = list(csv.reader(csv_file, delimiter=',',
                                       skipinitialspace=True))
        id_to_config = {}
        for row in csv_data:
            config_id = int(re.match(r'^(\d*):', row[0]).group(1))
            params = [re.match(r'^\d*: (.*)', row[0]).group(1)]
            params.extend(row[1:])
            #self.logger.debug(params)
            matches = [re.match(r'(.*)=\'(.*)\'', p) for p in params]
            values = {m.group(1) : m.group(2) for m in matches}
            values = deactivate_inactive_hyperparameters(fix_types(values, cs),
                                                         cs).get_dictionary()
            id_to_config[config_id] = Configuration(cs, values=values)
        self.id_to_config = id_to_config
        names, feats = self.scen.feature_names, self.scen.feature_dict
        rh = CSV2RH().read_csv_to_rh(data,
                                     cs=cs,
                                     id_to_config=id_to_config,
                                     train_inst=self.scen.train_insts,
                                     test_inst=self.scen.test_insts,
                                     instance_features=feats)

        return rh

    def get_validated_runhistory(self, cs):
        """
        Expects the following files:

        - `self.folder/validate-time-train/validationCallStrings(...).csv`
        - `self.folder/validate-time-train/validationRunResultLineMatrix(...).csv`
        - `self.folder/validate-time-test/validationCallStrings(...).csv`
        - `self.folder/validate-time-test/validationRunResultLineMatrix(...).csv`

        Returns
        -------
        validated_rh: RunHistory
            validated runhistory
        """
        self.logger.debug("Loading validation-data")
        folder = os.path.join(self.folder, 'validate-time-train')
        configs_fn = re.search(r'validationCallStrings.*?\.csv', str(os.listdir(folder)))
        if not configs_fn:
            self.logger.warning("Specified validation_format is \'SMAC2\', but no "
                                "\'validationCallStrings(...).csv\'-file could be found "
                                "in %s" % folder)
            return
        configs_fn = os.path.join(folder, configs_fn.group())

        results_fn = re.search(r'validationRunResultLineMatrix.*?\.csv',
                str(os.listdir(folder)))
        if not results_fn:
            self.logger.warning("Specified validation_format is \'SMAC2\', but no "
                                "\'validationRunResultLineMatrix(...).csv\'-file could be found "
                                "in %s" % folder)
            return
        results_fn = os.path.join(folder, results_fn.group())

        self.logger.debug("Configurations loaded from %s", configs_fn)
        self.logger.debug("Runhistory loaded as csv from %s", results_fn)

        # Load configurations
        csv_data = load_csv_to_pandaframe(configs_fn, self.logger, False)
        id_to_config = {}
        for idx, row in csv_data.iterrows():
            config_id = int(row[0])
            configuration = row[1].split()
            params = [p.lstrip('-') for p in configuration[::2]]  # all odds
            values = [v.strip('\'') for v in configuration[1::2]]  # all evens
            param_values = dict(zip(params, values))
            param_values = deactivate_inactive_hyperparameters(fix_types(param_values, cs),
                                                         cs).get_dictionary()
            id_to_config[config_id] = Configuration(cs, values=param_values)

        names, feats = self.scen.feature_names, self.scen.feature_dict

        # Translate smac2-validation (RunResultString-matrix) to csv
        csv_data = load_csv_to_pandaframe(results_fn, self.logger, delimiter='\",\"')
        data = pd.DataFrame()
        for idx, row in csv_data.iterrows():
            instance, seed = row[0], row[1]
            for column in csv_data.columns[2:]:
                config_id = int(re.match(r'^Run result line of validation config #(\d*)$', column).group(1))
                result = [e.strip() for e in row[column].split(',')]
                data = data.append({"config_id" : config_id,
                                    "instance_id" : instance,
                                    "seed" : seed,
                                    "time" : result[1],
                                    "cost" : result[1] if self.scen.run_obj == 'runtime' else result[3],
                                    "status" : result[0]},
                                    ignore_index=True)

        rh = CSV2RH().read_csv_to_rh(data,
                                     cs=cs,
                                     id_to_config=id_to_config,
                                     train_inst=self.scen.train_insts,
                                     test_inst=self.scen.test_insts,
                                     instance_features=feats)

        self.logger.debug("%d datapoints for %d configurations found in validated rh.",
                          len(rh.data), len(rh.get_all_configs()))

        return rh

    def get_trajectory(self, cs):
        """Expects the following files:

        - `self.folder/smac-output/aclib/state-run1/traj-run-(...).csv`
        """
        folder = os.path.join(self.folder, "smac-output/aclib/state-run1")
        traj_fn = re.search(r'traj-run-\d*.txt', str(os.listdir(os.path.join(folder, '..'))))
        if not traj_fn:
            raise FileNotFoundError("Specified format is \'SMAC2\', but no "
                                    "\'../traj-run\'-file could be found "
                                    "in %s" % folder)
        traj_fn = os.path.join(folder, '..', traj_fn.group())
        with open(traj_fn, 'r') as csv_file:
            csv_data = list(csv.reader(csv_file, delimiter=',',
                                       skipinitialspace=True))
        header, csv_data = csv_data[0][:-1], np.array([csv_data[1:]])[0]
        csv_data = pd.DataFrame(np.delete(csv_data, np.s_[5:], axis=1), columns=header)
        csv_data = csv_data.apply(pd.to_numeric, errors='ignore')
        traj = []
        def add_to_traj(row):
            new_entry = {}
            new_entry['cpu_time'] = row['CPU Time Used']
            new_entry['total_cpu_time'] = None
            new_entry["wallclock_time"] = row['Wallclock Time']
            new_entry["evaluations"] = -1
            new_entry["cost"] = row["Estimated Training Performance"]
            new_entry["incumbent"] = self.id_to_config[row["Incumbent ID"]]
            traj.append(new_entry)
        csv_data.apply(add_to_traj, axis=1)
        return traj

