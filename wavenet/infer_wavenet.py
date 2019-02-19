'''Train'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import os
import sys

import chainer
import chainer.functions as F
import chainer.training
import chainer.training.extensions as extensions
import numpy as np
import scipy.io.wavfile as wavfile
import tqdm

import wavenet.models as models
import wavenet.utils as utils


def generate_and_save_samples(sample_fn, length, count, dir, rate, levels):
    def save_samples(data):
        data = (data * np.reshape(np.arange(levels) / (levels-1), [levels, 1, 1])).sum(
            axis=1, keepdims=True)
        value = np.iinfo(np.int16).max
        audio = (utils.inverse_mulaw(data * 2 - 1) * value).astype(np.int16)
        for idx, sample in enumerate(audio):
            filename = os.path.join(dir, 'sample_{}.wav'.format(idx))
            wavfile.write(filename, rate, np.squeeze(sample))

    samples = chainer.Variable(
        chainer.cuda.cupy.zeros([count, levels, 1, length], dtype='float32'))
    one_hot_ref = chainer.cuda.cupy.eye(levels).astype('float32')

    with tqdm.tqdm(total=length) as bar:
        for i in range(length):
            probs = F.softmax(sample_fn(samples))[:, :, 0, 0, i]
            samples.data[:, :, 0, i] = one_hot_ref[utils.sample_from(probs.data.get())]
            bar.update()

    samples.to_cpu()
    save_samples(samples.data)

def main():
    parser = argparse.ArgumentParser(description='PixelCNN')
    parser.add_argument('--gpu', '-g', type=int, default=-1,
                        help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--model', '-m', default='',
                        help='Path to model for generation')
    parser.add_argument('--hidden_dim', type=int, default=32,
                        help='Number of hidden dimensions')
    parser.add_argument('--out_hidden_dim', type=int, default=32,
                        help='Number of hidden dimensions')
    parser.add_argument('--stacks_num', '-s', type=int, default=5,
                        help='Number of stacks')
    parser.add_argument('--layers_num', '-l', type=int, default=10,
                        help='Number of layers per stack')
    parser.add_argument('--levels', type=int, default=256,
                        help='Level number to quantisize pixel values')
    parser.add_argument('--output', '-o', type=str, default='samples/',
                        help='Output sample directory')
    parser.add_argument('--label', type=np.int32, default=0,
                        help='Class label to generate')
    parser.add_argument('--count', '-c', type=int, default=10,
                        help='Number of samples to generate')
    parser.add_argument('--rate', type=int, default=8000,
                        help='Samples rate')
    parser.add_argument('--length', type=int, default=4096, help='Output sample length')
    args = parser.parse_args()

    model = models.WaveNet(args.levels, args.hidden_dim, args.out_hidden_dim, args.stacks_num,
                       args.layers_num, 2)
    if args.gpu >= 0:
        chainer.cuda.get_device(args.gpu).use()
        model.to_gpu()
    chainer.serializers.load_npz(args.model, model)

    def sample_fn(samples):
        B, C, H, W = samples.shape
        return model(samples, np.ones(B).astype('i') * args.label)

    generate_and_save_samples(
        sample_fn, args.length, args.count, args.output, args.rate, args.levels)


if __name__ == '__main__':
    sys.exit(main())
