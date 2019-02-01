Quickstart
----------
CAVE is designed to adapt to any given workflow. While it's possible to generate a HTML-report via the commandline on a
given result-folder, CAVE may also run in interactive mode, running `individual analysis-methods <apidoc/cave.cavefacade.html>`_ on demand. We provide a
few examples to demonstrate this.
Make sure you followed the `installation details <installation.html>`_ before starting.

Analyse existing results via the commandline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are example toy results of all supported file formats in the folder `examples
<https://github.com/automl/CAVE/tree/master/examples>`_ on the github-repo.
Run

.. code-block:: bash

    cave --folders examples/smac3/example_output/* --ta_exec_dir examples/smac3/ --output CAVE_OUTPUT

to start the example (assuming you cloned the GitHub-repository in which the example is included).
By default, CAVE will execute all parts of the analysis. To disable certain (timeconsuming) parts
of the analysis, please see the section `commandline-options <manualdoc/commandline.html>`_.

Most importantly though: ``--folders`` takes one or several paths to directories with configurator output.
*glob*-extension is supported.
``--ta_exec_dir`` defines a directory, from which the configurator was run - in case that
there are relative paths while loading the data (e.g. instance-file-paths in SMAC's scenario-file). Here also one or more values are valid,
however either one path for all ``--folders``-paths or exactly as many (one-to-one mapping).
``--output`` simply defines, where to save CAVE-output (report, plots, tables, etc.).

Interactive notebook mode
~~~~~~~~~~~~~~~~~~~~~~~~~

You can also run CAVE in an interactive notebook mode. Make sure you have `jupyter <http://jupyter.org/install>`_
installed, then just create a CAVE-object within a running notebook and run analysis-methods manually. See the
`jupyter-explanation <manualdoc/jupyternotebook.html>`_ for details.
To run the smac3-example (within a notebook):

.. code-block:: python

    from cave.cavefacade import CAVE
    cave = CAVE(folders=["examples/smac3/example_output/run_1"],
                output_dir="test_jupyter_smac",
                ta_exec_dir=["examples/smac3"],
                file_format='SMAC3',
               )
    cave.performance_table()

