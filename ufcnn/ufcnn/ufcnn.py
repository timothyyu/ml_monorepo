from __future__ import division
import numpy as np
import tensorflow as tf


def init_conv_weights(shape, seed):
    n = np.prod(shape[:-1])
    initial = tf.random_normal(shape, stddev=(2 / n)**0.5, seed=seed)
    return tf.Variable(initial)


def init_conv_bias(shape):
    initial = tf.constant(0.0, shape=shape)
    return tf.Variable(initial)


def conv(x, w, b, filter_length, dilation):
    padding = [[0, 0], [0, 0], [dilation * (filter_length - 1), 0], [0, 0]]
    x = tf.pad(x, padding)
    if dilation == 1:
        x = tf.nn.conv2d(x, w, [1, 1, 1, 1], padding='VALID')
    else:
        x = tf.nn.atrous_conv2d(x, w, dilation, padding='VALID')

    return x + b


def mse_loss(y_hat, y):
    """Compute mean squared error loss.

    Parameters
    ----------
    y_hat, y : tensor
        Predicted and true values with identical shapes.

    Returns
    -------
    loss : scalar tensor
        Computed MSE loss.
    """
    return tf.reduce_mean(tf.square(y_hat - y))


def softmax(y_hat):
    """Compute softmax activations for a 3-d tensor.

    Parameters
    ----------
    y_hat : tensor, shape (batch_size, n_samples, n_classes)
        Raw predictions of a neural network.

    Returns
    -------
    sf : tensor, shape (batch_size, n_samples, n_classes)
        Computed softmax values, which can be interpreted as probabilities.
    """
    shape = tf.shape(y_hat)
    y_hat = tf.reshape(y_hat, (-1, shape[2]))
    sf = tf.nn.softmax(y_hat)
    return tf.reshape(sf, shape)


def cross_entropy_loss(y_hat, labels, sample_weights=None, sparse=False):
    """Compute cross-entropy loss for a 3-dimensional outputs.

    Parameters
    ----------
    y_hat : tensor, shape (batch_size, n_samples, n_outputs)
        Raw predictions of a neural network.
    labels : tensor
        True labels. It can have shape (batch_size, n_samples), then each
        values should be an index within [0, n_classes). Or alternatively
        it can have shape (batch_size, n_samples, n_outputs), then for each
        sample a probability distribution with n_outputs values should be
        provided (this case also handles one-hot label encoding). Set `sparse`
        parameter to select an appropriate setting.
    sample_weights : None or tensor, default None
        Weight for each sample for summing cross entropies, shape must be
        (batch_size, n_samples). Weights be normalized to unity sum, such
        that the computed sum can be interpreted as a weighted average.
        If None, all weights are assumed to be 1, i.e. a simple average is
        computed.
    sparse : bool, default False
        Whether `labels` are indices or full distributions.

    Returns
    -------
    loss : scalar tensor
        Average cross-entropy loss.
    """
    shape = tf.shape(y_hat)
    y_hat = tf.reshape(y_hat, [-1, shape[2]])
    if sparse:
        labels = tf.reshape(labels, [-1])
        ce = tf.nn.sparse_softmax_cross_entropy_with_logits(y_hat, labels)
    else:
        labels = tf.reshape(labels, [-1, shape[2]])
        ce = tf.nn.softmax_cross_entropy_with_logits(y_hat, labels)

    if sample_weights is None:
        return tf.reduce_mean(ce)
    else:
        weights = tf.reshape(sample_weights, [-1])
        weights = tf.div(weights, tf.reduce_sum(weights))
        return tf.reduce_sum(tf.mul(ce, weights))


def compute_accuracy(y_hat, labels, sparse=False):
    """Compute accuracy for a 3-dimensional outputs.

    The prediction is assumed to be made by argmax.

    Parameters
    ----------
    y_hat : tensor, shape (batch_size, n_samples, n_outputs)
        Raw predictions of a neural network. It is not required to convert it
        to softmax, because softmax is a monotonous transform.
    labels : tensor
        True labels. It can have shape (batch_size, n_samples), then each
        values should be an index within [0, n_classes). Or alternatively
        it can have shape (batch_size, n_samples, n_outputs), then for each
        sample a probability distribution with n_outputs values should be
        provided (this case also handles one-hot label encoding). In the
        latter case the correct label is also selected by argmax. Set `sparse`
        parameter to select an appropriate setting.
    sparse : bool, default False
        Whether `labels` are indices or full distributions.

    Returns
    -------
    accuracy : scalar tensor
        Computed accuracy.
    """
    prediction = tf.arg_max(y_hat, 2)
    if sparse:
        labels = tf.cast(labels, prediction.dtype)
    else:
        labels = tf.arg_max(labels, 2)

    return tf.reduce_mean(tf.cast(tf.equal(prediction, labels), tf.float32))


