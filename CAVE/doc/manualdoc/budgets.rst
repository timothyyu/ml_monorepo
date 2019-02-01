Budgets
~~~~~~~

Some configurators such as `BOHB/hpbandster <https://github.com/automl/HpBandSter>`_ try to optimize using budgets.
Budgets are limited resources that speed up the evaluation of a configuration, like an estimate. E.g. evaluating neural
networks with a reduced number of epochs can be seen as a budget configurator.
CAVE can process and analyze these results. It is possible to access each method for each budget individually. Also,
there are methods to compare across budgets.
CAVE will automatically use budgets, when the ``--file_format`` is *BOHB*. If you want to use budgets with CSV-input,
you need to specify *use_budgets* and provide an individual CSV-folder per budget.
