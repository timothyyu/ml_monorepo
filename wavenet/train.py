'''Train'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
import sys
import numpy as np

import chainer
import chainer.training
import chainer.training.extensions as extensions

import wavenet.models as models
import wavenet.utils as utils
import wavenet.parameter_statistics as stats


DATA_LOADER = {
    'mnist': chainer.datasets.get_mnist,
    'cifar': chainer.datasets.get_cifar10,
}


def main():
    parser = argparse.ArgumentParser(description='PixelCNN')
    parser.add_argument('--batchsize', '-b', type=int, default=16,
                        help='Number of images in each mini-batch')
    parser.add_argument('--epoch', '-e', type=int, default=20,
                        help='Number of sweeps over the dataset to train')
    parser.add_argument('--gpu', '-g', type=int, default=-1,
                        help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--resume', '-r', default='',
                        help='Resume the training from snapshot')
    parser.add_argument('--out', '-o', default='',
                        help='Output directory')
    parser.add_argument('--hidden_dim', '-d', type=int, default=128,
                        help='Number of hidden dimensions')
    parser.add_argument('--out_hidden_dim', type=int, default=16,
                        help='Number of hidden dimensions')
    parser.add_argument('--blocks_num', '-n', type=int, default=15,
                        help='Number of layers')
    parser.add_argument('--clip', type=float, default=1.,
                        help='L2 norm gradient clipping')
    parser.add_argument('--weight_decay', type=float, default=0.0001,
                        help='Weight decay rate (L2 regularization)')
    parser.add_argument('--learning_rate', type=float, default=0.001,
                        help='Bound for gradient hard clipping')
    parser.add_argument('--levels', type=int, default=2,
                        help='Level number to quantisize pixel values')
    parser.add_argument('--dataset', type=str, default='mnist',
                        help='Dataset for training. Either mnist or cifar.')
    parser.add_argument('--stats', type=bool, default=False,
                        help='Collect layerwise statistics')
    args = parser.parse_args()

    IN_CHANNELS = 3  # RGB
    # multiply hidden dim by IN_CHANNELS to make sure mask is disible by IN_CHANNELS
    model = models.Classifier(models.PixelCNN(
        IN_CHANNELS, args.hidden_dim, args.blocks_num, args.out_hidden_dim, args.levels))

    loader = DATA_LOADER[args.dataset]
    train, test = loader(ndim=3, withlabel=True) # shape is B, C, H, W
    # XXX: Better way to get classes?
    train_class, test_class = utils.extract_labels(train), utils.extract_labels(test)
    train, test = utils.extract_images(train), utils.extract_images(test)

    if args.dataset == 'mnist':
        train, test = utils.convert=utils.convert_to_rgb(train), utils.convert_to_rgb(test)

    train_l = utils.quantisize(train, args.levels)
    test_l = utils.quantisize(test, args.levels)

    if args.gpu >= 0:
        chainer.cuda.get_device(args.gpu).use()
        model.to_gpu()

        train = chainer.cuda.to_gpu(train_l.astype('f') / (args.levels - 1), device=args.gpu)
        test = chainer.cuda.to_gpu(test_l.astype('f') / (args.levels - 1), device=args.gpu)
        train_l = chainer.cuda.to_gpu(np.squeeze(train_l), device=args.gpu)
        test_l = chainer.cuda.to_gpu(np.squeeze(test_l), device=args.gpu)

    train = chainer.datasets.TupleDataset(train, train_l, train_class)
    test = chainer.datasets.TupleDataset(test, test_l, test_class)

    optimizer = chainer.optimizers.Adam(args.learning_rate)
    optimizer.setup(model)
    optimizer.add_hook(chainer.optimizer.GradientClipping(args.clip))
    optimizer.add_hook(chainer.optimizer.WeightDecay(args.weight_decay))

    train_iter = chainer.iterators.SerialIterator(train, args.batchsize)
    test_iter = chainer.iterators.SerialIterator(test, args.batchsize,
                                                 repeat=False, shuffle=False)

    updater = chainer.training.StandardUpdater(train_iter, optimizer, device=args.gpu)
    trainer = chainer.training.Trainer(updater, (args.epoch, 'epoch'), out=args.out)

    log_trigger = (1, 'epoch')
    trainer.extend(extensions.Evaluator(test_iter, model, device=args.gpu))

    trainer.extend(extensions.snapshot(), trigger=(1, 'epoch'))
    trainer.extend(extensions.snapshot_object(
        model.predictor, 'pixelcnn_{.updater.iteration}'), trigger=(1, 'epoch'))
    trainer.extend(extensions.LogReport(trigger=log_trigger))
    trainer.extend(extensions.PrintReport(
        ['epoch', 'iteration', 'main/nll', 'validation/main/nll', 'elapsed_time',
         'main/bits/dim', 'validation/bits/dim']))
    trainer.extend(extensions.ProgressBar())
    if args.stats:
        trainer.extend(stats.ParameterStatistics([
            model.predictor.conv1,
            model.predictor.conv2,
            model.predictor.conv4], trigger=log_trigger), trigger=log_trigger)

    if args.resume:
        chainer.serializers.load_npz(args.resume, trainer)

    trainer.run()


if __name__ == '__main__':
    sys.exit(main())
