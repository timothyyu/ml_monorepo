import sys, os
import logging
import numpy as np
import shutil

from smac.facade.smac_facade import SMAC
from smac.scenario.scenario import Scenario

import inspect
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
cmd_folder = os.path.realpath(os.path.join(cmd_folder, ".."))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

from cave.cavefacade import CAVE

""" If you want to add new test-scenarios to this script, just append your desired scenario to the 'scens'-list in
get_scenarios(). Use your output_dir as an identifier. """

def get_scenarios():
    scen_dict = {'algo' : 'python test/general_example/target_algorithm.py',
                 'paramfile' : 'test/general_example/param.pcs',
                 'runcount_limit' : 300,
                 'cutoff_time' : 500,
                 }

    scens = []

    scens.append({
            **scen_dict,
            **{'run_obj' : 'quality',
               'deterministic' : 1,
               'cutoff_time' : None,
               'output_dir' : 'test/general_example/results/scen_qual_det_notrain_notest_nofeat'},
            })

    scens.append({
            **scen_dict,
            **{'run_obj' : 'runtime',
               'deterministic' : 1,
               'output_dir' : 'test/general_example/results/scen_runt_det_notrain_notest_nofeat'},
            })

    scens.append({
            **scen_dict,
            **{'run_obj' : 'runtime',
               'deterministic' : 0,
               'output_dir' : 'test/general_example/results/scen_runt_nondet_notrain_notest_nofeat'},
            })

    scens.append({
            **scen_dict,
            **{'run_obj' : 'runtime',
               'deterministic' : 0,
               'instance_file' : 'test/general_example/train.txt',
               'output_dir' : 'test/general_example/results/scen_runt_det_train_notest_nofeat'},
            })

    scens.append({
            **scen_dict,
            **{'run_obj' : 'runtime',
               'deterministic' : 0,
               'instance_file' : 'test/general_example/train.txt',
               'test_instance_file' : 'test/general_example/test.txt',
               'output_dir' : 'test/general_example/results/scen_runt_det_train_test_nofeat'},
            })

    # NOT APPLICABLE
    #scens.append({
    #        **scen_dict,
    #        **{'run_obj' : 'runtime',
    #           'deterministic' : 0,
    #           'instance_file' : 'test/general_example/train.txt',
    #           'test_instance_file' : 'test/general_example/test.txt',
    #           'feature_file' : 'test/general_example/train_feat.csv',
    #           'output_dir' :
    #           'test/general_example/results/scen_runt_det_train_test_feattrain'},
    #        })

    #scens.append({
    #        **scen_dict,
    #        **{'run_obj' : 'runtime',
    #           'deterministic' : 0,
    #           'instance_file' : 'test/general_example/train.txt',
    #           'test_instance_file' : 'test/general_example/test.txt',
    #           'feature_file' : 'test/general_example/test_feat.csv',
    #           'output_dir' :
    #           'test/general_example/results/scen_runt_det_train_test_feattest'},
    #        })

    scens.append({
            **scen_dict,
            **{'run_obj' : 'runtime',
               'deterministic' : 0,
               'instance_file' : 'test/general_example/train.txt',
               'test_instance_file' : 'test/general_example/test.txt',
               'feature_file' : 'test/general_example/train_and_test_feat.csv',
               'output_dir' :
               'test/general_example/results/scen_runt_det_train_test_featboth'},
            })
    return scens

def generate_bohb_data():
    import warnings
    import hpbandster.core.nameserver as hpns
    import hpbandster.core.result as hpres
    from hpbandster.optimizers import BOHB as BOHB

    run_id = '0'  # Every run has to have a unique (at runtime) id.
    NS = hpns.NameServer(run_id=run_id, host='localhost', port=0)
    ns_host, ns_port = NS.start()

    from neural_opt import MyWorker, get_configspace

    w = MyWorker(nameserver=ns_host,
             nameserver_port=ns_port,
             run_id=run_id,  # same as nameserver's
            )
    w.run(background=True)

    # Log the optimization results for later analysis
    result_logger = hpres.json_result_logger(directory='test/general_example/results/bohb_full_configspace',
                                             overwrite=True)

    bohb = BOHB(configspace=get_configspace(),
                run_id=run_id,  # same as nameserver's
                eta=2, min_budget=5, max_budget=100,  # Hyperband parameters
                nameserver=ns_host, nameserver_port=ns_port,
                result_logger=result_logger,
                )

    # Then start the optimizer. The n_iterations parameter specifies
    # the number of iterations to be performed in this run
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = bohb.run(n_iterations=2)

    # After the run is finished, the services started above need to be shutdown.
    # This ensures that the worker, the nameserver and the master all properly exit
    # and no (daemon) threads keep running afterwards.
    # In particular we shutdown the optimizer (which shuts down all workers) and the nameserver.
    bohb.shutdown(shutdown_workers=True)
    NS.shutdown()


def print_help():
    print("This script will generate scenarios for the corner cases of provided information (with/without features, instances, etc.) using toy data.\n"
          "Start this script with one of the following arguments in a suitable python-environment (that fulfills CAVE's requirements):\n"
          "-- 'generate' will generate suitable test-cases using SMAC-optimization \n"
          "-- 'cave' will analyze the results of the generate-option using cave \n"
          "-- 'clean' will delete previous results \n"
          "-- 'firefox' will open all reports in firefox.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    #logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print_help()
    elif sys.argv[1] == 'generate':
        generate_bohb_data()
        for scen in get_scenarios():
            scenario = Scenario(scen)
            smac = SMAC(scenario=scenario, rng=np.random.RandomState(42))
            smac.optimize()
    elif sys.argv[1] == 'cave':
        failed = []
        for scen in get_scenarios():
            try:
                folder = [f for f in os.listdir(scen['output_dir']) if f.startswith('run')][0]
                cave = CAVE([os.path.join(scen['output_dir'], folder)],
                            os.path.join(scen['output_dir'], 'CAVE_RESULT'),
                            ta_exec_dir='.', validation_method='validation')
                cave.analyze(param_importance=['ablation', 'forward_selection', 'lpi'], cfp_number_quantiles=2)
            except:
                failed.append(scen['output_dir'])
        print("Failed: %s" % (str(failed)))
    elif sys.argv[1] == 'firefox':
        import webbrowser
        firefox = webbrowser.get('firefox')
        for url in [os.path.join(scen['output_dir'], 'CAVE_RESULT/report.html') for scen in get_scenarios()]:
            firefox.open_new_tab(url)
    elif sys.argv[1] == 'clean':
        shutil.rmtree('test/general_example/results')
    else:
        logging.error("%s not an option.", sys.argv[1])
        print_help()
