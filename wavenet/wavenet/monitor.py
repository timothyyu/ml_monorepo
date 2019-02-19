# Taken from https://github.com/hvy/chainer-param-monitor
import numpy as np
from functools import reduce
from chainer.cuda import cupy

import chainer

# The name template of the statistic to collect and include in the report.
# E.g. 'predictor/conv1/W/grad/percentile/sigma_one'
key_template = '{model}/{layer}/{param}/{attr}/{statistic}'


def _percentiles(data, sigma=(0.13, 2.28, 15.87, 50, 84.13, 97.72, 99.87)):

    """Compute percentiles for data and return an array with the same length
    as the number of elements in ``sigma``.

    Args:
        data (array): 1-dimensional NumPy or CuPy arryay.
        sigma (tuple): Sigmas for which percentiles are computed. Defaults to
            the three-sigma-rule. See: https://en.wikipedia.org/wiki/Percentile

    Returns:
        array: Array of percentiles.
    """

    # TODO: Make percentile computation faster for GPUs.

    # To CPU before computing the percentiles since CuPy doesn't implement
    # np.percentile().
    if cupy.get_array_module(data) is cupy:
        data = cupy.asnumpy(data)

    try:
        ps = np.percentile(data, sigma)
    except IndexError:
        # If data is missing from uninitialized parameters, add
        # NaN placeholders instead of skipping the measurements completely
        # or registering zeros.
        ps = np.array((float('NaN'),) * 7)

    # Back to GPU when percentiles are computed.
    if cupy.get_array_module(data) is cupy:
        ps = cupy.asarray(ps)

    return ps


def layer_params(layer, param_name, attr_name):

    """Return parameters in a flattened array from the given layer or an empty
    array if the parameters are not found.

    Args:
        layer (~chainer.Link): The layer from which parameters are collected.
        param_name (str): Name of the parameter, ``'W'`` or ``'b'``.
        attr_name (str): Name of the attribute, ``'data'`` or ``'grad'``.

    Returns:
        array: Flattened array of parameters.
    """

    if isinstance(layer, chainer.Chain):
        # Nested chainer.Chain, aggregate all underlying statistics
        return layers_params(layer, param_name, attr_name)
    elif not hasattr(layer, param_name):
        return layer.xp.array([])

    params = getattr(layer, param_name)
    params = getattr(params, attr_name)
    return params.flatten()


def layers_params(model, param_name, attr_name):

    """Return all parameters in a flattened array from the given model.

    Args:
        model (~chainer.Chain): The model from which parameters are collected.
        param_name (str): Name of the parameter, ``'W'`` or ``'b'``.
        attr_name (str): Name of the attribute, ``'data'`` or ``'grad'``.

    Returns:
        array: Flattened array of parameters.
    """

    xp = model.xp
    params = xp.array([], dtype=xp.float32)

    for param in model.params():
        if param.name == param_name:
            values = getattr(param, attr_name)
            values = values.flatten()
            params = xp.concatenate((params, values))  # Slow?

    return params


def weight_statistics(model, layer_name=None):

    """Collect weight statistict from the given model and return it as a
    ``dict``.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    return parameter_statistics(model, 'W', 'data', layer_name)


def bias_statistics(model, layer_name=None):

    """Collect bias statistict from the given model and return it as a
    ``dict``.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    return parameter_statistics(model, 'b', 'data', layer_name)


def weight_gradient_statistics(model, layer_name=None):

    """Collect weight gradient statistict from the given model and return it
    as a ``dict``.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    return parameter_statistics(model, 'W', 'grad', layer_name)


def bias_gradient_statistics(model, layer_name=None):

    """Collect bias gradient statistict from the given model and return it
    as a ``dict``.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    return parameter_statistics(model, 'b', 'grad', layer_name)


def sparsity(model, include_bias=False, layer_name=None):

    """Count the number of parameters with the value zero for the given model
    and return it as a ``dict``.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        include_bias (bool): ``True`` to include the number of biases that are
            zero, ``False`` to exclude them.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    xp = model.xp

    def reduce_count_zeros(acc, param):
        if param.name == 'W' or (include_bias and param.name == 'b'):
            acc += param.data.size - xp.count_nonzero(param.data)
        return acc

    if layer_name is not None:
        sparsity = reduce(reduce_count_zeros, [getattr(model, layer_name)], 0)
    else:
        sparsity = reduce(reduce_count_zeros, model.params(), 0)

    key = key_template.format(model=model.name,
                              layer='*' if layer_name is None else layer_name,
                              param='Wb' if include_bias else 'W' ,
                              attr='sparsity',
                              statistic='zeros')

    return { key: sparsity }


def parameter_statistics(model, param_name, attr_name, layer_name=None):

    """Collect statistict from the given model and return it as a ``dict``.

    The returned ``dict`` contains a key for each metric, mapping to a NumPy
    or CuPy ``float32`` value depending on if the given model was on the CPU or
    the GPU.

    Args:
        model (~chainer.Chain): The model from which statistics are collected.
        param_name (str): Name of the parameter, ``'W'`` or ``'b'``.
        attr_name (str): Name of the attribute, ``'data'`` or ``'grad'``.
        layer_name (str): Name of the layer which may be specified or set to
            ``None`` to aggregate over all layers.

    Returns:
        dict: Parameter statistics.
    """

    if layer_name is not None:  # Collect statistics for a single layer only
        l = getattr(model, layer_name)
        lp = layer_params(l, param_name, attr_name)
        return as_statistics(lp, model.name, param_name, attr_name,
                             layer_name=layer_name)

    lp = layers_params(model, param_name, attr_name)
    return as_statistics(lp, model.name, param_name, attr_name)


def as_statistics(data, model_name, param_name, attr_name, layer_name=None,
                  statistics=('min', 'max', 'mean', 'std', 'percentiles')):

    """Compute statistics based on the given data and return it as a ``dict``.

    Args:
        data (array): NumPy or CuPy array of data.
        model_name (str): Name of the model,  e.g. ``predictor``.
        param_name (str): Name of the parameter, ``'W'`` or ``'b'``.
        attr_name (str): Name of the attribute, ``'data'`` or ``'grad'``.
        layer_name (str): Name of the layer which may be specified or set to
            ``None``. In the case of ``None`` the layer name will be set to
            ``'*'``.

    Returns:
        dict: Parameter statistics.
    """

    stats = {}

    if layer_name is None:
        layer_name = '*'

    statistics = list(statistics)

    if 'percentiles' in statistics:
        statistics.pop(statistics.index('percentiles'))
        percentiles = _percentiles(data)
        for i, p in enumerate(['n3s', 'n2s', 'n1s', 'z', '1s', '2s', '3s']):
            key = key_template.format(model=model_name,
                                      layer=layer_name,
                                      param=param_name,
                                      attr=attr_name,
                                      statistic='percentile/{}'.format(p))
            stats[key] = percentiles[i]

    for s in statistics:
        key = key_template.format(model=model_name,
                                  layer=layer_name,
                                  param=param_name,
                                  attr=attr_name,
                                  statistic=s)
        try:
            stats[key] = getattr(data, s)()
        except ValueError:
            # If data is invalid, e.g. for uninitialized linear links,
            # chainer.links.Linear
            stats[key] = float('NaN')

    return stats
