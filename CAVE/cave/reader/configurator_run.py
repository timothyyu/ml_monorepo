import logging

from smac.facade.smac_facade import SMAC
from smac.optimizer.objective import average_cost
from smac.runhistory.runhistory import RunHistory, DataOrigin

from cave.reader.smac3_reader import SMAC3Reader
from cave.reader.smac2_reader import SMAC2Reader
from cave.reader.csv_reader import CSVReader


class ConfiguratorRun(SMAC):
    """
    ConfiguratorRuns load and maintain information about individual configurator
    runs. There are three supported formats: SMAC3, SMAC2 and CSV
    This class is responsible for providing a scenario, a runhistory and a
    trajectory and handling original/validated data appropriately.
    """
    def __init__(self,
                 folder: str,
                 ta_exec_dir: str,
                 file_format: str='SMAC3',
                 validation_format: str='NONE'):
        """Initialize scenario, runhistory and incumbent from folder, execute
        init-method of SMAC facade (so you could simply use SMAC-instances instead)

        Parameters
        ----------
        folder: string
            output-dir of this run
        ta_exec_dir: string
            if the execution directory for the SMAC-run differs from the cwd,
            there might be problems loading instance-, feature- or PCS-files
            in the scenario-object. since instance- and PCS-files are necessary,
            specify the path to the execution-dir of SMAC here
        file_format: string
            from [SMAC2, SMAC3, CSV]
        validation_format: string
            from [SMAC2, SMAC3, CSV, NONE], in which format to look for validated data
        """
        self.logger = logging.getLogger("cave.ConfiguratorRun.{}".format(folder))
        self.cave = None  # Set if we analyze configurators that use budgets

        self.folder = folder
        self.ta_exec_dir = ta_exec_dir
        self.file_format = file_format
        self.validation_format = validation_format

        self.logger.debug("Loading from \'%s\' with ta_exec_dir \'%s\'.",
                          folder, ta_exec_dir)
        if validation_format == 'NONE':
            validation_format = None

        def get_reader(name):
            if name == 'SMAC3':
                return SMAC3Reader(folder, ta_exec_dir)
            elif name == 'BOHB':
                self.logger.debug("File format is BOHB, assmuming data was converted to SMAC3-format using "
                                  "HpBandSter2SMAC from cave.utils.converter.hpbandster2smac.")
                return SMAC3Reader(folder, ta_exec_dir)
            elif name == 'SMAC2':
                return SMAC2Reader(folder, ta_exec_dir)
            elif name == 'CSV':
                return CSVReader(folder, ta_exec_dir)
            else:
                raise ValueError("%s not supported as file-format" % name)
        self.reader = get_reader(file_format)

        self.scen = self.reader.get_scenario()
        self.original_runhistory = self.reader.get_runhistory(self.scen.cs)
        self.validated_runhistory = None

        self.traj = self.reader.get_trajectory(cs=self.scen.cs)
        self.default = self.scen.cs.get_default_configuration()
        self.incumbent = self.traj[-1]['incumbent']
        self.train_inst = self.scen.train_insts
        self.test_inst = self.scen.test_insts
        self._check_rh_for_inc_and_def(self.original_runhistory, 'original runhistory')

        if validation_format:
            self.logger.debug('Using format %s for validation', validation_format)
            reader = get_reader(validation_format)
            reader.scen = self.scen
            self.validated_runhistory = reader.get_validated_runhistory(self.scen.cs)
            self._check_rh_for_inc_and_def(self.validated_runhistory, 'validated runhistory')
            self.logger.info("Found validated runhistory for \"%s\" and using "
                             "it for evaluation. #configs in validated rh: %d",
                             self.folder, len(self.validated_runhistory.config_ids))

        self.combined_runhistory = RunHistory(average_cost)
        self.combined_runhistory.update(self.original_runhistory,
                                        origin=DataOrigin.INTERNAL)
        if self.validated_runhistory:
            self.combined_runhistory.update(self.validated_runhistory,
                                            origin=DataOrigin.EXTERNAL_SAME_INSTANCES)

        self.epm_runhistory = RunHistory(average_cost)
        self.epm_runhistory.update(self.combined_runhistory)

        # Initialize SMAC-object
        super().__init__(scenario=self.scen, runhistory=self.combined_runhistory)  # restore_incumbent=incumbent)
        # TODO use restore, delete next line
        self.solver.incumbent = self.incumbent

    def get_incumbent(self):
        return self.solver.incumbent

    def _check_rh_for_inc_and_def(self, rh, name=''):
        """
        Check if default and incumbent are evaluated on all instances in this rh

        Parameters
        ----------
        rh: RunHistory
            runhistory to be checked
        name: str
            name for logging-purposes

        Returns
        -------
        return_value: bool
            False if either inc or def was not evaluated on all
            train/test-instances
        """
        return_value = True
        for c_name, c in [("default", self.default), ("inc", self.incumbent)]:
            runs = rh.get_runs_for_config(c)
            evaluated = set([inst for inst, seed in runs])
            for i_name, i in [("train", self.train_inst),
                              ("test", self.test_inst)]:
                not_evaluated = set(i) - evaluated
                if len(not_evaluated) > 0:
                    self.logger.debug("RunHistory %s only evaluated on %d/%d %s-insts "
                                      "for %s in folder %s",
                                      name, len(i) - len(not_evaluated), len(i),
                                      i_name, c_name, self.folder)
                    return_value = False
        return return_value
