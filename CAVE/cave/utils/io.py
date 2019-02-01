import os
import csv
import warnings

import numpy as np
import pandas as pd
from bokeh.io import export_png, output_notebook

from ConfigSpace.util import deactivate_inactive_hyperparameters, fix_types

from cave.utils.timing import timing


@timing
def export_bokeh(plot, path, logger):
    """Export bokeh-plot to png-file. Create directory if necessary

    Parameters
    ----------
    plot: bokeh.plotting.figure
        bokeh plot to export
    path: str
        path to save plot to
    logger: Logger
        logger for debugging
    """
    base = os.path.split(path)[0]
    logger.debug("Exporting to %s (base: %s)", path, base)
    plot.background_fill_color, plot.border_fill_color = None, None
    if base and not os.path.exists(base):
        logger.debug("%s does not exist. Creating...", base)
        os.makedirs(base)
    try:
        with warnings.catch_warnings(record=True) as list_of_warnings:
            warnings.simplefilter('always')
            export_png(plot, filename=path)
            for w in list_of_warnings:
                logger.debug("During export a %s was raised: %s", str(w.category), w.message)
    except (RuntimeError, TypeError) as err:
        logger.debug("Exporting failed", exc_info=1)
        logger.warning("Exporting bokeh-plot to \"%s\" failed. "
                       "To activate automatic png-export, please follow instructions on CAVE's GitHub "
                       "(install selenium and phantomjs-prebuilt).", path)
    except (SystemError) as err:
        logger.debug("Exporting failed", exc_info=1)
        logger.warning("Exporting bokeh-plot to \"%s\" failed. "
                       "This issue is known, but not yet solved. However it seems to appear with too few data-points. "
                       "Feel free to report your example on https://github.com/automl/CAVE/issues.", path)
    except Exception as err:
        logger.debug("Exporting failed", exc_info=1)
        logger.warning("Exporting bokeh-plot to \"%s\" failed. (run --verbose DEBUG for more info)", path)


def load_csv_to_pandaframe(csv_path, logger, apply_numeric=True, delimiter=','):
    """Load csv-file and return pd.DataFrame. First line of file is expected to
    be the header.

    Parameters
    ----------
    csv_path: str
        path to csv-file
    logger: logging.Logger
        logger, for debugging
    apply_numeric: boolean
        whether to an attempt should be taken to turn columns into numeric values.
    delimiter: str
        can be used to determine custom delimiter

    Returns
    -------
    data_frame: pd.DataFrame
        csv-dataframe
    """
    with open(csv_path, 'r') as csv_file:
        lines = csv_file.readlines()
        csv_data = [[e.strip('" \n') for e in l.split(delimiter)] for l in lines]
    header, csv_data = csv_data[0], np.array([csv_data[1:]])[0]
    data = pd.DataFrame(csv_data, columns=header)
    if apply_numeric:
        data = data.apply(pd.to_numeric, errors='ignore')
    logger.debug("Headers in \'%s\': %s", csv_path, data.columns.values)
    if not len(data.columns) == len(set(data.columns)):
        raise ValueError("Detected a duplicate in the columns of the "
                         "csv-file \"%s\"." % csv_path)
    return data


def load_config_csv(path, cs, logger):
    """ Load configurations.csv in the following format:

    +-----------+-----------------+-----------------+-----+
    | CONFIG_ID | parameter_name1 | parameter_name2 | ... |
    +===========+=================+=================+=====+
    | 0         | value1          | value2          | ... |
    +-----------+-----------------+-----------------+-----+
    | ...       | ...             | ...             | ... |
    +-----------+-----------------+-----------------+-----+

    Parameters
    ----------
    path: str
        path to csv-file
    cs: ConfigurationSpace
        configspace with matching parameters
    logger: Logger
        logger for debugs

    Returns
    -------
    (parameters, id_to_config): (str, dict)
        parameter-names and dict mapping ids to Configurations
    """
    id_to_config = {}
    logger.debug("Trying to read configuration-csv-file: %s.", path)
    config_data = load_csv_to_pandaframe(path, logger, apply_numeric=False)
    config_data['CONFIG_ID'] = config_data['CONFIG_ID'].apply(pd.to_numeric)
    config_data.set_index('CONFIG_ID', inplace=True)
    logger.debug("Found parameters: %s", config_data.columns)
    logger.debug("Parameters in pcs: %s", cs.get_hyperparameter_names())
    diff = set(config_data.columns).symmetric_difference(set(cs.get_hyperparameter_names()))
    if diff:
        raise ValueError("Provided pcs does not match configuration-file "
                         "\'%s\' (check parameters %s)" % (path, diff))
    for index, row in config_data.iterrows():
        values = {name: row[name] for name in config_data.columns if row[name]}
        id_to_config[index] = deactivate_inactive_hyperparameters(fix_types(values, cs), cs)
    return config_data.columns, id_to_config
