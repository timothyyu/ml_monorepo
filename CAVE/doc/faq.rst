F.A.Q.
======

.. rubric:: The automatic export of bokeh-plots does not work, why?

You're likely seeing a warning refering to missing installs of selenium and/or
phantomjs-prebuilt. While selenium should be included in the requirements,
phantomjs-prebuilt is not a pip-install. Please refer to the documentation of
phantomjs or `bokeh <https://bokeh.pydata.org/en/latest/docs/user_guide/export.html>`_ to see how installation works (usually `npm install -g phantomjs-prebuilt` should do the trick).

.. rubric:: What is the `ta_exec_dir`-option good for?

The `ta_exec_dir` specifies the target algorithm execution directory. With this option you can run *CAVE* from any
folder, just make sure the relative paths in the scenario can be found from the path you specify in `ta_exec_dir`.

.. rubric:: I experience problems with the origins in the configuration footprint when using SMAC3-data...

Configuration origins may require you to install SMAC3's development branch with `pip install -e
git+git://github.com/automl/SMAC3@development#egg=smac`.
