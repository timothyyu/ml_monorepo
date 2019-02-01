import os
import sys

from keras import backend as K
from keras.preprocessing import sequence
from keras.optimizers import SGD, RMSprop, Adagrad
from keras.utils import np_utils
from keras.models import Sequential, Graph, Model
from keras.models import model_from_json

from keras.layers import Input, merge, Flatten, Dense, Activation, Convolution1D, ZeroPadding1D
from keras.layers import TimeDistributed, Reshape
from keras.layers.recurrent import LSTM

from keras.engine import training 


class Models(object):

    def __init__(self):
        pass

    def save_model (self, model, model_name):
        locpath="./"
        json_string = model.to_json()
        open(locpath + model_name + '_architecture.json', 'w').write(json_string)
        model.save_weights(locpath + model_name + '_weights.h5', overwrite=True)

        yaml_string = model.to_yaml()
        with open(locpath + model_name + '_data.yml', 'w') as outfile:
            outfile.write( yaml_string)

    def load_model(self, model_name):
        """ 
        reading the model from disk - including all the trained weights and the complete model design (hyperparams, planes,..)
        """
    
        locpath="./"
        arch_name = locpath + model_name + '_architecture.json'
        weight_name = locpath + model_name + '_weights.h5'
    
        if not os.path.isfile(arch_name) or not os.path.isfile(weight_name):
            print("model_name given and file %s and/or %s not existing. Aborting." % (arch_name, weight_name))
            sys.exit()

        print("Loaded model: ",model_name)

        try:
            model = model_from_json(open(arch_name).read(),{'Convolution1D_Transpose_Arbitrary':Convolution1D_Transpose_Arbitrary})
        except NameError:
            model = model_from_json(open(arch_name).read())

        model.load_weights(weight_name)
        self.model = model
        return model


    def model_ufcnn_concat(self, sequence_length=5000,
                       features=1,
                       nb_filter=150,
                       filter_length=5,
                       output_dim=1,
                       optimizer='adagrad',
                       loss='mse',
                       batch_size = 512,
                       regression = True,
                       class_mode=None,
                       activation="softplus",
                       init="lecun_uniform"):

        main_input = Input(name='input', shape=(sequence_length, features))

        #########################################################

        #input_padding = ZeroPadding1D(2)(main_input)  # to avoid lookahead bias

        #########################################################

        conv1 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(main_input)
        relu1 = Activation(activation)(conv1)

        #########################################################

        conv2 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(relu1)
        relu2 = Activation(activation)(conv2)

        #########################################################

        conv3 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(relu2)
        relu3 = Activation(activation)(conv3)

        #########################################################

        conv4 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(relu3)
        relu4 = Activation(activation)(conv4)

        #########################################################

        conv5 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(relu4)
        relu5 = Activation(activation)(conv5)

        #########################################################

        merge6 = merge([relu3, relu5], mode='concat')
        conv6 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(merge6)
        relu6 = Activation(activation)(conv6)

        #########################################################

        merge7 = merge([relu2, relu6], mode='concat')
        conv7 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(merge7)
        relu7 = Activation(activation)(conv7)

        #########################################################

        merge8 = merge([relu1, relu7], mode='concat')
        conv8 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init)(merge8)
        relu8 = Activation(activation)(conv8)

        conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='valid', init=init)(relu8)
        activation9 = (Activation(activation))(conv9)
        flat = Flatten () (activation9)
        # activation in the last layer should be linear... and a one dimensional array.....
        dense = Dense(output_dim)(flat)
        output = dense
    
        model = Model(input=main_input, output=output)
        model.compile(optimizer=optimizer, loss=loss)

        print(model.summary())

        self.model = model
        return model

    def atari_conv_model(self, sequence_length=5000,
                       features=1,
                       output_dim=1,
                       optimizer='adagrad',
                       activation='softplus',
                       loss='mse',
                       batch_size = 512,
                       init="lecun_uniform"):
        """
        After the ConvModel in Deep Mind RL paper: Mnih, V., et al. "Asynchronous Methods for Deep Reinforcement Learning"
        """

        main_input = Input(name='input', shape=(sequence_length, features))

        #########################################################

        #input_padding = ZeroPadding1D(2)(main_input)  # to avoid lookahead bias

        #########################################################

        conv1 = Convolution1D(nb_filter=16, filter_length=8, border_mode='valid', init=init, subsample_length=4)(main_input)
        relu1 = Activation(activation)(conv1)

        #########################################################

        conv2 = Convolution1D(nb_filter=32, filter_length=4, border_mode='valid', subsample_length=2, init=init)(relu1)
        relu2 = Activation(activation)(conv2)

        #########################################################

        flat = Flatten () (relu2)
        dense1 = Dense(256)(flat)
        relu3 = Activation(activation)(dense1)

        # activation in the last layer should be linear... and a one dimensional array.....
        dense2 = Dense(output_dim)(relu3)
        output = dense2
    
        model = Model(input=main_input, output=output)
        model.compile(optimizer=optimizer, loss=loss)

        print(model.summary())
        self.model = model
        return model


    def XXXget_layer_weights(self):
        """
        get the layers of the current model...
        """
        result = {} 
        jlayer=0
        for layer in self.model.layers:
            symbolic_weights = layer.trainable_weights + layer.non_trainable_weights
            weight_values = K.batch_get_value(symbolic_weights)
            layer_list=[]
            for i, (w, val) in enumerate(zip(symbolic_weights, weight_values)):
                layer_list.append(val)
            print("ADDING W",jlayer)
            result[jlayer] = layer_list
            jlayer += 1
        return result 


    def XXXset_layer_weights(self, input_weights):
        """
        set the weights of the current model to the input weights...
        """
        #for name, val in results:
        jlayer=0
        weight_value_tuples = []
        for layer in self.model.layers:
            weight_values = input_weights[jlayer]
            jlayer += 1
            symbolic_weights = layer.trainable_weights + layer.non_trainable_weights
            weight_value_tuples += zip(symbolic_weights, weight_values)

        K.batch_set_value(weight_value_tuples)

    def XXXget_gradients_numeric(self, x, y, updates=[]):
        cost_s, grads_s = self.get_cost_grads_symbolic()
        #sample_weights missing...

        #inputs = x + y + self.sample_weights + [1.]
        ## x and y must come from Keras ans are placeholdes
        inputs = [x] + [y] + [] + [1.]
        train_function = K.function(inputs,
                                    [grads_s],
                                     updates=updates)


        f = train_function
        outs = f(inputs)
        print (outs)


     
    def XXXget_cost_grads_symbolic(self):
        """ Returns symbolic cost and symbolic gradients for the model """
        trainable_params = self._get_trainable_params(self.model)

        #cost = self.model.model.total_loss
        cost = self.model.total_loss
        grads = K.gradients(cost, trainable_params)

        return cost, grads


    def XXX_get_trainable_params(self, model):
        params = []
        for layer in model.layers:
            params += training.collect_trainable_weights(layer)
        return params

    def XXXget_training_function(self, x,y):
        # get trainable weights
        trainable_weights = []
        for layer in self.model.layers:
            trainable_weights += collect_trainable_weights(layer)

        # get the grads - more or less
        weights = [K.variable(np.zeros(K.get_value(p).shape)) for p in trainable_weights]
        training_updates = self.optimizer.get_updates(trainable_weights, self.constraints, self.total_loss)


    def pack_theta(self, trainable_weights):
        """ Flattens a set of shared variables (trainable_weights)"""
        x = np.empty(0)
        for t in trainable_weights:
            x = np.concatenate((x, K.get_value(t).reshape(-1)))
        return x


    def unpack_theta(self, theta):
        """ Converts flattened theta back to tensor shapes of Keras model params """
        weights = []
        idx = 0
        model = self.model
        for layer in model.layers:
            layer_weights = []
            for param in layer.get_weights():
                plen = np.prod(param.shape)
                layer_weights.append(
                    np.asarray(
                        theta[
                            idx:(
                                idx +
                                plen)].reshape(
                            param.shape),
                        dtype=np.float32))
                idx += plen
            weights.append(layer_weights)
        return weights


    def set_model_params(self, theta):
        """ Sets the Keras model params from a flattened numpy array of theta """
        model = self.model
        trainable_params = self.unpack_theta(theta)
        for trainable_param, layer in zip(trainable_params, model.layers):
            layer.set_weights(trainable_param)


    def get_cost_grads(self):
        """ Returns the cost and flattened gradients for the model """
        model = self.model
        trainable_params = self.get_trainable_params()

        #cost = model.model.total_loss
        cost = model.total_loss
        grads = K.gradients(cost, trainable_params)

        return cost, grads


    def flatten_grads(self, grads):
        """ Flattens a set tensor variables (gradients) """
        x = np.empty(0)
        for g in grads:
            x = np.concatenate((x, g.reshape(-1)))
        return x


    def get_trainable_params(self):
        model = self.model
        trainable_weights = []
        for layer in model.layers:
            trainable_weights += keras.engine.training.collect_trainable_weights(
                layer)
        return trainable_weights


    def get_training_function(self, x, y):
        model = self.model
        cost, grads = self.get_cost_grads()
        outs = [cost]
        if type(grads) in {list, tuple}:
            outs += grads
        else:
            outs.append(grads)

        fn = K.function(
            inputs=[],
            outputs=outs,
            givens={
                model.inputs[0]: x,
                model.targets[0]: y,
                model.sample_weights[0]: np.ones(
                    (x.shape[0],
                     ),
                    dtype=np.float32),
                K.learning_phase(): np.uint8(1)})

        def train_fn(theta):
            self.set_model_params(theta)
            cost_grads = fn([])
            cost = np.asarray(cost_grads[0], dtype=np.float64)
            grads = np.asarray(self.flatten_grads(cost_grads[1:]), dtype=np.float64)

            return cost, grads

        return train_fn


    def fit_scipy(self, model, x, y, nb_epoch=300, method='L-BFGS-B', **kwargs):
        trainable_params = self.get_trainable_params()
        theta0 = self.pack_theta(trainable_params)
   

        train_fn = self.get_training_function(x, y)
        print("BEFORE")
        print(train_fn)
        print(theta0)

        weights = sp.optimize.minimize(
            train_fn, theta0, method=method, jac=True, options={
                'maxiter': nb_epoch, 'disp': False}, **kwargs)
        print("AFTER")
        trainable_params = self.get_trainable_params()
        theta0 = self.pack_theta(trainable_params)
        print(theta0)

        theta_final = weights.x
        print (weights.x)
        self.set_model_params(theta_final)

    def fit_sgd(self, x, y, nb_epoch=10):
        alfa = 0.9 # ... Momentum
        lr = 0.1 # -... learning rate

        trainable_params = self.get_trainable_params()
        theta0 = self.pack_theta(trainable_params)
        train_fn = self.get_training_function(x, y)

        m = np.zeros_like(theta0)
        for i in range(nb_epoch):
            trainable_params = self.get_trainable_params()
            theta0 = self.pack_theta(trainable_params)

            #mi = αmi + (1 − α)∆θi
            m = alfa * m + (1-alfa)*theta0

            # θ ← θ − ηmi
            theta0 = theta0 - lr*m
            self.set_model_params(theta0)
            
            
    """
if __name__ == "__main__":
    sequence_length = 1000
    features = 32
    output_dim = 3
    batch_size = 32


    mo = Models()
    model = mo.atari_conv_model(sequence_length=sequence_length, features=features, output_dim=output_dim, batch_size=32)


    x = np.random.rand(batch_size, sequence_length, features).astype(np.float32)
    y = np.random.rand(batch_size, output_dim).astype(np.float32)

    x_eval = x[0].copy().reshape((1,sequence_length, features))
    y_eval = y[0].copy().reshape((1,output_dim))

    print("Loss before ", model.evaluate(x_eval,y_eval))


    #mo.fit_scipy(model, x, y, nb_epoch=10, method='L-BFGS-B')
    mo.fit_sgd(x, y, nb_epoch=1000)

    print("Loss after  ", model.evaluate(x_eval,y_eval))
    """