def construct_ufcnn(n_inputs=1, n_outputs=1, n_levels=1, n_filters=10,
                    filter_length=5, random_seed=0):
    """Construct a Undecimated Fully Convolutional Neural Network.

    The architecture replicates one from the paper [1]_. It is depicted below
    for 3 levels::

        input -- H1 ---------------------------- G1 -- C -- output
                     |                        |
                     -- H2 -------------- G2 --
                           |            |
                           -- H3 -- G3 --

    Here H and G are convolutional layers, each followed by ReLU
    transformation, C is the final convolutional layer. The outputs are
    concatenated at branch merges. All filter (except C) outputs `n_filters`
    signals, but because of concatenations filter G1 and G2 have to process
    2 * `n_filters` signals.

    A filter on level l implicitly contains 2**(l-1) zeros inserted between
    its values. It allows the network to progressively look farther into the
    past and learn dependencies on wide range of time scales.

    The important thing in time-series modeling is applying filters in a
    causal-way, i.e. convolutions must not include values after a current
    time moment. This is achieved by zero-padding from the left before
    applying the convolution.

    Implementation is done in tensorflow.

    Parameters
    ----------
    n_inputs : int, default 1
        Number of input time series.
    n_outputs : int, default 1
        Number of output time series.
    n_levels : int, default 1
        Number of levels in the network, see the picture above.
    n_filters : int, default 10
        Number of filters in each convolutional layers (except the last one).
    filter_length : int, default 5
        Length of the filters.
    random_seed : int or None, default 0
        Random seed to use for weights and biases initialization. None means
        that the seed will be selected "at random".

    Returns
    -------
    x : tensor, shape (batch_size, n_samples, n_inputs)
        Use it to feed input sequences into the network.
    y_hat : tensor, shape (batch_size, n_samples, n_outputs)
        Use it to read-out networks predictions.
    weights : list of tensors, length 2 * n_levels + 1
        List of convolution weights, the order is H, G, C.
    biases : list of tensors, length 2 * n_levels + 1
        List of convolution biases, the order is H, G, C.

    Notes
    -----
    Weights and biases will be initialized with truncated normal random
    variables with std of 0.1, you can reinitialize them using the returned
    `weights` and `biases` lists.

    Weights are initialized from a normal distribution with a standard
    deviation of ``(2 / n) ** 0.5``, where ``n`` is the number of inputs
    to a layer. Biases are initialized to zero. Such initialization is good
    if input time series are standardized to zero mean and unit variance. It
    is advised in [2]_.

    References
    ----------
    .. [1] Roni Mittelman "Time-series modeling with undecimated fully
           convolutional neural networks", http://arxiv.org/abs/1508.00317
    .. [2] Kaiming He et al. "Delving Deep into Rectifiers: Surpassing
           Human-Level Performance on ImageNet Classification",
           http://arxiv.org/abs/1502.01852
    """
    H_weights = []
    H_biases = []
    G_weights = []
    G_biases = []

    for level in range(n_levels):
        if level == 0:
            H_weights.append(
                init_conv_weights([1, filter_length, n_inputs, n_filters],
                                  random_seed))
        else:
            H_weights.append(
                init_conv_weights([1, filter_length, n_filters, n_filters],
                                  random_seed))

        H_biases.append(init_conv_bias([n_filters]))

        if level == n_levels - 1:
            G_weights.append(
                init_conv_weights([1, filter_length, n_filters, n_filters],
                                  random_seed))
        else:
            G_weights.append(
                init_conv_weights([1, filter_length, 2 * n_filters, n_filters],
                                  random_seed))

        G_biases.append(init_conv_bias([n_filters]))

    x_in = tf.placeholder(tf.float32, shape=[None, None, n_inputs])

    # Add height dimensions for 2D convolutions.
    x = tf.expand_dims(x_in, 1)
    H_outputs = []
    dilation = 1
    for w, b in zip(H_weights, H_biases):
        x = tf.nn.relu(conv(x, w, b, filter_length, dilation))
        H_outputs.append(x)
        dilation *= 2

    x_prev = None
    for x, w, b in zip(reversed(H_outputs),
                       reversed(G_weights),
                       reversed(G_biases)):
        if x_prev is not None:
            x = tf.concat(3, [x_prev, x])
        x = tf.nn.relu(conv(x, w, b, filter_length, dilation))
        x_prev = x
        dilation //= 2

    C_weights = init_conv_weights([1, filter_length, n_filters, n_outputs],
                                  random_seed)
    C_biases = init_conv_weights([n_outputs], random_seed)

    y_hat = conv(x, C_weights, C_biases, filter_length, 1)
    # Remove height dimension.
    y_hat = tf.squeeze(y_hat, [1])

    weights = H_weights + G_weights + [C_weights]
    biases = H_biases + G_biases + [C_biases]

    return x_in, y_hat, weights, biases
