'''Models.'''
#%%
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools

import numpy as np
import chainer
import chainer.functions as F
import chainer.links as L

import wavenet.utils as utils


INIT = chainer.initializers.HeUniform()


class MaskedConvolution2D(L.Convolution2D):
    def __init__(self, *args, mask='B', **kwargs):
        super(MaskedConvolution2D, self).__init__(
            *args, **kwargs
        )

        Cout, Cin, kh, kw = self.W.shape
        pre_mask = self.xp.ones_like(self.W.data).astype('f')
        yc, xc = kh // 2, kw // 2

        # context masking - subsequent pixels won't hav access to next pixels (spatial dim)
        pre_mask[:, :, yc+1:, :] = 0.0
        pre_mask[:, :, yc:, xc+1:] = 0.0

        # same pixel masking - pixel won't access next color (conv filter dim)
        def bmask(i_out, i_in):
            cout_idx = np.expand_dims(np.arange(Cout) % 3 == i_out, 1)
            cin_idx = np.expand_dims(np.arange(Cin) % 3 == i_in, 0)
            a1, a2 = np.broadcast_arrays(cout_idx, cin_idx)
            return a1 * a2

        for j in range(3):
            pre_mask[bmask(j, j), yc, xc] = 0.0 if mask == 'A' else 1.0

        pre_mask[bmask(0, 1), yc, xc] = 0.0
        pre_mask[bmask(0, 2), yc, xc] = 0.0
        pre_mask[bmask(1, 2), yc, xc] = 0.0

        self.mask = pre_mask

    def __call__(self, x):
        if self.has_uninitialized_params:
            with chainer.cuda.get_device(self._device_id):
                self._initialize_params(x.shape[1])

        return chainer.functions.connection.convolution_2d.convolution_2d(
            x, self.W * self.mask, self.b, self.stride, self.pad, self.use_cudnn,
            deterministic=self.deterministic)

    def to_gpu(self, device=None):
        self._persistent.append('mask')
        res = super().to_gpu(device)
        self._persistent.remove('mask')
        return res


class CroppedConvolution(L.Convolution2D):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def __call__(self, x):
        ret = super().__call__(x)
        kh, kw = self.ksize
        pad_h, pad_w = self.pad
        h_crop = -(kh + 1) if pad_h == kh else None
        w_crop = -(kw + 1) if pad_w == kw else None
        return ret[:, :, :h_crop, :w_crop]


