# -*- coding: utf-8 -*-
from __future__ import absolute_import

from keras import backend as K
from keras import activations, initializations, regularizers, constraints
from keras.engine import Layer, InputSpec

import tensorflow as tf


def deconv_output_length(input_length, filter_size, border_mode, stride):
    print("input_lenght: {}, filter_size: {}, border_mode: {}, stride: {}".format(
        input_length, filter_size, border_mode, stride
    ))
    if input_length is None:
        return None
    assert border_mode in {'same', 'valid'}
    if border_mode == 'same':
        output_length = input_length * stride
    elif border_mode == 'valid':
        # output_length = input_length * stride - filter_size + 1
        output_length = (input_length - 1) * stride + filter_size
    return output_length


class Convolution2D_Transpose(Layer):
    """
        Creates a 2D Convolution Transpose layer (sometimes called "Deconvolution").
        Based on code by Xiaomin Wu in "[fchollet/keras] Anyone implemented a Deconvolutional                    
              layer combined the Keras and Tensorflow? (#2106)"

        Must be placed in the keras/layers/ directory.

        W_shape --- shape of the weights - should be calculated internally
         [filter_dim_y, filter_dim_x, self.nb_filter(=number of channels in output), number_of_channels_in_input]

        b_shape ... shape of the biases - should be calculated internally
         [0] ... nb_filter 

        strides 
         Strides of the filters
         [stride_in_batch_size(must be 1), stride_y, stride_x, stride_in_depth (must be 1)]

        deconv_shape
         this is output_shape of TF conv2d_transpose
         deconv_shape = [batch_size, output_size_y, output_size_x, number_of_filters]

        padding: valid|same (small caps)

        input_dim, input_length ... Keras input parameters


        Also U can set the output_shape(deconv_shape) according to:

        def conv_transpose_out_length(input_size, filter_size, border_mode, stride):
            if input_size is None:
                return None
            if border_mode == 'valid':
                output_size = (input_size - 1) * stride + filter_size
            elif border_mode == 'same':
                output_size = input_size
            return output_size
          
    """

    input_ndim = 4

    def __init__(self,
                 init='glorot_uniform', activation='linear', weights=None,
                 padding='valid', strides=[1,1,1,1], deconv_shape=[], W_shape = [],b_shape=[],
                 W_regularizer=None, b_regularizer=None, activity_regularizer=None,
                 W_constraint=None, b_constraint=None, input_dim=None, input_length=None, **kwargs):

        if padding not in {'valid','same'}:
            raise Exception('Invalid border mode for Convolution2D:', padding)
        self.deconv_shape = deconv_shape
        self.init = initializations.get(init)
        self.activation = activations.get(activation)
        assert padding in {'valid', 'same'}, 'border_mode must be in {valid, same}'
        self.padding = padding
        self.strides = strides

        self.W_regularizer = regularizers.get(W_regularizer)
        self.b_regularizer = regularizers.get(b_regularizer)
        self.activity_regularizer = regularizers.get(activity_regularizer)

        self.W_shape = W_shape
        self.b_shape = b_shape

        self.W_constraint = constraints.get(W_constraint)
        self.b_constraint = constraints.get(b_constraint)
        self.constraints = [self.W_constraint, self.b_constraint]

        self.initial_weights = weights
        #self.input = K.placeholder(ndim=4) # old keras 0.3.x

        # Keras 1.0:
        self.input_spec = [InputSpec(ndim=4)]
        self.initial_weights = weights
        self.input_dim = input_dim
        self.input_length = input_length
        if self.input_dim:
            kwargs['input_shape'] = (self.input_length, self.input_dim)

        super(Convolution2D_Transpose, self).__init__(**kwargs)

    def build(self, input_shape):
        input_dim = input_shape[2]
        #self.W_shape = (self.nb_filter, input_dim, self.filter_length, 1) # goven from outside
        self.W = self.init(self.W_shape, name='{}_W'.format(self.name))
        self.b = K.zeros((self.b_shape), name='{}_b'.format(self.name))
        self.trainable_weights = [self.W, self.b]
        self.regularizers = []

        if self.W_regularizer:
            self.W_regularizer.set_param(self.W)
            self.regularizers.append(self.W_regularizer)

        if self.b_regularizer:
            self.b_regularizer.set_param(self.b)
            self.regularizers.append(self.b_regularizer)

        if self.activity_regularizer:
            self.activity_regularizer.set_layer(self)
            self.regularizers.append(self.activity_regularizer)

        self.constraints = {}
        if self.W_constraint:
            self.constraints[self.W] = self.W_constraint
        if self.b_constraint:
            self.constraints[self.b] = self.b_constraint

        if self.initial_weights is not None:
            self.set_weights(self.initial_weights)
            del self.initial_weights


    @property
    def get_output_shape(self, input_shape):
        return self.deconv_shape

    def call(self, X,  mask=None):
        #X = self.get_input(train)
        X = K.permute_dimensions(X, (0, 2, 3, 1))
        conv_out = tf.nn.conv2d_transpose(X, self.W, strides=self.strides,
                                          padding=self.padding.upper(),
                                          output_shape=self.deconv_shape)

        output = conv_out + K.reshape(self.b, (1, 1, 1, self.W_shape[2]))
        return K.permute_dimensions(output, (0, 3, 1, 2))

    def get_config(self):
        config = {
                  'init': self.init.__name__,
                  'activation': self.activation.__name__,
                  'padding': self.padding,
                  'strides': self.strides,
                  'W_regularizer': self.W_regularizer.get_config() if self.W_regularizer else None,
                  'b_regularizer': self.b_regularizer.get_config() if self.b_regularizer else None,
                  'activity_regularizer': self.activity_regularizer.get_config() if self.activity_regularizer else None,
                  'W_constraint': self.W_constraint.get_config() if self.W_constraint else None,
                  'b_constraint': self.b_constraint.get_config() if self.b_constraint else None,
                  'W_shape': self.W_shape,
                  'b_shape': self.b_shape,
                  'deconv_shape': self.deconv_shape }
        base_config = super(Convolution2D_Transpose, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

    def get_output_shape_for(self, input_shape):
        return (self.deconv_shape[0],self.deconv_shape[1],self.deconv_shape[2],self.deconv_shape[3])
 
class Convolution1D_Transpose(Layer):
    """
        Creates a 1D Convolution Transpose layer (sometimes called "Deconvolution").
        Based on code by Xiaomin Wu in "[fchollet/keras] Anyone implemented a Deconvolutional
              layer combined the Keras and Tensorflow? (#2106)"

        Must be placed in the keras/layers/ directory.

        W_shape --- shape of the weights - should be calculated internally
         [filter_dim_x, self.nb_filter(=number of channels in output), number_of_channels_in_input]

        b_shape ... shape of the biases - should be calculated internally
         [0] ... nb_filter

        strides
         Strides of the filters
         [stride_in_batch_size(must be 1), stride_x, stride_in_depth (must be 1)]

        deconv_shape
         this is output_shape of TF conv2d_transpose
         deconv_shape = [batch_size, output_size_x, number_of_filters]

        padding: valid|same (small caps)

        input_dim, input_length ... Keras input parameters


        Also U can set the output_shape(deconv_shape) according to:

        def conv_transpose_out_length(input_size, filter_size, border_mode, stride):
            if input_size is None:
                return None
            if border_mode == 'valid':
                output_size = (input_size - 1) * stride + filter_size
            elif border_mode == 'same':
                output_size = input_size
            return output_size

    """

    input_ndim = 3

    def __init__(self,
                 init='glorot_uniform', activation='linear', weights=None,
                 padding='valid', strides=[1,1,1], deconv_shape=[], W_shape = [],b_shape=[],
                 W_regularizer=None, b_regularizer=None, activity_regularizer=None,
                 W_constraint=None, b_constraint=None, input_dim=None, input_length=None, **kwargs):

        if padding not in {'valid','same'}:
            raise Exception('Invalid border mode for Convolution1D:', padding)
        #self.deconv_shape = deconv_shape

        # transform 1 D in 2D
        #deconv_shape = [batch_size, output_size_y, output_size_x, number_of_filters]
        self.deconv_shape = [deconv_shape[0],1,deconv_shape[1],deconv_shape[2]]

        self.init = initializations.get(init)
        self.activation = activations.get(activation)
        assert padding in {'valid', 'same'}, 'border_mode must be in {valid, same}'
        self.padding = padding
        self.strides = [strides[0],1,strides[1],strides[2]]

        self.W_regularizer = regularizers.get(W_regularizer)
        self.b_regularizer = regularizers.get(b_regularizer)
        self.activity_regularizer = regularizers.get(activity_regularizer)

        self.W_shape = [1, W_shape[0], W_shape[1], W_shape[2]]
        self.b_shape = b_shape

        self.W_constraint = constraints.get(W_constraint)
        self.b_constraint = constraints.get(b_constraint)
        self.constraints = [self.W_constraint, self.b_constraint]

        self.initial_weights = weights
        #self.input = K.placeholder(ndim=4) # old keras 0.3.x

        # Keras 1.0:
        self.input_spec = [InputSpec(ndim=3)]
        self.initial_weights = weights
        self.input_dim = input_dim
        self.input_length = input_length
        if self.input_dim:
            kwargs['input_shape'] = (self.input_length, self.input_dim)

        super(Convolution1D_Transpose, self).__init__(**kwargs)

    def build(self, input_shape):
        input_dim = input_shape[2]
        # self.W_shape = (self.nb_filter, input_dim, self.filter_length, 1)
        self.W = self.init(self.W_shape, name='{}_W'.format(self.name))
        self.b = K.zeros((self.b_shape), name='{}_b'.format(self.name))
        self.trainable_weights = [self.W, self.b]
        self.regularizers = []

        if self.W_regularizer:
            self.W_regularizer.set_param(self.W)
            self.regularizers.append(self.W_regularizer)

        if self.b_regularizer:
            self.b_regularizer.set_param(self.b)
            self.regularizers.append(self.b_regularizer)

        if self.activity_regularizer:
            self.activity_regularizer.set_layer(self)
            self.regularizers.append(self.activity_regularizer)

        self.constraints = {}
        if self.W_constraint:
            self.constraints[self.W] = self.W_constraint
        if self.b_constraint:
            self.constraints[self.b] = self.b_constraint

        if self.initial_weights is not None:
            self.set_weights(self.initial_weights)
            del self.initial_weights


    @property
    def get_output_shape(self, input_shape):
        return self.deconv_shape

    def call(self, X,  mask=None):
        # 1D -> 2D
        X = K.expand_dims(X,2)
        X = K.permute_dimensions(X, (0, 2, 3, 1))
        conv_out = tf.nn.conv2d_transpose(X, self.W, strides=self.strides,
                                          padding=self.padding.upper(),
                                          output_shape=self.deconv_shape)

        output = conv_out + K.reshape(self.b, (1, 1, 1, self.W_shape[2]))
        output =  K.permute_dimensions(output, (0, 3, 1, 2))
        # 2D -> 1D
        output = K.squeeze(output,2)
        return output

    def get_config(self):
        config = {
                  'init': self.init.__name__,
                  'activation': self.activation.__name__,
                  'padding': self.padding,
                  'strides': self.strides,
                  'W_regularizer': self.W_regularizer.get_config() if self.W_regularizer else None,
                  'b_regularizer': self.b_regularizer.get_config() if self.b_regularizer else None,
                  'activity_regularizer': self.activity_regularizer.get_config() if self.activity_regularizer else None,
                  'W_constraint': self.W_constraint.get_config() if self.W_constraint else None,
                  'b_constraint': self.b_constraint.get_config() if self.b_constraint else None,
                  'W_shape': self.W_shape,
                  'b_shape': self.b_shape,
                  'deconv_shape': self.deconv_shape }
        base_config = super(Convolution1D_Transpose, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

    def get_output_shape_for(self, input_shape):
        #return (self.deconv_shape[0],self.deconv_shape[1],self.deconv_shape[2],self.deconv_shape[3])
        return (self.deconv_shape[0],self.deconv_shape[1],self.deconv_shape[2])
 

class Convolution1D_Transpose_Arbitrary(Layer):
    """
        Creates a 1D Convolution Transpose layer (sometimes called "Deconvolution").
        Based on code by Xiaomin Wu in "[fchollet/keras] Anyone implemented a Deconvolutional
              layer combined the Keras and Tensorflow? (#2106)"

        Must be placed in the keras/layers/ directory.

        W_shape --- shape of the weights - should be calculated internally
         [filter_dim_x, self.nb_filter(=number of channels in output), number_of_channels_in_input]

        b_shape ... shape of the biases - should be calculated internally
         [0] ... nb_filter

        strides
         Strides of the filters
         [stride_in_batch_size(must be 1), stride_x, stride_in_depth (must be 1)]

        deconv_shape
         this is output_shape of TF conv2d_transpose
         deconv_shape = [batch_size, output_size_x, number_of_filters]

        padding: valid|same (small caps)

        input_dim, input_length ... Keras input parameters


        Also U can set the output_shape(deconv_shape) according to:

        def conv_transpose_out_length(input_size, filter_size, border_mode, stride):
            if input_size is None:
                return None
            if border_mode == 'valid':
                output_size = (input_size - 1) * stride + filter_size
            elif border_mode == 'same':
                output_size = input_size
            return output_size
Convolution1D_Transpose_Arbitrary
    """

    input_ndim = 3

    def __init__(self, nb_filter, filter_length,
                 init='glorot_uniform', activation='linear', weights=None,
                 padding='valid', strides=[1,1,1],
                 W_regularizer=None, b_regularizer=None, activity_regularizer=None,
                 W_constraint=None, b_constraint=None, input_dim=None, input_length=None, **kwargs):

        if padding not in {'valid','same'}:
            raise Exception('Invalid border mode for Convolution1D:', padding)
        #self.deconv_shape = deconv_shape

        # transform 1 D in 2D
        #deconv_shape = [batch_size, output_size_y, output_size_x, number_of_filters]
        # self.deconv_shape = [deconv_shape[0],1,deconv_shape[1],deconv_shape[2]]

        self.nb_filter = nb_filter
        self.filter_length = filter_length
        self.init = initializations.get(init)
        self.activation = activations.get(activation)
        assert padding in {'valid', 'same'}, 'border_mode must be in {valid, same}'
        self.padding = padding
        # necessary for loading, since a 4 dim. stride will be saved
        if len(strides) == 3:
            self.strides = [strides[0], 1, strides[1], strides[2]]
        else:
            self.strides = strides

        self.W_regularizer = regularizers.get(W_regularizer)
        self.b_regularizer = regularizers.get(b_regularizer)
        self.activity_regularizer = regularizers.get(activity_regularizer)

        # self.W_shape = [1, W_shape[0], W_shape[1], W_shape[2]]
        # self.b_shape = b_shape

        self.W_constraint = constraints.get(W_constraint)
        self.b_constraint = constraints.get(b_constraint)
        self.constraints = [self.W_constraint, self.b_constraint]

        self.initial_weights = weights
        #self.input = K.placeholder(ndim=4) # old keras 0.3.x

        # Keras 1.0:
        self.input_spec = [InputSpec(ndim=3)]
        self.initial_weights = weights
        self.input_dim = input_dim
        self.input_length = input_length
        if self.input_dim:
            kwargs['input_shape'] = (self.input_length, self.input_dim)
        super(Convolution1D_Transpose_Arbitrary, self).__init__(**kwargs)


    def build(self, input_shape):
        input_dim = input_shape[2]
        # self.W_shape = (self.nb_filter, input_dim, self.filter_length, 1)
        self.W_shape = (1, self.filter_length, self.nb_filter, input_dim)
        print("Weights shape (filter_height, filter_width, nb_filter, input_dim): ", self.W_shape)
        self.W = self.init(self.W_shape, name='{}_W'.format(self.name))
        self.b = K.zeros((self.nb_filter), name='{}_b'.format(self.name))
        self.trainable_weights = [self.W, self.b]
        self.regularizers = []

        if self.W_regularizer:
            self.W_regularizer.set_param(self.W)
            self.regularizers.append(self.W_regularizer)

        if self.b_regularizer:
            self.b_regularizer.set_param(self.b)
            self.regularizers.append(self.b_regularizer)

        if self.activity_regularizer:
            self.activity_regularizer.set_layer(self)
            self.regularizers.append(self.activity_regularizer)

        self.constraints = {}
        if self.W_constraint:
            self.constraints[self.W] = self.W_constraint
        if self.b_constraint:
            self.constraints[self.b] = self.b_constraint

        if self.initial_weights is not None:
            self.set_weights(self.initial_weights)
            del self.initial_weights


    def get_output_shape_for(self, input_shape=None):
        length = deconv_output_length(input_shape[1],
                                    self.filter_length,
                                    self.padding,
                                    self.strides[2])
        print("Output length: ", length)
        return (input_shape[0], length, self.nb_filter)


    def call(self, X, mask=None):
        # 1D -> 2D
        batch = K.shape(X)[0]
        width = deconv_output_length(K.shape(X)[1],
                                    self.filter_length,
                                    self.padding,
                                    self.strides[2])

        print("Output width: ", width)

        print("Input shape: ", K.shape(X))
        X = K.expand_dims(X,2)
        print("Input shape after expand: ", K.shape(X))
        # X = K.permute_dimensions(X, (0, 2, 3, 1))
        X = K.permute_dimensions(X, (0, 2, 1, 3))
        print("Input shape after permute: ", K.shape(X))
        deconv_shape = tf.pack([batch, 1, width, self.nb_filter])
        print("Deconv shape: ", deconv_shape)
        conv_out = tf.nn.conv2d_transpose(X, self.W, strides=self.strides,
                                          padding=self.padding.upper(),
                                          output_shape=deconv_shape)

        output = conv_out + K.reshape(self.b, (1, 1, 1, self.W_shape[2]))
        print("Output shape: ", K.shape(output))
        # output =  K.permute_dimensions(output, (0, 3, 1, 2))
        output =  K.permute_dimensions(output, (0, 2, 1, 3))
        print("Output shape after permute: ", K.shape(output))
        # 2D -> 1D
        output = K.squeeze(output,2)
        print("Output shape after squeeze: ", K.shape(output))
        return output

    def get_config(self):
        config = {
                  'init': self.init.__name__,
                  'activation': self.activation.__name__,
                  'padding': self.padding,
                  'strides': self.strides,
                  'W_regularizer': self.W_regularizer.get_config() if self.W_regularizer else None,
                  'b_regularizer': self.b_regularizer.get_config() if self.b_regularizer else None,
                  'activity_regularizer': self.activity_regularizer.get_config() if self.activity_regularizer else None,
                  'W_constraint': self.W_constraint.get_config() if self.W_constraint else None,
                  'b_constraint': self.b_constraint.get_config() if self.b_constraint else None,
                  'filter_length': self.filter_length,
                  'nb_filter': self.nb_filter,
                  'input_length': self.input_length,
                  'input_dim': self.input_dim
                  }
        base_config = super(Convolution1D_Transpose_Arbitrary, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

    @property
    def get_output_shape(self, input_shape):
        #return (self.deconv_shape[0],self.deconv_shape[1],self.deconv_shape[2],self.deconv_shape[3])
        return self.get_output_shape_for(input_shape=input_shape)
