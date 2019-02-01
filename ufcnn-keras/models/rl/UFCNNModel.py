
from keras import backend as K
from keras.preprocessing import sequence
from keras.optimizers import SGD, RMSprop, Adagrad
from keras.utils import np_utils
from keras.models import Sequential, Graph, Model
from keras.models import model_from_json

from keras.layers import Input, merge, Flatten, Dense, Activation, Convolution1D, ZeroPadding1D
from keras.layers import TimeDistributed, Reshape
from keras.layers.recurrent import LSTM


class NN_Model(object):

    def __init__(self):
        pass
    def ufcnn_model_concat(self, sequence_length=5000,
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

        #########################################################
        if regression:
            #########################################################

            conv9 = Convolution1D(nb_filter=output_dim, filter_length=filter_length, border_mode='same', init=init)(relu8)
            output = conv9
            #main_output = conv9.output

        else:

            conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='valid', init=init)(relu8)
            activation9 = (Activation(activation))(conv9)
            flat = Flatten () (activation9)
            output = flat
    
        model = Model(input=main_input, output=output)
        model.compile(optimizer=optimizer, loss=loss)

        print(model.summary())
        return model

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
            try:
                model = model_from_json(open(arch_name).read())
            except:
                rmsprop = RMSprop (lr=0.00001, rho=0.9, epsilon=1e-06)  # for sequence length 500
                loss="categorical_crossentropy"
                model = ufcnn_model_concat_shift(regression = False, output_dim=3, features=32, loss=loss, sequence_length=499, optimizer=rmsprop)

        model.load_weights(weight_name)
        return model

