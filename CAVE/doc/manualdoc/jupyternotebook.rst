Jupyter Notebook
================

CAVE is compatible with jupyter notebooks, that means all plots and tables will render in a jupyter notebook.
There is an example in examples/cave_notebook.ipynb, that you can start with
jupyter-notebook example/cave_notebook.ipynb.
To use CAVE in such an interactive mode, you have to create a `CAVE-instance <../apidoc/cave.cavefacade.html>`_:

.. code-block:: python

    from cave.cavefacade import CAVE
    cave = CAVE(folders=["examples/smac3/example_output/run_1"],
                output_dir="test_jupyter_smac",
                ta_exec_dir=["examples/smac3"],
                file_format='SMAC3',
               )

You can then use any of CAVE's methods to analyze the loaded results by simply using it:

.. code-block:: python

    cave.performance_table()

When using budgets, you can specify which budget you want to plot/analyze:

.. code-block:: python

    cave = CAVE(folders=["examples/bohb"],
                output_dir="test_jupyter_bohb",
                ta_exec_dir=["examples/bohb"],
                file_format='BOHB',
               )
    cave.print_budgets()
    cave.performance_table('budget_42')


