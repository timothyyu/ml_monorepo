import numpy as np
import keras.backend as K
from keras.layers import *
from keras.initializers import *
from keras.models import *

class NALU(Layer):
    def __init__(self, units, MW_initializer='glorot_uniform',
                 G_initializer='glorot_uniform', mode="NALU",
                 **kwargs):
        if 'input_shape' not in kwargs and 'input_dim' in kwargs:
            kwargs['input_shape'] = (kwargs.pop('input_dim'),)
        super(NALU, self).__init__(**kwargs)
        self.units = units
        self.mode = mode
        self.MW_initializer = initializers.get(MW_initializer)
        self.G_initializer = initializers.get(G_initializer)
        self.input_spec = InputSpec(min_ndim=2)
        self.supports_masking = True

    def build(self, input_shape):
        assert len(input_shape) >= 2
        input_dim = input_shape[-1]

        self.W_hat = self.add_weight(shape=(input_dim, self.units),
                                     initializer=self.MW_initializer,
                                     name='W_hat')
        self.M_hat = self.add_weight(shape=(input_dim, self.units),
                                     initializer=self.MW_initializer,
                                     name='M_hat')
        if self.mode == "NALU":
            self.G = self.add_weight(shape=(input_dim, self.units),
                                     initializer=self.G_initializer,
                                     name='G')
        self.input_spec = InputSpec(min_ndim=2, axes={-1: input_dim})
        self.built = True

    def call(self, inputs):
        W = K.tanh(self.W_hat) * K.sigmoid(self.M_hat)
        a = K.dot(inputs, W)
        if self.mode == "NAC":
            output = a
        elif self.mode == "NALU":
            m = K.exp(K.dot(K.log(K.abs(inputs) + 1e-7), W))
            g = K.sigmoid(K.dot(K.abs(inputs), self.G))
            output = g * a + (1 - g) * m
        else:
            raise ValueError("Valid modes: 'NAC', 'NALU'.")
        return output

    def compute_output_shape(self, input_shape):
        assert input_shape and len(input_shape) >= 2
        assert input_shape[-1]
        output_shape = list(input_shape)
        output_shape[-1] = self.units
        return tuple(output_shape)

    def get_config(self):
        config = {
            'units': self.units,
            'mode' : self.mode,
            'MW_initializer': initializers.serialize(self.MW_initializer),
            'G_initializer':  initializers.serialize(self.G_initializer)
        }
        base_config = super(Dense, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

def nalu_model(mode=NALU):
    x = Input((100,))
    y = NALU(2, mode=mode, 
             MW_initializer=RandomNormal(stddev=1),
             G_initializer=Constant(10))(x)
    y = NALU(1, mode=mode, 
             MW_initializer=RandomNormal(stddev=1),
             G_initializer=Constant(10))(y)
    return Model(x, y)

def mlp_model():
    x = Input((100,))
    y = Dense(2, activation="relu")(x)
    y = Dense(1)(y)
    return Model(x, y)

def get_data(N, op):
    split = 45
    trX = np.random.normal(0, 0.5, (N, 100))
    a = trX[:, :split].sum(1)
    b = trX[:, split:].sum(1)
    print(a.min(), a.max(), b.min(), b.max())
    trY = op(a, b)[:, None]
    teX = np.random.normal(0, 2, (N, 100))
    a = teX[:, :split].sum(1)
    b = teX[:, split:].sum(1)
    print(a.min(), a.max(), b.min(), b.max())
    teY = op(a, b)[:, None]
    return (trX, trY), (teX, teY)

if __name__ == "__main__":
    m = nalu_model("NALU")
    m.compile("rmsprop", "mse", metrics=["mae"])
    (trX, trY), (teX, teY) = get_data(2 ** 16, lambda a, b: a - b)
    K.set_value(m.optimizer.lr, 1e-2)
    m.fit(trX, trY, validation_data=(teX, teY), batch_size=1024, epochs=200)
    K.set_value(m.optimizer.lr, 1e-3)
    m.fit(trX, trY, validation_data=(teX, teY), batch_size=1024, epochs=200)
    K.set_value(m.optimizer.lr, 1e-4)
    m.fit(trX, trY, validation_data=(teX, teY), batch_size=1024, epochs=200)
