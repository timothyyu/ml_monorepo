from collections import OrderedDict

from pimp.importance.importance import Importance
from ConfigSpace.configuration_space import Configuration

from cave.analyzer.base_analyzer import BaseAnalyzer

class CaveParameterImportance(BaseAnalyzer):

    def __init__(self,
                 pimp: Importance,
                 incumbent: Configuration,
                 output_dir: str):
        """Calculate parameter-importance using the PIMP-package.

        Parameters
        ----------
        pimp: Importance
            parameter importance object for fanova, ablation, etc

        Returns
        -------
        importance: pimp.Importance
            importance object with evaluated data
        """
        # Evaluate parameter importance
        self.pimp = pimp
        self.incumbent = incumbent
        self.output_dir = output_dir
        # To be set
        self.param_imp = OrderedDict()

    def parameter_importance(self, modus):
        """
        modus: str
            modus for parameter importance, from
            [forward-selection, ablation, fanova, lpi]
        """
        self.logger.info("... parameter importance {}".format(modus))
        self.pimp.evaluate_scenario([modus], self.output_dir)
        self.param_imp[modus] = self.pimp.evaluator.evaluated_parameter_importance

