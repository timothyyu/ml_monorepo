from keras.engine import Layer
from keras.engine import InputSpec
from keras import initializers
from keras import regularizers
from keras import constraints
from keras import backend as K

from keras.utils.generic_utils import get_custom_objects


class NALU(Layer):
    def __init__(self, units,
                 use_gating=True,
                 kernel_W_initializer='glorot_uniform',
                 kernel_M_initializer='glorot_uniform',
                 gate_initializer='glorot_uniform',
                 kernel_W_regularizer=None,
                 kernel_M_regularizer=None,
                 gate_regularizer=None,
                 kernel_W_constraint=None,
                 kernel_M_constraint=None,
                 gate_constraint=None,
                 epsilon=1e-7,
                 **kwargs):
        """
        Neural Arithmatic and Logical Unit.

        # Arguments:
            units: Output dimension.
            use_gating: Bool, determines whether to use the gating
                mechanism between W and m.
            kernel_W_initializer: Initializer for `W` weights.
            kernel_M_initializer: Initializer for `M` weights.
            gate_initializer: Initializer for gate `G` weights.
            kernel_W_regularizer: Regularizer for `W` weights.
            kernel_M_regularizer: Regularizer for `M` weights.
            gate_regularizer: Regularizer for gate `G` weights.
            kernel_W_constraint: Constraints on `W` weights.
            kernel_M_constraint: Constraints on `M` weights.
            gate_constraint: Constraints on gate `G` weights.
            epsilon: Small factor to prevent log 0.

        # Reference:
        - [Neural Arithmetic Logic Units](https://arxiv.org/abs/1808.00508)

        """
        super(NALU, self).__init__()
        self.units = units
        self.use_gating = use_gating
        self.epsilon = epsilon

        self.kernel_W_initializer = initializers.get(kernel_W_initializer)
        self.kernel_M_initializer = initializers.get(kernel_M_initializer)
        self.gate_initializer = initializers.get(gate_initializer)
        self.kernel_W_regularizer = regularizers.get(kernel_W_regularizer)
        self.kernel_M_regularizer = regularizers.get(kernel_M_regularizer)
        self.gate_regularizer = regularizers.get(gate_regularizer)
        self.kernel_W_constraint = constraints.get(kernel_W_constraint)
        self.kernel_M_constraint = constraints.get(kernel_M_constraint)
        self.gate_constraint = constraints.get(gate_constraint)

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

        if self.use_gating:
            self.G = self.add_weight(shape=(input_dim, self.units),
                                     name='G',
                                     initializer=self.gate_initializer,
                                     regularizer=self.gate_regularizer,
                                     constraint=self.gate_constraint)
        else:
            self.G = None

        self.input_spec = InputSpec(min_ndim=2, axes={-1: input_dim})
        self.built = True

    def call(self, inputs, **kwargs):
        W = K.tanh(self.W_hat) * K.sigmoid(self.M_hat)
        m = K.exp(K.dot(K.log(K.abs(inputs) + self.epsilon), W))
        a = K.dot(inputs, W)

        if self.use_gating:
            g = K.sigmoid(K.dot(inputs, self.G))
            outputs = g * a + (1. - g) * m
        else:
            outputs = a + m

        return outputs

    def compute_output_shape(self, input_shape):
        assert input_shape and len(input_shape) >= 2
        assert input_shape[-1]
        output_shape = list(input_shape)
        output_shape[-1] = self.units
        return tuple(output_shape)

    def get_config(self):
        config = {
            'units': self.units,
            'use_gating': self.use_gating,
            'kernel_W_initializer': initializers.serialize(self.kernel_W_initializer),
            'kernel_M_initializer': initializers.serialize(self.kernel_M_initializer),
            'gate_initializer': initializers.serialize(self.gate_initializer),
            'kernel_W_regularizer': regularizers.serialize(self.kernel_W_regularizer),
            'kernel_M_regularizer': regularizers.serialize(self.kernel_M_regularizer),
            'gate_regularizer': regularizers.serialize(self.gate_regularizer),
            'kernel_W_constraint': constraints.serialize(self.kernel_W_constraint),
            'kernel_M_constraint': constraints.serialize(self.kernel_M_constraint),
            'gate_constraint': constraints.serialize(self.gate_constraint),
            'epsilon': self.epsilon
        }

        base_config = super(NALU, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


get_custom_objects().update({'NALU': NALU})
