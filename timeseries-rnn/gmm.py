# Layer implementing a Gaussian mixture model.
# Implementation largely follows https://github.com/fchollet/keras/issues/1061.
# In contrast to the original code, the loss was divided by sqrt(2 pi) to use the same Gaussian as in numpy.random.norm 

from keras.layers import Layer
# TODO: This is only implemented for theano, rewrite it using keras.backend (as an exercise).
import theano
import theano.tensor as T
import numpy as np

class GMMActivation(Layer):
    """
    GMM-like activation function.
    Assumes that input has (D+2)*M dimensions, where D is the dimensionality of the 
    target data. The first M*D features are treated as means, the next M features as 
    standard devs and the last M features as mixture components of the GMM. 
    """
    def __init__(self, M, **kwargs):
        super(GMMActivation, self).__init__(**kwargs)
        self.M = M

    def get_output(self, train=False):
        X = self.get_input(train)
        D = T.shape(X)[1]/self.M - 2
        # leave mu values as they are since they're unconstrained
        # scale sigmas with exp, s.t. all values are non-negative 
        X = T.set_subtensor(X[:,D*self.M:(D+1)*self.M], T.exp(X[:,D*self.M:(D+1)*self.M]))
        # scale alphas with softmax, s.t. that all values are between [0,1] and sum up to 1
        X = T.set_subtensor(X[:,(D+1)*self.M:(D+2)*self.M], T.nnet.softmax(X[:,(D+1)*self.M:(D+2)*self.M]))
        return X

    def get_config(self):
        config = {"name": self.__class__.__name__,
                  "M": self.M}
        base_config = super(GMMActivation, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

def gmm_loss(y_true, y_pred):
    """
    GMM loss function.
    Assumes that y_pred has (D+2)*M dimensions and y_true has D dimensions. The first 
    M*D features are treated as means, the next M features as standard devs and the last 
    M features as mixture components of the GMM. 
    """
    def loss(m, M, D, y_true, y_pred):
        mu = y_pred[:,D*m:(m+1)*D]
        sigma = y_pred[:,D*M+m]
        alpha = y_pred[:,(D+1)*M+m]
        return (alpha/sigma/np.sqrt(2. * np.pi)) * T.exp(-T.sum(T.sqr(mu-y_true),-1)/(2*sigma**2))

    D = T.shape(y_true)[1]
    M = T.shape(y_pred)[1]/(D+2)
    seq = T.arange(M)
    result, _ = theano.scan(fn=loss, outputs_info=None, 
    sequences=seq, non_sequences=[M, D, y_true, y_pred])
    return -T.log(result.sum(0))