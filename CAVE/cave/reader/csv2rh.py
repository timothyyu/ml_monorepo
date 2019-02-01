import os
import warnings
import logging
import csv
from typing import Union

import pandas as pd
import numpy as np

from smac.runhistory.runhistory import RunHistory, DataOrigin
from smac.optimizer.objective import average_cost, _cost
from smac.utils.io.input_reader import InputReader
from smac.tae.execute_ta_run import StatusType

from ConfigSpace.util import deactivate_inactive_hyperparameters, fix_types
from ConfigSpace import Configuration, ConfigurationSpace
from ConfigSpace.hyperparameters import UniformFloatHyperparameter, CategoricalHyperparameter
from ConfigSpace.read_and_write import pcs

from cave.utils.io import load_csv_to_pandaframe

__author__ = "Joshua Marben"
__copyright__ = "Copyright 2018, ML4AAD"
__license__ = "3-clause BSD"
__maintainer__ = "Joshua Marben"
__email__ = "joshua.marben@neptun.uni-freiburg.de"

class CSV2RH(object):
    def __init__(self):
        pass

    def read_csv_to_rh(self, data,
                       cs:Union[None, str, ConfigurationSpace]=None,
                       id_to_config:Union[None, dict]=None,
                       train_inst:Union[None, str, list]=None,
                       test_inst:Union[None, str, list]=None,
                       instance_features:Union[None, str, dict]=None,
                       logger=None,
                       seed=42):
        """ Interpreting a .csv-file as runhistory.
        Valid values for the header of the csv-file/DataFrame are:
        ['seed', 'cost', 'time', 'status', 'config_id', 'instance_id'] or any
        parameter- or instance-feature-names.

        Parameters
        ----------
        data: str or pd.DataFrame
            either string to csv-formatted runhistory-file or DataFrame
            containing the same information
        cs: str or ConfigurationSpace
            config-space to use for this runhistory
        id_to_config: dict
            mapping ids to Configuration-objects
        train_inst: str or list[str]
            train instances or path to file
        test_inst: str or list[str]
            test instances or path to file
        instance_features: str or dict
            instance features as dict mapping instance-ids to feature-array or
            file to appropriately formatted instance-feature-file

        Returns:
        --------
        rh: RunHistory
            runhistory with all the runs from the csv-file
        """
        self.logger = logging.getLogger('cave.utils.csv2rh')
        self.input_reader = InputReader()
        self.train_inst = input_reader.read_instance_file(train_inst) if type(train_inst) == str else train_inst
        self.test_inst =  input_reader.read_instance_file(test_inst) if type(test_inst) == str else test_inst
        feature_names = []  # names of instance-features
        if type(instance_features) == str:
            feature_names, instance_features = input_reader.read_instance_features_file(instance_features)

        # Read in data
        if isinstance(data, str):
            self.logger.debug("Detected path for csv-file (\'%s\')", data)
            data = load_csv_to_pandaframe(data, self.logger, apply_numeric=False)

        # Expecting header as described in docstring
        self.valid_values = ['seed', 'cost', 'time', 'status', 'config_id', 'instance_id']

        if isinstance(cs, str):
            self.logger.debug("Reading PCS from %s", cs)
            with open(cs, 'r') as fh:
                cs = pcs.read(fh)
        elif not cs:
            # No config-space provided, create from columns
            if self.id_to_config:
                cs = np.random.choice(list(self.id_to_config.values())).configuration_space
            else:
                parameters = set(data.columns)
                parameters -= set(self.valid_values)
                parameters -= set(feature_names)
                parameters = list(parameters)
            cs = self.create_cs_from_pandaframe(data[parameters])

        parameters = cs.get_hyperparameter_names()
        if not feature_names and not 'instance_id' in data.columns:
            feature_names = [c for c in data.columns if
                             not c.lower() in self.valid_values and
                             not c in parameters]

        for c in set(self.valid_values).intersection(set(data.columns)):
            # Cast to numeric
            data[c] = data[c].apply(pd.to_numeric, errors='ignore')

        data, id_to_config = self.extract_configs(data, cs, id_to_config)
        data, id_to_inst_feats = self.extract_instances(data, feature_names,
                                                        instance_features)
        self.logger.debug("Found: seed=%s, cost=%s, time=%s, status=%s",
                          'seed' in data.columns, 'cost' in data.columns,
                          'time' in data.columns, 'status' in data.columns)

        # Create RunHistory
        rh = RunHistory(average_cost)
        def add_to_rh(row):
            new_status = self._interpret_status(row['status']) if 'status' in row else StatusType.SUCCESS
            rh.add(config=id_to_config[row['config_id']],
                   cost=row['cost'],
                   time=row['time'] if 'time' in row else -1,
                   status=new_status,
                   instance_id=row['instance_id'] if 'instance_id' in row else None,
                   seed=row['seed'] if 'seed' in row else None,
                   additional_info=None,
                   origin=DataOrigin.INTERNAL)

        data.apply(add_to_rh, axis=1)
        return rh

    def create_cs_from_pandaframe(self, data):
        # TODO use from pyimp after https://github.com/automl/ParameterImportance/issues/72 is implemented
        warnings.warn("No parameter configuration space (pcs) provided! "
                      "Interpreting all parameters as floats. This might lead "
                      "to suboptimal analysis.", RuntimeWarning)
        self.logger.debug("Interpreting as parameters: %s", data.columns)
        minima = data.min()  # to define ranges of hyperparameter
        maxima = data.max()
        cs = ConfigurationSpace(seed=42)
        for p in data.columns:
            cs.add_hyperparameter(UniformFloatHyperparameter(p,
                                  lower=minima[p] - 1, upper=maxima[p] + 1))

    def _interpret_status(self, status, types=None):
        """
        Parameters
        ----------
        status: str
            status-string
        types: dict[str:StatusType]
            optional, mapping to use

        Returns
        -------
        status: StatusType
            interpreted status-type
        """
        if not types:
            types = {"SAT" : StatusType.SUCCESS,
                     "UNSAT" : StatusType.SUCCESS,
                     "SUCCESS" : StatusType.SUCCESS,
                     "STATUSTYPE.SUCCESS" : StatusType.SUCCESS,
                     "TIMEOUT" : StatusType.TIMEOUT,
                     "STATUSTYPE.TIMEOUT" : StatusType.TIMEOUT,
                     "CRASHED" : StatusType.CRASHED,
                     "STATUSTYPE.CRASHED" : StatusType.CRASHED,
                     "MEMOUT" : StatusType.MEMOUT,
                     "STATUSTYPE.MEMOUT" : StatusType.MEMOUT,
                     "ABORT" : StatusType.ABORT,
                     "STATUSTYPE.ABORT" : StatusType.ABORT,
                     }

        status = status.strip().upper()
        if status in types:
            status = types[status]
        else:
            self.logger.warning("Could not parse %s as a status. Valid values "
                                "are: %s. Treating as CRASHED run.", status,
                                types.keys())
            status = StatusType.CRASHED
        return status

    def extract_configs(self, data, cs: ConfigurationSpace, id_to_config=None):
        """After completion, every unique configuration in the data will have a
        corresponding id in the data-frame.
        The data-frame is expected to either contain a column for config-id OR
        columns for each individual hyperparameter. Parameter-names will be used
        from the provided configspace.
        If a mapping of ids to configurations already exists, it will be used.

        Parameters
        ----------
        data: pd.DataFrame
            pandas dataframe containing either a column called `config_id` or a
            column for every individual parameter
        cs: ConfigurationSpace
            optional, if provided the `parameters`-argument will be ignored
        id_to_config: dict[int:Configuration]
            optional, mapping ids to Configurations (necessary when using
            `config_id`-column)

        Returns
        -------
        data: pd.DataFrame
            if no config-id-columns was there before, there is one now.
        id_to_config: dict
            mapping every id to a configuration
        """
        if id_to_config:
            config_to_id = {conf : name for name, conf in id_to_config.items()}
        else:
            id_to_config = {}
            config_to_id = {}

        parameters = cs.get_hyperparameter_names()

        if 'config_id' in data.columns and not id_to_config:
            raise ValueError("When defining configs with \"config_id\" "
                             "in header, you need to provide the argument "
                             "\"configurations\" to the CSV2RH-object - "
                             "either as a dict, mapping the id's to "
                             "Configurations or as a path to a csv-file "
                             "containing the necessary information.")

        if not 'config_id' in data.columns:
            # Map to configurations
            ids_in_order = []
            data['config_id'] = -1
            def add_config(row):
                values = {name : row[name] for name in parameters if
                            row[name] != ''}
                config = deactivate_inactive_hyperparameters(fix_types(values, cs), cs)
                if not config in config_to_id:
                    config_to_id[config] = len(config_to_id)
                row['config_id'] = config_to_id[config]
                return row
            data = data.apply(add_config, axis=1)
            id_to_config = {conf : name for name, conf in config_to_id.items()}

        # Check whether all config-ids are present
        if len(set(data['config_id']) - set(id_to_config.keys())) > 0:
            raise ValueError("config id %s cannot be identified (is your "
                             "configurations.csv complete?")

        return data, id_to_config

    def extract_instances(self, data, feature_names, features):
        """After completion, every unique instance in the data will have a
        corresponding id in the data-frame.
        The data-frame is expected to either contain a column for instance-id OR
        columns for each individual instance-feature. Parameter-names will be used
        from the provided configspace.
        If a mapping of ids to configurations already exists, it will be used.

        Parameters
        ----------
        data: pd.DataFrame
            pandas dataframe containing either a column called `instance_id` or a
            column for every individual instance-features
        feature_names: list[str]
            optional, list of feature-names
        features: dict[int:np.array]
            optional, mapping ids to instance-feature vectors (necessary when using
            `instance_id`-column)

        Returns
        -------
        data: pd.DataFrame
            if no instance_id-columns was there before, there is one now.
        id_to_inst_feats: dict
            mapping every id to instance-features
        """
        id_to_inst_feats = {}
        inst_feats_to_id = {}
        if features:
            id_to_inst_feats = {i : tuple([str(f) for f in feat]) for i, feat in
                                features.items()}
            inst_feats_to_id = {feat : i for i, feat in
                                id_to_inst_feats.items()}
        if 'instance_id' in data.columns and not features:
            raise ValueError("Instances defined via \'instance_id\'-column, "
                             "but no instance features available.")
        elif not 'instance_id' in data.columns and feature_names:
            # Add new column for instance-ids
            data['instance_id'] = -1
            self.old = None
            def add_instance(row):
                row_features = tuple([str(row[idx]) for idx in feature_names])
                if not row_features in inst_feats_to_id:
                    new_id = len(inst_feats_to_id)
                    inst_feats_to_id[row_features] = new_id
                    id_to_inst_feats[new_id] = features
                row['instance_id'] = inst_feats_to_id[row_features]
                self.old = row_features
                return row
            data = data.apply(add_instance, axis=1)
        else:
            self.logger.info("No instances detected.")
        id_to_inst_feats = {i : np.array(f).astype('float64') for i, f in
                            id_to_inst_feats.items()}
        return data, id_to_inst_feats
