'''Server for visualization.'''
#%%
from __future__ import (absolute_import, print_function, unicode_literals, division)

import json
import itertools
import numpy as np

from bokeh.layouts import column, gridplot
from bokeh.models import Button
from bokeh.palettes import Set1
from bokeh.plotting import figure, curdoc, output_notebook, show, output_server

#%%
def _keys_for(link):
    data = ['W/data', 'W/grad', 'b/data', 'b/grad']
    weights_biases = ['{}/{}/{}'.format(link, entry, key) for entry in data for key in SUFFIX_KEYS]
    stats = ['{}/{}'.format(link, key) for key in ['W/data-grad/ratio', 'b/data-grad/ratio', 'W-b/data/zeros']]
    return stats + weights_biases


def convert_to_patch(xt, y_lower, y_upper):
    return {
        'x': np.append(xt, xt[::-1]),
        'y': np.append(y_lower, y_upper)
    }


def plot_stats(p, key):
    _get = get_for(key)

    y_min = p.line(x=[], y=[], line_dash='dashed')
    y_max = p.line(x=[], y=[], line_dash='dashed')
    y1 = p.patch(x=[], y=[], alpha=0.1)
    y2 = p.patch(x=[], y=[], alpha=0.1)
    y3 = p.patch(x=[], y=[], alpha=0.2)
    y4 = p.line(x=[], y=[])

    return [y_min, y_max, y1, y2, y3, y4]


def get(key):
    return dataseries.get(key, np.empty((1, 2)))

def get_for(key):
    def _get(suffix):
        return get(key + '/' + suffix)
    return _get

FILENAME = 'log'
COLORS = Set1[3][:2] * 2
ALPHAS = [.2, .2, 1., 1.]
TRAIN_KEY, TEST_KEY = 'main/nll', 'validation/main/nll'
TIME_KEY = 'iteration'
WINDOW_SIZE = 20
PREFIX_KEYS = [
]
SUFFIX_KEYS = ['max', 'mean', 'min', 'percentile/0', 'percentile/1', 'percentile/2',
               'percentile/3', 'percentile/4', 'percentile/5', 'percentile/6', 'std']
DATA_KEYS = [TRAIN_KEY, TEST_KEY] + list(itertools.chain(*[_keys_for(link) for link in PREFIX_KEYS]))

#%%
loss_plot = figure(plot_width=1000, plot_height=800)
loss = loss_plot.multi_line(xs=[[]] * 4,
                            ys=[[]] * 4,
                            color=COLORS,
                            alpha=ALPHAS)

plots = []
dataseries = {}
source = {}


for prefix in PREFIX_KEYS:
    for key in ['W/data', 'W/grad', 'b/data', 'b/grad']:
        complex_key = prefix+'/'+key
        p = figure(title=complex_key)
        source[complex_key] = plot_stats(p, complex_key)
        plots.append(p)
    for key in ['W/data-grad/ratio', 'b/data-grad/ratio', 'W-b/data/zeros']:
        complex_key = prefix+'/'+key
        p = figure(title=complex_key)
        source[complex_key] = p.line(get(complex_key)[:, 0], get(complex_key)[:, 1])
        plots.append(p)


grid = gridplot(plots, plot_width=250, plot_height=250, ncols=7)


def callback():
    with open(FILENAME) as ifile:
        data = json.load(ifile)
        for key in DATA_KEYS:
            dataseries[key] = np.array([
                (rcrd[TIME_KEY], rcrd[key]) for rcrd in data if key in rcrd], 'f')
            if not len(dataseries[key]):
                del dataseries[key]



    def window_for(size):
        window = np.hamming(size)
        window /= window.sum()
        return window

    def smooth(data):
        edge_data = [np.convolve(data[:size], window_for(size), mode='valid')
                     for size in range(1, WINDOW_SIZE)]

        return np.concatenate(edge_data + [np.convolve(data, window_for(WINDOW_SIZE), mode='valid')])

    train_ts = get('main/nll')
    test_ts = get('validation/main/nll')

    train_smooth = smooth(train_ts[:, 1])
    test_smooth = smooth(test_ts[:, 1])

    loss.data_source.data.update({
        'xs': [train_ts[:, 0], test_ts[:, 0]] * 2,
        'ys': [train_ts[:, 1], test_ts[:, 1], train_smooth, test_smooth],
    })


    for k, v in source.items():
        if isinstance(v, list):
            _get = get_for(k)

            xt = _get('mean')[:, 0]
            v[0].data_source.data.update({
                'x': _get('min')[:, 0],
                'y': _get('min')[:, 1]
            })
            v[1].data_source.data.update({
                'x': _get('max')[:, 0],
                'y': _get('max')[:, 1]
            })
            v[2].data_source.data.update(
                convert_to_patch(xt, _get('percentile/0')[:, 1], _get('percentile/6')[:, 1]))
            v[3].data_source.data.update(
                convert_to_patch(xt, _get('percentile/1')[:, 1], _get('percentile/5')[:, 1]))
            v[4].data_source.data.update(
                convert_to_patch(xt, _get('percentile/2')[:, 1], _get('percentile/4')[:, 1]))

            v[-1].data_source.data.update({
                'x': _get('percentile/3')[:, 0],
                'y': _get('percentile/3')[:, 1],
            })
        else:
            v.data_source.data.update({
                'x': get(k)[:, 0],
                'y': get(k)[:, 1],
            })


# # add a button widget and configure with the call back
button = Button(label="Update")
button.on_click(callback)

# output_notebook()
layout = column(button, loss_plot, grid)
curdoc().add_root(layout)


