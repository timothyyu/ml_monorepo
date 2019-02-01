import os
import itertools
import logging

import matplotlib.pyplot as plt
plt.style.use(os.path.join(os.path.dirname(__file__), 'mpl_style'))  # noqa
from matplotlib.pyplot import setp

import numpy as np

"""
Mostly taken from https://bitbucket.org/aadfreiburg/plotting_scripts
"""


def plot_scatter_plot(x_data, y_data, labels, title="",
                      min_val=None, max_val=1000, grey_factor=1,
                      linefactors=None, user_fontsize=22, dpi=100,
                      metric="runtime", jitter_timeout=True,
                      markers=None, sizes=None, out_fn=None):
    """
    Method to generate a scatter plot
    Parameters
    ----------
    x_data: numpy.array
        performance values of one algorithm
    y_data: numpy.array
        performance values of the other algorithm
    labels: tuple
        (xlabel, ylabel)
    title: str
        title of plot
    min_val: float
        minimal value to plot
    max_val: float
        maximal value to plot
    grey_factor: float
        grey factor of points with a speedup of less 2
    linefactors: list of floats
        factors of speedups
    user_fontsize: int
        font size
    dpi: int
        resolution
    metric: str
        "runtime" or something else
    jitter_timeout: bool
        Add some noise to remove timeout clutter
    """

    if markers is None or len(markers) != 3:
        regular_marker = 'x'
        timeout_marker = '+'
        grey_marker = '.'
    else:
        regular_marker = markers[0]
        timeout_marker = markers[1]
        grey_marker = markers[2]

    if sizes is None or len(sizes) != 3:
        s_r = 5
        s_t = 5
        s_g = 5
    else:
        s_r = sizes[0]
        s_t = sizes[1]
        s_g = sizes[2]

    c_angle_bisector = "#e41a1c"  # Red
    c_good_points = "#999999"     # Grey
    c_other_points = "k"
    size = 1
    st_ref = "--"

    ticklabel_size = user_fontsize
    linefactor_size = user_fontsize - 2
    label_size = user_fontsize + 1

    #
    # ------
    # maximum_value: location for timeout points
    # max_val      : Initially user-defined timeout, then set to axes limit
    # time_out_val : location for timeout points
    # -----

    if max_val is None:
        max_val = 1000
        # raise ValueError("max_val cannot be None")
    maximum_value = max_val

    # Colors
    ref_colors = itertools.cycle([  # "#e41a1c",    # Red
                                 "#377eb8",    # Blue
                                 "#4daf4a",    # Green
                                 "#984ea3",    # Purple
                                 "#ff7f00",    # Orange
                                 "#ffff33",    # Yellow
                                 "#a65628",    # Brown
                                 "#f781bf",    # Pink
                                 # "#999999",    # Grey
                                 ])

    # set initial limits
    x_min = min([min(x) for x in x_data])
    y_min = min([min(y) for y in y_data])
    x_max = max([max(x) for x in x_data])
    y_max = max([max(y) for y in y_data])
    x_min = min([x_min, y_min])
    y_min = x_min
    x_max = max([x_max, y_max])
    y_max = x_max
    if min_val is not None:
        auto_min_val = min([x_min, y_min, min_val])
    else:
        auto_min_val = min([x_min, y_min])

    if metric == "runtime" or metric == "quality":
        timeout_factor = 2
        timeout_val = maximum_value * timeout_factor
        auto_max_val = maximum_value
    else:
        timeout_factor = 1
        timeout_val = 1
        auto_max_val = max([x_max, y_max])

    # Set up figure
    if len(x_data) > 1:
        fig = plt.figure(1, dpi=dpi, figsize=(10, 5))
        ax1 = fig.add_subplot(1, 2, 1, adjustable='box', aspect=1)
        ax2 = fig.add_subplot(1, 2, 2, adjustable='box', aspect=1)
        axes = [ax1, ax2]
    else:
        fig = plt.figure(1, dpi=dpi, figsize=(10, 10))
        ax1 = fig.add_subplot(1, 1, 1, adjustable='box', aspect=1)
        axes = [ax1]

    for ax in axes:
        ax.grid(True, linestyle='-', which='major', color='lightgrey', alpha=0.5)

    # Plot angle bisector and reference_lines
    out_up = auto_max_val
    out_lo = max(10**-6, auto_min_val)

    # if metric == "runtime" or metric == "quality":
    for ax in axes:
        ax.plot([out_lo, out_up], [out_lo, out_up], c=c_angle_bisector)

        if linefactors is not None:
            for f in linefactors:
                c = next(ref_colors)
                # Lower reference lines
                ax.plot([f*out_lo, out_up], [out_lo, (1.0/f)*out_up], c=c, linestyle=st_ref, linewidth=size*1.5)
                # Upper reference lines
                ax.plot([out_lo, (1.0/f)*out_up], [f*out_lo, out_up], c=c, linestyle=st_ref, linewidth=size*1.5)
                offset = 1.1
                if int(f) == f:
                    lf_str = "%dx" % f
                else:
                    lf_str = "%2.1fx" % f
                ax.text((1.0/f)*out_up, out_up*offset+1000, lf_str, color=c, fontsize=linefactor_size)
                ax.text(out_up*offset+1000, (1.0/f)*out_up, lf_str, color=c, fontsize=linefactor_size)

    #######
    #  Scatter
    def scatter(x_data_, y_data_, ax):
        """ Encapsulated to support subplots if train and test are
        differentiated. """
        logger = logging.getLogger("cave.scatter")
        logger.debug("Incumbent better: %d, default better: %d",
                     len([x for x in x_data_ > y_data_ if x]),
                     len([x for x in x_data_ < y_data_ if x]))

        grey_idx = list()
        timeout_x = list()
        timeout_y = list()
        timeout_both = list()
        rest_idx = list()
        for idx_x, x in enumerate(x_data_):
            if x >= max_val > y_data_[idx_x]:
                # timeout of x algo
                timeout_x.append(idx_x)
            elif y_data_[idx_x] >= max_val > x:
                # timeout of y algo
                timeout_y.append(idx_x)
            elif y_data_[idx_x] >= max_val and x >= max_val:
                # timeout of both algos
                timeout_both.append(idx_x)
            elif y_data_[idx_x] < grey_factor*x and x < grey_factor*y_data_[idx_x]:
                grey_idx.append(idx_x)
            else:
                rest_idx.append(idx_x)

        # Regular points
        if len(grey_idx) > 1:
            ax.scatter(x_data_[grey_idx], y_data_[grey_idx], marker=grey_marker,
                       edgecolor='', facecolor=c_good_points, s=s_g)
        ax.scatter(x_data_[rest_idx], y_data_[rest_idx], marker=regular_marker, c=c_other_points, s=s_r)

        if metric == "runtime" or metric == "quality":
            # max_val lines
            ax.plot([maximum_value, maximum_value], [auto_min_val, maximum_value],
                    c=c_other_points, linestyle="--", zorder=0, linewidth=size)
            ax.plot([auto_min_val, maximum_value], [maximum_value, maximum_value],
                    c=c_other_points, linestyle="--", zorder=0, linewidth=size)

            # Timeout points
            if jitter_timeout:
                scat_x = np.random.randn(len(timeout_x), 1)*0.1*timeout_val + timeout_val
                scat_y = np.random.randn(len(timeout_y), 1)*0.1*timeout_val + timeout_val
                scat_both = (np.random.randn(len(timeout_both), 1)*0.1*timeout_val + timeout_val,
                             np.random.randn(len(timeout_both), 1)*0.1*timeout_val + timeout_val)
            else:
                scat_x = [timeout_val]*len(timeout_x)
                scat_y = [timeout_val]*len(timeout_y)
                scat_both = ([timeout_val]*len(timeout_both), [timeout_val]*len(timeout_both))

            ax.scatter(scat_x, y_data_[timeout_x],
                       marker=timeout_marker, c=c_other_points, s=s_t)
            ax.scatter(scat_both[0], scat_both[1],
                       marker=timeout_marker, c=c_other_points, s=s_t)
            ax.scatter(x_data_[timeout_y], scat_y,
                       marker=timeout_marker, c=c_other_points, s=s_t)

    for x, y, ax in zip(x_data, y_data, axes):
        scatter(x, y, ax)

    # Set axes scale and limits
    # if metric == "runtime":
    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")

    # Set axes labels
    for ax in axes:
        ax.set_xlabel(labels[0], fontsize=label_size)
        ax.set_ylabel(labels[1], fontsize=label_size)

    # if debug:
    #     # Plot legend
    #     for ax in axes:
    #         leg = ax.legend(loc='best', fancybox=True)
    #     leg.get_frame().set_alpha(0.5)

    max_val = timeout_val * timeout_factor
    auto_min_val *= 0.9
    for ax in axes:
        ax.set_autoscale_on(False)
        if max_val is not None and min_val is None:
            # User sets max val
            ax.set_ylim([auto_min_val, max_val])
            ax.set_xlim(ax.get_ylim())
        elif max_val > min_val and max_val is not None and min_val is not None:
            # User sets both, min and max -val
            ax.set_ylim([min_val, max_val])
            ax.set_xlim(ax.get_ylim())
        else:
            # User sets nothing
            ax.set_xlim([auto_min_val, max_val])
            ax.set_ylim(ax.get_xlim())

    # Plot maximum value as tick
    if int(maximum_value) == maximum_value:
        maximum_value = int(maximum_value)
        maximum_str = r"$%d$" % maximum_value
    else:
        maximum_str = r"$%5.2f$" % maximum_value

    # if metric == "runtime" or metric == "quality":
    for ax in axes:
        if int(np.log10(maximum_value)) != np.log10(maximum_value):
            # If we do not already have this ticklabel as a regular label
            ax.text(ax.get_ylim()[0] - 0.1 * np.abs(ax.get_ylim()[0]),
                    maximum_value,
                    maximum_str,
                    horizontalalignment='right', verticalalignment="center",
                    fontsize=user_fontsize)
            ax.text(maximum_value,
                    ax.get_ylim()[0] - 0.1 * np.abs(ax.get_ylim()[0]),
                    maximum_str,
                    horizontalalignment='center', verticalalignment="top",
                    fontsize=user_fontsize)

        # Plot 'timeout'
        ax.text(ax.get_xlim()[0] - 0.1 * np.abs(ax.get_ylim()[0]),
                timeout_val,
                "timeout ", horizontalalignment='right',
                verticalalignment="center", fontsize=user_fontsize,
                rotation=30)
        ax.text(timeout_val,
                ax.get_ylim()[0] - 0.1 * np.abs(ax.get_ylim()[0]),
                "timeout ",  horizontalalignment='center',
                verticalalignment="top",
                fontsize=user_fontsize, rotation=30)

        #########
        # Adjust ticks > max_val
        ax.xaxis.set_ticks_position('bottom')
        ax.yaxis.set_ticks_position('left')
        # major axes
        for tic in ax.xaxis.get_major_ticks():
            if tic._loc > maximum_value:
                tic.tick1On = tic.tick2On = False
        for tic in ax.yaxis.get_major_ticks():
            if tic._loc > maximum_value:
                tic.tick1On = tic.tick2On = False

        # minor axes
        for tic in ax.xaxis.get_minor_ticks():
            if tic._loc > maximum_value:
                tic.tick1On = tic.tick2On = False
        for tic in ax.yaxis.get_minor_ticks():
            if tic._loc > maximum_value:
                tic.tick1On = tic.tick2On = False

        # tick labels
        for ax in axes:
            ticks_x = ax.get_xticks()
            new_ticks_label = list()
            for l_idx in range(len(ticks_x)):
                if ticks_x[l_idx] < maximum_value:
                    if 0 < ticks_x[l_idx] < 1:
                        new_ticks_label.append(str(r"$10^{%d}$" %
                                                   int(np.log10(ticks_x[l_idx]))))
                    if 1 <= ticks_x[l_idx] < 1000:
                        new_ticks_label.append(str(r"$%d^{ }$" %
                                                   int(ticks_x[l_idx])))
                    if 1000 <= ticks_x[l_idx]:
                        new_ticks_label.append(str(r"$10^{%d}$" %
                                                   int(np.log10(ticks_x[l_idx]))))
            ax.set_xticklabels(new_ticks_label)  # , rotation=45)
            ax.set_yticklabels(new_ticks_label)  # , rotation=45)

    # Change fontsize for ticklabels
    for ax in axes:
        setp(ax1.get_yticklabels(), fontsize=ticklabel_size)
        setp(ax1.get_xticklabels(), fontsize=ticklabel_size)

    fig.tight_layout()
    fig.savefig(out_fn)
    plt.close(fig)

    return out_fn
