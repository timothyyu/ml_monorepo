"""Example data sets."""
from __future__ import division
import numpy as np


def generate_tracking(n_series, n_samples, speed=0.2,
                      dynamics_noise=0.005, measurement_noise=0.005,
                      random_state=0):
    """Generate data for the tracking problem from [1]_.

    The task is to estimate the position of a target moving with a constant
    speed in a 2-dimensional square box, bouncing from its bounds, using the
    measurements of its polar angle (bearing). The box is centered at (0, 0)
    and its side length is 20.

    Parameters
    ----------
    n_series : int
        Number of time series to generate.
    n_samples : int
        Number of samples in each time series.
    speed : float, default 0.1
        Step size of the target per time step.
    dynamics_noise : float, default 0.005
        Standard deviation of noise to add to the target position.
    measurement_noise : float, default 0.005
        Standard deviation of noise to add to the bearing measurements.
    random_state : int, default 0
        Seed to use in the random generator.

    Returns
    -------
    X : ndarray, shape (n_series, 1, n_stamps, 1)
        Input series.
    Y : ndarray, shape (n_series, 1, n_stamps, 2)
        Output series of x and y coordinates.

    References
    ----------
    .. [1] Roni Mittelman "Time-series modeling with undecimated fully
           convolutional neural networks", http://arxiv.org/abs/1508.00317.
    """
    rng = np.random.RandomState(random_state)
    angle = rng.uniform(-np.pi, np.pi, n_series)
    velocity = speed * np.vstack((np.sin(angle), np.cos(angle))).T
    position = np.arange(n_samples)[None, :, None] * velocity[:, None, :]
    position += dynamics_noise * rng.randn(*position.shape)

    D = 10
    t = np.remainder(position + D, 4 * D)
    position = -D + np.minimum(t, 4 * D - t)
    bearing = np.arctan2(position[:, :, 1], position[:, :, 0])
    bearing += measurement_noise * rng.randn(*bearing.shape)

    return bearing[:, :, None], position


def generate_ar(n_series, n_samples, random_state=0):
    """Generate a linear auto-regressive series.

    This simple model is defined as::

        X(t) = 0.4 * X(t - 1) - 0.6 * X(t - 4) + 0.5 * N(0, 1)

    The task is to predict the current value using all the previous values.

    Parameters
    ----------
    n_series : int
        Number of time series to generate.
    n_samples : int
        Number of samples in each time series.
    random_state : int, default 0
        Seed to use in the random generator.

    Returns
    -------
    X, Y : ndarray, shape (n_series, 1, n_stamps, 1)
        Input and output sequences, `Y` is just delayed by 1 sample version
        of `X`.
    """
    n_init = 4
    n_discard = 20
    X = np.zeros((n_series, n_init + n_discard + n_samples + 1))

    rng = np.random.RandomState(random_state)
    X[:, n_init] = rng.randn(n_series)

    for i in range(n_init + 1, X.shape[1]):
        X[:, i] = (0.4 * X[:, i - 1] - 0.6 * X[:, i - 4] +
                   0.1 * rng.randn(n_series))

    Y = X[:, n_init + n_discard + 1:, None]
    X = X[:, n_init + n_discard: -1, None]

    return X, Y
