"""
An example for the usage of SMAC within Python.
We optimize a simple SVM on the IRIS-benchmark.
"""

import logging
import numpy as np
from sklearn import svm, datasets
from sklearn.model_selection import cross_val_score

# Import ConfigSpace and different types of parameters
from smac.configspace import ConfigurationSpace
from ConfigSpace.hyperparameters import CategoricalHyperparameter, \
    UniformFloatHyperparameter, UniformIntegerHyperparameter
from ConfigSpace.conditions import InCondition

# Import SMAC-utilities
from smac.tae.execute_func import ExecuteTAFuncDict
from smac.scenario.scenario import Scenario
from smac.facade.smac_facade import SMAC

def svm_from_cfg_with_instance(cfg, instance, seed):
    """ Creates a SVM based on a configuration and evaluates it on the
    specified instance of the iris-dataset. Uses the rest of the dataset as
    train and the specified instance as test. We are really hyperoptimizing
    here, so this is more complicated than necessary.

    Parameters:
    -----------
    cfg: Configuration (ConfigSpace.ConfigurationSpace.Configuration)
        Configuration containing the parameters.
        Configurations are indexable!
    instance: int
        Index of instance to evaluate
    seed: int
        random state

    Returns:
    --------
    A crossvalidated mean score for
    """
    # For deactivated parameters, the configuration stores None-values.
    # This is not accepted by the SVM, so we remove them.
    cfg = {k : cfg[k] for k in cfg if cfg[k]}
    # We translate boolean values:
    cfg["shrinking"] = True if cfg["shrinking"] == "true" else False
    # And for gamma, we set it to a fixed value or to "auto" (if used)
    if "gamma" in cfg:
        cfg["gamma"] = cfg["gamma_value"] if cfg["gamma"] == "value" else "auto"
        cfg.pop("gamma_value", None)  # Remove "gamma_value"

    data = iris.data
    target = iris.target

    test_data = data[instance]
    test_target = target[instance]
    train_data = data[:instance] + data[instance+1:]
    train_target = target[:instance] + target[instance+1:]

    clf = svm.SVC(**cfg, random_state=seed)
    clf.fit(train_data, train_target)
    return 1-int(clf.predict(test_data)==test_target)

def optimize():
    # We load the iris-dataset (a widely used benchmark)
    iris = datasets.load_iris()

    #logger = logging.getLogger("SVMExample")
    logging.basicConfig(level=logging.INFO)  # logging.DEBUG for debug output

    # Build Configuration Space which defines all parameters and their ranges
    cs = ConfigurationSpace()

    # We define a few possible types of SVM-kernels and add them as "kernel" to our cs
    kernel = CategoricalHyperparameter("kernel", ["linear", "rbf", "poly", "sigmoid"], default="poly")
    cs.add_hyperparameter(kernel)

    # There are some hyperparameters shared by all kernels
    C = UniformFloatHyperparameter("C", 0.001, 1000.0, default=1.0)
    shrinking = CategoricalHyperparameter("shrinking", ["true", "false"], default="true")
    cs.add_hyperparameters([C, shrinking])

    # Others are kernel-specific, so we can add conditions to limit the searchspace
    degree = UniformIntegerHyperparameter("degree", 1, 5, default=3)     # Only used by kernel poly
    coef0 = UniformFloatHyperparameter("coef0", 0.0, 10.0, default=0.0)  # poly, sigmoid
    cs.add_hyperparameters([degree, coef0])
    use_degree = InCondition(child=degree, parent=kernel, values=["poly"])
    use_coef0 = InCondition(child=coef0, parent=kernel, values=["poly", "sigmoid"])
    cs.add_conditions([use_degree, use_coef0])

    # This also works for parameters that are a mix of categorical and values from a range of numbers
    # For example, gamma can be either "auto" or a fixed float
    gamma = CategoricalHyperparameter("gamma", ["auto", "value"], default="auto")  # only rbf, poly, sigmoid
    gamma_value = UniformFloatHyperparameter("gamma_value", 0.0001, 8, default=1)
    cs.add_hyperparameters([gamma, gamma_value])
    # We only activate gamma_value if gamma is set to "value"
    cs.add_condition(InCondition(child=gamma_value, parent=gamma, values=["value"]))
    # And again we can restrict the use of gamma in general to the choice of the kernel
    cs.add_condition(InCondition(child=gamma, parent=kernel, values=["rbf", "poly", "sigmoid"]))


    # Scenario object
    scenario = Scenario("test/test_files/svm_scenario.txt")

    # Example call of the function
    # It returns: Status, Cost, Runtime, Additional Infos
    def_value = svm_from_cfg(cs.get_default_configuration())
    print("Default Value: %.2f" % (def_value))

    # Optimize, using a SMAC-object
    print("Optimizing! Depending on your machine, this might take a few minutes.")
    smac = SMAC(scenario=scenario, rng=np.random.RandomState(42),
            tae_runner=svm_from_cfg)

    incumbent = smac.optimize()
    inc_value = svm_from_cfg(incumbent)

    print("Optimized Value: %.2f" % (inc_value))

if __name__ == "__main__":
    cfg_args = sys.argv[6:]
    cfg = {}
    for i in range(0, 2, len(cfg)):
        cfg[cfg_args[i][1:]] = cfg_args[i+1]  # Strip leading '-' on parameter name
    tmp = svm_from_cfg_with_instance(cfg, int(sys.argv[1]), sys.argv[5])
    print('Result for SMAC: SUCCESS, -1, -1, %f, %s' % (tmp, seed))