class ResidualBlock(chainer.Chain):
    def __init__(self, in_channels, out_channels, filter_size, mask='B', nobias=False):
        super(ResidualBlock, self).__init__(
            vertical_conv_t=CroppedConvolution(
                in_channels, out_channels, ksize=[filter_size//2+1, filter_size],
                pad=[filter_size//2+1, filter_size//2]),
            vertical_conv_s=CroppedConvolution(
                in_channels, out_channels, ksize=[filter_size//2+1, filter_size],
                pad=[filter_size//2+1, filter_size//2]),
            v_to_h_conv_t=L.Convolution2D(out_channels, out_channels, 1),
            v_to_h_conv_s=L.Convolution2D(out_channels, out_channels, 1),

            horizontal_conv_t=MaskedConvolution2D(
                in_channels, out_channels, ksize=[1, filter_size],
                pad=[0, filter_size // 2], mask=mask),
            horizontal_conv_s=MaskedConvolution2D(
                in_channels, out_channels, ksize=[1, filter_size],
                pad=[0, filter_size // 2], mask=mask),

            horizontal_output=MaskedConvolution2D(out_channels, out_channels, 1, mask=mask),
            label=L.EmbedID(10, out_channels)
        )

    def __call__(self, v, h, label):
        v_t = self.vertical_conv_t(v)
        v_s = self.vertical_conv_s(v)
        to_vertical_t = self.v_to_h_conv_t(v_t)
        to_vertical_s = self.v_to_h_conv_s(v_s)

        # v_gate = self.vertical_gate_conv(v)
        # label bias is added to both vertical and horizontal conv
        # here we take only shape as it should be the same
        label = F.broadcast_to(F.expand_dims(F.expand_dims(self.label(label), -1), -1), v_t.shape)
        v_t, v_s = v_t + label, v_s + label
        v = F.tanh(v_t) * F.sigmoid(v_s)

        h_t = self.horizontal_conv_t(h)
        h_s = self.horizontal_conv_s(h)
        h_t, h_s = h_t + to_vertical_t + label, h_s + to_vertical_s + label
        h = self.horizontal_output(F.tanh(h_t) * F.sigmoid(h_s))

        return v, h


class ResidualBlockList(chainer.ChainList):
    def __init__(self, block_num, *args, **kwargs):
        blocks = [ResidualBlock(*args, **kwargs) for _ in range(block_num)]
        super(ResidualBlockList, self).__init__(*blocks)

    def __call__(self, v, h, label):
        for block in self:
            v_, h_ = block(v, h, label)
            v, h = v_, h + h_
        return v, h


class PixelCNN(chainer.Chain):
    def __init__(self, in_channels, hidden_dims, block_num, out_hidden_dims, out_dims, nobias=False):
        super(PixelCNN, self).__init__(
            conv1=ResidualBlock(in_channels, hidden_dims, 7, mask='A', nobias=nobias),
            blocks=ResidualBlockList(block_num, hidden_dims, hidden_dims, 3, nobias=nobias),
            conv2=MaskedConvolution2D(hidden_dims, out_hidden_dims, 1, nobias=nobias),
            conv4=MaskedConvolution2D(out_hidden_dims, out_dims * in_channels, 1, nobias=nobias)
        )
        self.in_channels = in_channels
        self.out_dims = out_dims

    def __call__(self, x, label):
        v, h = self.conv1(x, x, label)
        # XXX: Consider doing something with vertical stack output as well
        _, h = self.blocks(v, h, label)
        h = self.conv2(F.relu(h))
        h = self.conv4(F.relu(h))

        batch_size, _, height, width = h.shape
        h = F.reshape(h, [batch_size, self.out_dims, self.in_channels, height, width])

        return h


# TODO: rename class
class Classifier(chainer.Chain):
     def __init__(self, predictor):
         super(Classifier, self).__init__(predictor=predictor)

     def __call__(self, x, t, label):
         y = self.predictor(x, label)
         dims = self.xp.prod(np.array(y.shape[2:]))  # for CIFAR should be 3072

         nll = F.softmax_cross_entropy(y, t, normalize=True)
         chainer.report({'nll': nll, 'bits/dim': nll / dims}, self)
         return nll


class CausalDilatedConvolution1D(chainer.links.DilatedConvolution2D):
    def __init__(self, in_channels, out_channels, pad, dilate, kernel_width, *args, **kwargs):
        pad = dilate if pad is None else pad
        super().__init__(
            in_channels, out_channels, ksize=[1, kernel_width], pad=[0, pad], dilate=[1, dilate],
            *args, **kwargs
        )
        self.crop = 2 * pad - dilate

    def __call__(self, x):
        ret = super().__call__(x)
        return ret[:, :, :, :-self.crop]  # B, C, 1, W


class CausalLayer(chainer.Chain):
    def __init__(self, in_channels, out_channels, dilate, kernel_width):
        super().__init__(
            gated_conv=CausalDilatedConvolution1D(
                in_channels, 2*out_channels, None, dilate, kernel_width,
                initialW=INIT),
            res_conv=L.Convolution2D(out_channels, in_channels, 1, initialW=INIT),
            skip_conv=L.Convolution2D(out_channels, in_channels, 1, initialW=INIT)
        )

    def __call__(self, x):
        x_ = self.gated_conv(x)
        x_tanh, x_sigmoid = F.split_axis(x_, 2, axis=1)

        x_ = F.tanh(x_tanh) * F.sigmoid(x_sigmoid)
        x1 = self.res_conv(x_)
        x2 = self.skip_conv(x_)
        return x + x1, x2


class CausalStack(chainer.ChainList):
    def __init__(self, layers_num, in_channels, out_channels, kernel_width):
        layers = [CausalLayer(in_channels, out_channels, 2 ** i, kernel_width)
                  for i in range(layers_num)]
        super().__init__(*layers)

    def __call__(self, x):
        skip_conn = []
        for layer in self:
            x, skip_ = layer(x)
            skip_conn.append(skip_)
        return x, skip_conn


class StackList(chainer.ChainList):
    def __init__(self, stack_num, *args, **kwargs):
        stacks = [CausalStack(*args, **kwargs) for _ in range(stack_num)]
        super().__init__(*stacks)

    def __call__(self, x):
        skip_conn = []
        for stack in self:
            x, skip = stack(x)
            skip_conn.extend(skip)
        return x, skip_conn


class WaveNet(chainer.Chain):
    def __init__(self, out_channels, hidden_dim, out_hidden_dim, stacks_num,
                 layers_num, kernel_width):
        super().__init__(
            conv1=CausalDilatedConvolution1D(out_channels, hidden_dim, 2, 1, 2, initialW=INIT),
            stacks=StackList(stacks_num, layers_num, hidden_dim, hidden_dim, kernel_width),
            conv2=L.Convolution2D(hidden_dim, out_hidden_dim, 1, initialW=INIT),
            conv3=L.Convolution2D(out_hidden_dim, out_channels, 1, initialW=INIT),
        )
        self.out_channels = out_channels

    def __call__(self, x, label):
        x, skip = self.stacks(self.conv1(x))
        x = self.conv2(F.relu(x+sum(skip)))
        x = self.conv3(F.relu(x))

        batch_size, _, _, width = x.shape
        x = F.reshape(x, [batch_size, self.out_channels, 1, 1, width])
        return x
