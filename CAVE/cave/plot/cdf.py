import numpy as np
import matplotlib.pyplot as plt


def plot_cdf(x_list, y_list, label_list, timeout, out_fn):
    """
    Parameters
    ----------
    x_list, y_list: List[np.array]
        zip lists and plot all data on one plot
    label_list: str
        strings for legend corresponding to x, y
    timeout: float
        if set, timeouts are marked at this point
    out_fn: str
        filename

    Returns
    -------
    out_fn: str
        filename
    """
    f = plt.figure(1, dpi=100, figsize=(10, 10))
    ax = f.add_subplot(1, 1, 1)
    colors = ['red', 'blue', 'green']
    for x, y, l, c in zip(x_list, y_list, label_list, colors):
        ax.step(x, y, color=c, linestyle='-', label=l)
    ax.legend()
    ax.grid(True)
    ax.set_xscale('log')
    ax.set_ylabel('probability of being solved')
    ax.set_xlabel('time')
    # Plot 'timeout'
    if timeout:
        ax.text(timeout,
                ax.get_ylim()[0] - 0.1 * np.abs(ax.get_ylim()[0]),
                "timeout ", horizontalalignment='center',
                verticalalignment="top", rotation=30)
        ax.axvline(x=timeout, linestyle='--')

    f.tight_layout()
    f.savefig(out_fn)
    plt.close(f)
    return out_fn
