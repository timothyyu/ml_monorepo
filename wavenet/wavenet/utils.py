'''Utilities.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import itertools
import operator
import os

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

from chainer.dataset.dataset_mixin import DatasetMixin


def binarize(images, xp=np):
    """
    Stochastically binarize values in [0, 1] by treating them as p-values of
    a Bernoulli distribution.
    """
    return (xp.random.uniform(size=images.shape) < images).astype('i')


def quantisize(images, levels):
    return (np.digitize(images, np.arange(levels) / levels) - 1).astype('i')


def convert_to_rgb(images, xp=np):
    return xp.tile(images, [1, 3, 1, 1])


def sample_from(distribution):
    batch_size, bins = distribution.shape
    return np.array([np.random.choice(bins, p=distr) for distr in distribution])


def extract_labels(data):
    return np.fromiter(map(operator.itemgetter(1), data), dtype='i')


def extract_images(data):
    return np.array(list(map(operator.itemgetter(0), data))).astype('f')


def mulaw(audio, mu=255):
    return np.sign(audio) * np.log1p(mu * np.abs(audio)) / np.log1p(mu)


def inverse_mulaw(data, mu=255):
    return np.sign(data) * ((mu + 1) ** np.abs(data) - 1) / mu


def wav_to_float(audio, bits=16):
    '''Squash -2 ** 15; 2 ** 15 into [-1, 1] range'''
    return audio / 2 ** (bits-1)


def wav_files_in(dir):
    for path, _, files in os.walk(dir):
        names = [name for name in files if '.wav' in name]
        for name in names:
            yield os.path.join(path, name)


def _preprocess(ifilename, rate, chunk_length):
    # data within [-32768 / 2, 32767 / 2] interval
    baserate, data = wavfile.read(ifilename)
    audio = signal.resample_poly(data, rate, baserate)
    # audio within [0; 1] interval: wav_to_float converts it to be in [-1;1] interval
    # mulaw leaves it within same interval, then we shift it to be in [0;1] interval
    audio = mulaw(wav_to_float(audio)) * 0.5 + 0.5
    while len(audio) >= chunk_length:
        yield audio[:chunk_length]
        audio = audio[chunk_length:]


def nth(iterable, n, default=None):
    "Returns the nth item or a default value (from itertool recipes)"
    return next(itertools.islice(iterable, n, None), default)


def receptive_field_size(layers, stacks):
    return stacks * 2 ** layers


#%%
class VCTK(DatasetMixin):
    def __init__(self, root_dir, receptive_field_size):
        self._levels = 256
        self._receptive_field_size = receptive_field_size
        self._populate(root_dir)

    def _populate(self, dir):
        data = []
        files = [os.path.join(dir, name) for name in os.listdir(dir) if 'vctk_' in name]

        for name in files:
            with open(name, 'rb') as ifile:
                fstat = os.fstat(ifile.fileno())
                while ifile.tell() < fstat.st_size:
                    d = np.load(ifile)
                    data.append(d)
        data = np.concatenate(data)
        count, width = data.shape
        labels = quantisize(data, self._levels)
        data = np.eye(self._levels)[labels].astype(np.float32)
        self.data = np.expand_dims(np.transpose(data, [0, 2, 1]), 2)
        self.labels = np.reshape(labels, [count, 1, 1, width])
        self.labels[:, :, :, :self._receptive_field_size] = -1

    def __len__(self):
        return len(self.data)

    def get_example(self, i):
        return (self.data[i], self.labels[i], np.array(0))
