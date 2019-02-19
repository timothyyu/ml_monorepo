from keras.engine import Layer
from keras.engine import InputSpec
from keras import initializers
from keras import regularizers
from keras import constraints
from keras import backend as K

from keras.utils.generic_utils import get_custom_objects


class NAC(Layer):
    def __init__(self, units,
                 kernel_W_initializer='glorot_uniform',
                 kernel_M_initializer='glorot_uniform',
                 kernel_W_regularizer=None,
                 kernel_M_regularizer=None,
                 kernel_W_constraint=None,
                 kernel_M_constraint=None,
                 **kwargs):
        """
        Neural Accumulator.

        # Arguments:
            units: Output dimension.
            kernel_W_initializer: Initializer for `W` weights.
            kernel_M_initializer: Initializer for `M` weights.
            kernel_W_regularizer: Regularizer for `W` weights.
            kernel_M_regularizer: Regularizer for `M` weights.
            kernel_W_constraint: Constraints on `W` weights.
            kernel_M_constraint: Constraints on `M` weights.
            epsilon: Small factor to prevent log 0.

        # Reference:
        - [Neural Arithmetic Logic Units](https://arxiv.org/abs/1808.00508)

        """
        super(NAC, self).__init__()
        self.units = units

        self.kernel_W_initializer = initializers.get(kernel_W_initializer)
        self.kernel_M_initializer = initializers.get(kernel_M_initializer)
        self.kernel_W_regularizer = regularizers.get(kernel_W_regularizer)
        self.kernel_M_regularizer = regularizers.get(kernel_M_regularizer)
        self.kernel_W_constraint = constraints.get(kernel_W_constraint)
        self.kernel_M_constraint = constraints.get(kernel_M_constraint)

        self.supports_masking = True

    def build(self, input_shape):
        assert len(input_shape) >= 2
        input_dim = input_shape[-1]

        self.W_hat = self.add_weight(shape=(input_dim, self.units),
                                     name='W_hat',
                                     initializer=self.kernel_W_initializer,
                                     regularizer=self.kernel_W_regularizer,
                                     constraint=self.kernel_W_constraint)

        self.M_hat = self.add_weight(shape=(input_dim, self.units),
                                     name='M_hat',
                                     initializer=self.kernel_M_initializer,
                                     regularizer=self.kernel_M_regularizer,
                                     constraint=self.kernel_M_constraint)

        self.input_spec = InputSpec(min_ndim=2, axes={-1: input_dim})
        self.built = True

    def call(self, inputs, **kwargs):
        W = K.tanh(self.W_hat) * K.sigmoid(self.M_hat)
        a = K.dot(inputs, W)
        return a

    def compute_output_shape(self, input_shape):
        assert input_shape and len(input_shape) >= 2
        assert input_shape[-1]
        output_shape = list(input_shape)
        output_shape[-1] = self.units
        return tuple(output_shape)

    def get_config(self):
        config = {
            'units': self.units,
            'kernel_W_initializer': initializers.serialize(self.kernel_W_initializer),
            'kernel_M_initializer': initializers.serialize(self.kernel_M_initializer),
            'kernel_W_regularizer': regularizers.serialize(self.kernel_W_regularizer),
            'kernel_M_regularizer': regularizers.serialize(self.kernel_M_regularizer),
            'kernel_W_constraint': constraints.serialize(self.kernel_W_constraint),
            'kernel_M_constraint': constraints.serialize(self.kernel_M_constraint),
        }

        base_config = super(NAC, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


get_custom_objects().update({'NAC': NAC})
