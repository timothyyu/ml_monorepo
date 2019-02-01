from __future__ import absolute_import
from __future__ import print_function
import sys
import glob

import time
import numpy as np
import pandas as pd
import os.path
import time
import datetime
import re

from keras.preprocessing import sequence
from keras.optimizers import SGD, RMSprop, Adagrad
from keras.utils import np_utils
from keras.models import Sequential, Graph, Model
from keras.models import model_from_json

from keras.layers import Input, merge, Flatten, Dense, Activation, Convolution1D, ZeroPadding1D

#from keras.layers.core import Dense, Dropout, Activation, TimeDistributedDense, Flatten, Reshape, Permute, Merge, Lambda
#from keras.layers.convolutional import Convolution1D, MaxPooling1D, Convolution2D, MaxPooling2D, UpSampling1D, UpSampling2D, ZeroPadding1D
from keras.layers.advanced_activations import ParametricSoftplus, SReLU
from keras.callbacks import ModelCheckpoint, Callback
import matplotlib.pyplot as plt

path = "./training_data_large/"  # to make sure signal files are written in same directory as data files

def draw_model(model):
    from IPython.display import SVG
    from keras.utils.visualize_util import model_to_dot
    from keras.utils.visualize_util import plot

    #graph = to_graph(model, show_shape=True)
    #graph.write_png("UFCNN_1.png")

    SVG(model_to_dot(model).create(prog='dot', format='svg'))
    plot(model, to_file='UFCNN_1.png')


def print_nodes_shapes(model):
    for k, v in model.inputs.items():
        print("{} : {} : {} : {}".format(k, type(v), v.input_shape, v.output_shape))
        
    for k, v in model.nodes.items():
        print("{} : {} : {} : {}".format(k, type(v), v.input_shape, v.output_shape))
        
    for k, v in model.outputs.items():
        print("{} : {} : {} : {}".format(k, type(v), v.input_shape, v.output_shape))
        
        
def print_layers_shapes(model):
    for l in model.layers:
        print("{} : {} : {}".format(type(l), l.input_shape, l.output_shape))
        

def save_neuralnet (model, model_name):

    json_string = model.to_json()
    open(path + model_name + '_architecture.json', 'w').write(json_string)
    model.save_weights(path + model_name + '_weights.h5', overwrite=True)

    yaml_string = model.to_yaml()
    with open(path + model_name + '_data.yml', 'w') as outfile:
        outfile.write( yaml_string)

def load_neuralnet(model_name):
    """ 
    reading the model from disk - including all the trained weights and the complete model design (hyperparams, planes,..)
    """

    arch_name = path + model_name + '_architecture.json'
    weight_name = path + model_name + '_weights.h5'

    if not os.path.isfile(arch_name) or not os.path.isfile(weight_name):
        print("model_name given and file %s and/or %s not existing. Aborting." % (arch_name, weight_name))
        sys.exit()

    print("Loaded model: ",model_name)

    model = model_from_json(open(arch_name).read())
    model.load_weights(weight_name)
    return model


def ufcnn_model_concat(sequence_length=5000,
                       features=1,
                       nb_filter=150,
                       filter_length=5,
                       output_dim=1,
                       optimizer='adagrad',
                       loss='mse',
                       regression = True,
                       class_mode=None,
                       activation="softplus",
                       init="lecun_uniform"):
    #model = Graph()
   
    #model.add_input(name='input', input_shape=(None, features))

    main_input = Input(name='input', shape=(None, features))

    #########################################################

    #model.add_node(ZeroPadding1D(2), name='input_padding', input='input') # to avoid lookahead bias

    input_padding = (ZeroPadding1D(2))(main_input)  # to avoid lookahead bias

    #########################################################

    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='valid', init=init, input_shape=(sequence_length, features)), name='conv1', input='input_padding')
    #model.add_node(Activation(activation), name='relu1', input='conv1')

    conv1 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='valid', init=init, input_shape=(sequence_length, features))(input_padding)
    relu1 = (Activation(activation))(conv1)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv2', input='relu1')
    #model.add_node(Activation(activation), name='relu2', input='conv2')

    conv2 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu1)
    relu2 = (Activation(activation))(conv2)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv3', input='relu2')
    #model.add_node(Activation(activation), name='relu3', input='conv3')


    conv3 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu2)
    relu3 = (Activation(activation))(conv3)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv4', input='relu3')
    #model.add_node(Activation(activation), name='relu4', input='conv4')

    conv4 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu3)
    relu4 = (Activation(activation))(conv4)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv5', input='relu4')
    #model.add_node(Activation(activation), name='relu5', input='conv5')

    conv5 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu4)
    relu5 = (Activation(activation))(conv5)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv6',
    #                 inputs=['relu3', 'relu5'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu6', input='conv6')


    conv6 = merge([relu3, relu5], mode='concat', concat_axis=1)
    relu6 = (Activation(activation))(conv6)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv7',
    #                 inputs=['relu2', 'relu6'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu7', input='conv7')

    conv7 = merge([relu2, relu6], mode='concat', concat_axis=1)
    relu7 = (Activation(activation))(conv7)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv8',
    #                 inputs=['relu1', 'relu7'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu8', input='conv8')

    conv8 = merge([relu1, relu7], mode='concat', concat_axis=1)
    relu8 = (Activation(activation))(conv8)

    #########################################################
    if regression:
        #########################################################
        #model.add_node(Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init), name='conv9', input='relu8')
        #model.add_output(name='output', input='conv9')


        conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init)(relu8)
        output = conv9
        #main_output = conv9.output

    else:
        #model.add_node(Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init), name='conv9', input='relu8')
        #model.add_node(Activation('softmax'), name='activation', input='conv9')
        #model.add_output(name='output', input='activation')

        conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init)(relu8)
        activation = (Activation('softmax'))(conv9)
        #main_output = activation.output
        output = activation
    
    #model.compile(optimizer=optimizer, loss={'output': loss})

    model = Model(input=main_input, output=output)
    model.compile(optimizer=optimizer, loss=loss)
    
    return model


def ufcnn_model_deconv(sequence_length=5000,
                       features=4,
                       nb_filter=150,
                       filter_length=5,
                       output_dim=1,
                       optimizer='adagrad',
                       loss='mse',
                       regression = False,
                       class_mode=None,
                       activation="softplus",
                       init="lecun_uniform"):
    #model = Graph()

    #model.add_input(name='input', input_shape=(None, features))

    main_input = Input(name='input', shape=(None, features))

    #########################################################

    #model.add_node(ZeroPadding1D(2), name='input_padding', input='input') # to avoid lookahead bias

    input_padding = (ZeroPadding1D(2))(main_input)  # to avoid lookahead bias

    #########################################################

    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='valid', init=init, input_shape=(sequence_length, features)), name='conv1', input='input_padding')
    #model.add_node(Activation(activation), name='relu1', input='conv1')

    conv1 = Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='valid', init=init, input_shape=(sequence_length, features))(input_padding)
    relu1 = (Activation(activation))(conv1)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv2', input='relu1')
    #model.add_node(Activation(activation), name='relu2', input='conv2')

    conv2 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu1)
    relu2 = (Activation(activation))(conv2)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv3', input='relu2')
    #model.add_node(Activation(activation), name='relu3', input='conv3')


    conv3 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu2)
    relu3 = (Activation(activation))(conv3)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv4', input='relu3')
    #model.add_node(Activation(activation), name='relu4', input='conv4')

    conv4 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu3)
    relu4 = (Activation(activation))(conv4)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init), name='conv5', input='relu4')
    #model.add_node(Activation(activation), name='relu5', input='conv5')

    conv5 = (Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='same', init=init))(relu4)
    relu5 = (Activation(activation))(conv5)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv6',
    #                 inputs=['relu3', 'relu5'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu6', input='conv6')


    conv6 = merge([relu3, relu5], mode='concat', concat_axis=1)
    relu6 = (Activation(activation))(conv6)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv7',
    #                 inputs=['relu2', 'relu6'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu7', input='conv7')

    conv7 = merge([relu2, relu6], mode='concat', concat_axis=1)
    relu7 = (Activation(activation))(conv7)

    #########################################################
    #model.add_node(Convolution1D(nb_filter=nb_filter,filter_length=filter_length, border_mode='same', init=init),
    #                 name='conv8',
    #                 inputs=['relu1', 'relu7'],
    #                 merge_mode='concat', concat_axis=-1)
    #model.add_node(Activation(activation), name='relu8', input='conv8')

    conv8 = merge([relu1, relu7], mode='concat', concat_axis=1)
    relu8 = (Activation(activation))(conv8)

    #########################################################
    if regression:
        #########################################################
        #model.add_node(Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init), name='conv9', input='relu8')
        #model.add_output(name='output', input='conv9')


        conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init)(relu8)
        output = conv9
        #main_output = conv9.output

    else:
        #model.add_node(Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init), name='conv9', input='relu8')
        #model.add_node(Activation('softmax'), name='activation', input='conv9')
        #model.add_output(name='output', input='activation')

        conv9 = Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init)(relu8)
        activation = (Activation('softmax'))(conv9)
        #main_output = activation.output
        output = activation

    #model.compile(optimizer=optimizer, loss={'output': loss})

    model = Model(input=main_input, output=output)
    model.compile(optimizer=optimizer, loss=loss)

    return model


def ufcnn_model_seq(sequence_length=5000,
                           features=1,
                           nb_filter=150,
                           filter_length=5,
                           output_dim=1,
                           optimizer='adagrad',
                           loss='mse',
                           regression = True,
                           class_mode=None,
                           init="lecun_uniform"):
    

    model = Sequential()
    model.add(ZeroPadding1D(2, input_shape=(None, features)))
    #########################################################
    model.add(Convolution1D(nb_filter=nb_filter, filter_length=filter_length, border_mode='valid', init=init))
    model.add(Activation('relu'))
    model.add(Convolution1D(nb_filter=output_dim, filter_length=sequence_length, border_mode='same', init=init))
    model.add(Activation('sigmoid'))
    
    model.compile(optimizer=optimizer, loss=loss)
    
    return model


def ufcnn_model(sequence_length=5000,
                           features=1,
                           nb_filter=150,
                           filter_length=5,
                           output_dim=1,
                           optimizer='adagrad',
                           loss='mse',
                           regression = True,
                           class_mode=None,
                           init="lecun_uniform",
                           mode='concat'):
    if mode == 'concat':
        return ufcnn_model_concat(sequence_length,
                           features,
                           nb_filter,
                           filter_length,
                           output_dim,
                           optimizer,
                           loss,
                           regression,
                           class_mode,
                           init)
    else:
        raise NotImplemented


def gen_cosine_amp(amp=100, period=25, x0=0, xn=50000, step=1, k=0.0001):
    """Generates an absolute cosine time series with the amplitude
    exponentially decreasing
    Arguments:
        amp: amplitude of the cosine function
        period: period of the cosine function
        x0: initial x of the time series
        xn: final x of the time series
        step: step of the time series discretization
        k: exponential rate
	Ernst 20160301 from https://github.com/fchollet/keras/blob/master/examples/stateful_lstm.py
        as a first test for the ufcnn
    """
    
    cos = np.zeros(((xn - x0) * step,  1, 1))
    print("Cos. Shape",cos.shape)
    for i in range(len(cos)):
        idx = x0 + i * step
        cos[i, 0, 0] = amp * np.cos(idx / (2 * np.pi * period))
        cos[i, 0, 0] = cos[i, 0, 0] * np.exp(-k * idx)
    return cos


def train_and_predict_regression(model, sequence_length=5000, batch_size=128, epochs=5):
    lahead = 1

    cos = gen_cosine_amp(xn = sequence_length * 100)

    expected_output = np.zeros((len(cos), 1, 1))

    for i in range(len(cos) - lahead):
        expected_output[i, 0] = np.mean(cos[i + 1:i + lahead + 1])

    print('Training')
    for i in range(epochs):
        print('Epoch', i, '/', epochs)
        model.fit({'input': cos, 'output': expected_output},
                  verbose=1,
                  nb_epoch=1,
                  shuffle=False,
                  batch_size=batch_size)

    print('Predicting')
    predicted_output = model.predict({'input': cos,}, batch_size=batch_size)
    
    return {'model': model, 'predicted_output': predicted_output, 'expected_output': expected_output}


def treat_X_tradcom(mean):
    """ treat some columns of the dataframe together when normalizing the dataframe:
        col. 1, 2, 4 ... Mkt Price, Bid price, Ask Price
        col 3 and 5 ... Ask & Bid price
    """ 

    result = mean.copy()
    #print("Result before max",result)

    mkt = mean[1]
    bid_px = mean[2]
    ask_px = mean[4]
    px_max=max(mkt,bid_px,ask_px)

    result[1] = px_max
    result[2] = px_max
    result[4] = px_max


    bid = mean[3]
    ask = mean[5]
    ba_max=max(bid,ask)

    result[3] = ba_max
    result[5] = ba_max

    print("Result after max",result)
   
    return result


def standardize_inputs(source, colgroups=None, mean=None, std=None):
    """
    Standardize input features.
    Groups of features could be listed in order to be standardized together.
    source: Pandas.DataFrame or filename of csv file with features
    colgroups: list of lists of groups of features to be standardized together (e.g. bid/ask price, bid/ask size)
    returns Xdf ...Pandas.DataFrame, mean ...Pandas.DataFrame, std ...Pandas.DataFrame
    """
    import itertools
    import types
    
    #if isinstance(source, types.StringTypes):
    if isinstance(source, str):
        Xdf = pd.read_csv(source, sep=" ", index_col = 0, header = None)
    elif isinstance(source, pd.DataFrame):
        Xdf = source
    else:
        raise TypeError
    
    df = pd.DataFrame()
    me = pd.DataFrame()
    st = pd.DataFrame()

    for colgroup in colgroups:
        _df,_me,_st = standardize_columns(Xdf[colgroup])
        # if mean & std are given, do not multiply with colgroup mean
        if mean is not None and std is not None:  
            _df = Xdf[colgroup]

        df = pd.concat([df, _df], axis=1)
        me = pd.concat([me, _me])
        st = pd.concat([st, _st])

        print("In Group me")
        print(me)
        
    #     _temp_list = list(itertools.chain.from_iterable(colgroups))
    separate_features = [col for col in Xdf.columns if col not in list(itertools.chain.from_iterable(colgroups))]
    if mean is None and std is None:
        _me = Xdf[separate_features].mean()
        _df = Xdf[separate_features].sub(_me)
        _st = Xdf[separate_features].std()
        _df = _df[separate_features].div(_st)
    else:
        _df = Xdf[separate_features]
       
    
    df = pd.concat([df, _df], axis=1)
    me = pd.concat([me, _me])
    st = pd.concat([st, _st])

    me = pd.Series(me[0])
    st = pd.Series(st[0])

    if mean is not None and std is not None:
     
        df = df.sub(mean)
        df = df.div(std)

    return df, me, st

    
def standardize_columns(colgroup):
    """
    Standardize group of columns together
    colgroup: Pandas.DataFrame
    returns: Pandas.DataFrames: Colum Group standardized, Mean of the colgroup, stddeviation of the colgroup
    """
    _me = np.mean(colgroup.values.flatten())
    centered = colgroup.sub(_me)
    me = pd.DataFrame(np.full(len(colgroup.columns),_me), index=colgroup.columns)

    _st = np.std(colgroup.values.flatten())
    standardized = centered.div(_st)
    st = pd.DataFrame(np.full(len(colgroup.columns),_st), index=colgroup.columns)
    
    return standardized, me, st
    
        
def get_tradcom_normalization(filename, mean=None, std=None):
    """  read in all X Data Frames and find mean and std of all columns...
    """
    Xdf = pd.read_csv(filename, sep=" ", index_col = 0, header = None)
    meanLoc = treat_X_tradcom(Xdf.mean())
    print("Mean Loc")
    print (meanLoc)
    sys.stdout.flush()

    if mean is None:
        mean = meanLoc

    mean = mean.to_frame().transpose()
    meanDf=pd.concat([mean, meanLoc.to_frame().transpose()])
    mean = meanDf.max()

    print("Mean")
    print (mean)
    sys.stdout.flush()

    stdLoc = treat_X_tradcom(Xdf.std())
    print("Std Loc")
    print (stdLoc)
    sys.stdout.flush()

    if std is None:
        std = stdLoc

    std = std.to_frame().transpose()
    stdDf=pd.concat([std, stdLoc.to_frame().transpose()])
    std = stdDf.max()

    print("Std")
    print (std)
  
    sys.stdout.flush()
    return(mean, std)


def prepare_tradcom_classification(training=True,
                                   ret_type='df',
                                   sequence_length=5000,
                                   features_list=[1,2,3,4],
                                   output_dim=3,
                                   file_list=None,
                                   mean=None,
                                   std=None,
                                   training_count=None):
    """
    prepare the datasets for the trading competition. training determines which datasets will be read
    returns: X and y: Pandas.DataFrames or np-Arrays storing the X - and y values for the fitting. 
    
    TODO: refactor - move file operations to separate functions, move stacking to function,
    remove commented blocks and undesired print statements
    """
    load_file = {'df': pd.read_pickle,
                 'stack': np.load,
                 'flat': np.load}
    
    save_file = {'df': lambda filename, obj: obj.to_pickle(filename),
                 'stack': lambda filename, obj: np.save(filename, obj),
                 'flat': lambda filename, obj: np.save(filename, obj)}

    print("Features_list",features_list)
    
    Xdf = pd.DataFrame()
    ydf = pd.DataFrame()

    outfile = "training_data_large/save_"+str(len(file_list))
    if training:
        outfile += "_train"
    else:
        if training_count is None:
            print("Training count needs to be given for testing")
            raise ValueError
        if mean is None or std is None:
            print("Mean & std to be given for testing")
            raise ValueError

        outfile += "_"+str(training_count)+"_test"
        
    filetype = '.pickle' if ret_type == 'df' else '.npy'

    outfile_X = outfile+"_X" + filetype
    outfile_y = outfile+"_y" + filetype
    outfile_m = outfile+"_m" + filetype
    outfile_s = outfile+"_s" + filetype

    if os.path.isfile(outfile_X) and os.path.isfile(outfile_y):
        X = load_file[ret_type](outfile_X)
        y = load_file[ret_type](outfile_y)
        #X = np.load(outfile_X)
        #y = np.load(outfile_y)
        if training:
          mean = pd.Series(np.load(outfile_m))
          std  = pd.Series(np.load(outfile_s))

        print("Found files ", outfile_X , " and ", outfile_y)
        return (X,y,mean,std)

    for filename in file_list:

        signalfile = filename.replace('prod_data','signal')
        signalfile = signalfile.replace('txt','csv')

        print("Working on Input files: ",filename, ", ",signalfile)

        if not os.path.isfile(signalfile):
            print("File ",signalfile," is not existing. Aborting.")
            sys.exit()

        # get the date...
        r = re.compile('^\D*(\d*)\D*', re.UNICODE)
        date = re.search(r, filename).group(1)
        print("Date is ",date)
        date_ux = time.mktime(datetime.datetime.strptime(date,"%Y%m%d").timetuple())

        # load dataframes and reindex
        Xdf_loc = pd.read_csv(filename, sep=" ", header = None,)
        # print(Xdf_loc.iloc[:3])
        Xdf_loc['Milliseconds'] = Xdf_loc[0]
        Xdf_loc['Date'] = pd.to_datetime(date_ux*1000*1000*1000)
        # Xdf_loc[0] = pd.to_datetime(date_ux*1000*1000*1000 + Xdf_loc[0]*1000*1000)
        # Xdf_loc = Xdf_loc.set_index([0])
        Xdf_loc = Xdf_loc.set_index(['Date', 'Milliseconds'], append=False, drop=True)
        # print(Xdf_loc.iloc[:3])

        Xdf = pd.concat([Xdf, Xdf_loc])
        print(Xdf.index[0])
        print(Xdf.index[-1])
    
        ydf_loc = pd.read_csv(signalfile, names = ['Milliseconds','signal',], )
        # print(ydf_loc.iloc[:3])
        #ydf_loc['Milliseconds'] = ydf_loc[0]
        ydf_loc['Date'] = pd.to_datetime(date_ux*1000*1000*1000)
        #ydf_loc[0] = pd.to_datetime(date_ux*1000*1000*1000 + ydf_loc[0]*1000*1000)
        #ydf_loc = ydf_loc.set_index([0])
        ydf_loc = ydf_loc.set_index(['Date', 'Milliseconds'], append=False, drop=True)
        # print(Xdf_loc.iloc[:3])
    
        ydf = pd.concat([ydf, ydf_loc])

    #select by features_list
    Xdf = Xdf[features_list]

#     print("XDF After")
#     print(Xdf)  

    Xdf, mean, std = standardize_inputs(Xdf, colgroups=[[2, 4], [3, 5]], mean=mean, std=std)
    # Xdf, mean, std = standardize_inputs(Xdf, colgroups=[[0, 1], ], mean=mean, std=std)

    # if nothing from above, the use the calculated data

    print("X-Dataframe after standardization")
    print(Xdf)
    print("Input check")
    print("Mean (should be 0)")
    print (Xdf.mean())
    print("Variance (should be 1)")
    print (Xdf.std())
   

    Xdf_array = Xdf.values
    
    X_xdim, X_ydim = Xdf_array.shape
    
    if ret_type == 'stack':               
        #start_time = time.time()  
        X = np.zeros((Xdf.shape[0]-sequence_length+1, sequence_length, len(features_list)))
        for i in range(0, Xdf.shape[0]-sequence_length+1):
            slice = Xdf.values[i:i+sequence_length]
            X[i] = slice
        #print("Time for Array Fill ", time.time()-start_time)  
        print(X.shape)
    elif ret_type == 'flat':
        X = Xdf_array.reshape((1, Xdf_array.shape[0], Xdf_array.shape[1]))
    elif ret_type == 'df':
        X = Xdf
    else:
        raise ValueError
    
    #print(X[-1])
    #print(_X[-1])
    # print(Xdf.iloc[-5:])

    ydf['sell'] = ydf.apply(lambda row: (1 if row['signal'] < -0.9 else 0 ), axis=1)
    ydf['buy']  = ydf.apply(lambda row: (1 if row['signal'] > 0.9 else 0 ), axis=1)
    ydf['hold'] = ydf.apply(lambda row: (1 if row['buy'] < 0.9 and row['sell'] <  0.9 else 0 ), axis=1)

    del ydf['signal']
    
    print("Buy signals:", ydf[ydf['buy'] !=0 ].shape[0])
    print("Sell signals:", ydf[ydf['sell'] !=0 ].shape[0])
    print("% of activity signals", float((ydf[ydf['buy'] !=0 ].shape[0] + ydf[ydf['sell'] !=0 ].shape[0])/ydf.shape[0]))
    
    if ret_type == 'stack':   
        y = np.zeros((ydf.shape[0]-sequence_length+1, sequence_length, output_dim))
        for i in range(0, ydf.shape[0]-sequence_length+1):
            slice = ydf.values[i:i+sequence_length]
            y[i] = slice 
        print(y.shape)
    elif ret_type == 'flat':
        y = ydf.values
        y = y.reshape((1, y.shape[0], y.shape[1]))
    elif ret_type == 'df':
        y = ydf
    else:
        raise ValueError        


    save_file[ret_type](outfile_X, X)
    save_file[ret_type](outfile_y, y)
    # np.save(outfile_X, X)
    # np.save(outfile_y, y)
    save_file[ret_type](outfile_m, mean)
    save_file[ret_type](outfile_s, std)
    #np.save(outfile_m, m)
    #np.save(outfile_s, s)
   
    return (X,y,mean,std)


def generator(X, y):
    print("Call to generator")
    print(X.index.equals(y.index))
    c = 1
    
    #dates = X.index.get_level_values(0).unique()
    
    while True:
        for date_idx in X.index.get_level_values(0).unique():
            #print(date_idx)
            #print(X.loc[date_idx].shape)
            #print(y.loc[date_idx].shape)
            X_array = X.loc[date_idx].values
            y_array = y.loc[date_idx].values
            X_samples = X_array.reshape((1, X_array.shape[0], X_array.shape[1]))
            y_samples = y_array.reshape((1, y_array.shape[0], y_array.shape[1]))
            yield {'input': X_samples, 'output': y_samples}


def train_and_predict_classification(model, sequence_length=5000, features=32, output_dim=3, batch_size=128, epochs=5, name = "model",  training_count=3, testing_count=3):

    final_loss = 0
    file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))

    if len(file_list) == 0:
        print ("Files ./training_data_large/product_data_*txt and signal_*.csv are needed. Please copy them in the ./training_data_large/ . Aborting.")
        sys.exit()
 
    line = []
    mean = None
    std  = None
    for j in range(training_count):
        filename = file_list[j]
        print('Normalizing: ',filename)
    #    (mean, std) = get_tradcom_normalization(filename = filename, mean = mean, std = std)
        
    # here i removed some intendation
    for j in range(training_count):
        filename = file_list[j]
        print('Training: ',filename)

        X,y = prepare_tradcom_classification(training = True, sequence_length = sequence_length, features = features, output_dim = output_dim, filename = filename, mean = mean, std = std)

        # running over all epochs to get the optimizer working well...
        history = model.fit({'input': X, 'output': y},
                      verbose=1,
                      nb_epoch=epochs,
                      shuffle=False,
                      batch_size=batch_size)
        print(history.history)
        sys.stdout.flush()
        final_loss = history.history['loss']
        line.extend(final_loss)

        save_neuralnet (model, "ufcnn_"+str(j))
    
    plt.figure()
    plt.plot(line) 
    plt.savefig("Convergence.png")
    #plt.show()

    total_class_count = 0
    total_correct_class_count = 0

    for k in range(testing_count):
        filename = file_list[training_count + k]
        print("Predicting: ",filename)

        X,y,mean,std = prepare_tradcom_classification(training=False, sequence_length=sequence_length, features=features, output_dim=output_dim, filename=filename, mean=mean, std=std )

        predicted_output = model.predict({'input': X,}, batch_size=batch_size, verbose = 2)
        #print(predicted_output)

        yp = predicted_output['output']
        xdim, ydim = yp.shape
    
        ## MSE for testing
        total_error  = 0
        correct_class= 0
        for i in range (xdim):
            delta = 0.
            for j in range(ydim):
                delta += (y[i][j] - yp[i][j]) * (y[i][j] - yp[i][j])
                #print ("Row %d, MSError: %8.5f " % (i, delta/ydim))
        
            total_error += delta
            if np.argmax(y[i]) == np.argmax(yp[i]):
                correct_class += 1

        print ("FIN Correct Class Assignment:  %6d /%7d" % (correct_class, xdim))
        print ("FIN Final Loss:  ", final_loss)

        total_class_count += xdim
        total_correct_class_count += correct_class

    print ("FINFIN Correct Class Assignment:  %6d /%7d" % (total_correct_class_count, total_class_count))

    return {'model': model, 'predicted_output': predicted_output['output'], 'expected_output': y}

    
def check_prediction(Xdf, y, yp, mean, std):
    """ Check the predicted classes and print results
    """
    ## MSE for testing
    total_error  = 0
    correct_class= 0

    y_pred_class = np.zeros((y.shape[2],))
    y_corr_pred_class = np.zeros((y.shape[2],))
    y_class      = np.zeros((y.shape[2],))
    y_labels = np.zeros((y.shape[1], y.shape[2]))
    a=['Buy','Sell','Hold']

    for i in range (y.shape[1]):
        delta = 0.
        for j in range(y.shape[2]):
            delta += (y[0][i][j] - yp[0][i][j]) * (y[0][i][j] - yp[0][i][j])
    
        total_error += delta
        
        #if np.any(y[0][i] != 0):     # some debug output, comment if not needed!
        #    print("Actual: ", y[0][i])
        #    print("Predicted: ", yp[0][i])
            
        if np.argmax(y[0][i]) == np.argmax(yp[0][i]):
            correct_class += 1
            y_corr_pred_class[np.argmax(yp[0][i])] += 1.

        y_pred_class[np.argmax(yp[0][i])] += 1.
        y_class[np.argmax(y[0][i])] += 1.
        y_labels[i][np.argmax(yp[0][i])] = 1

    print()
    print("Total MSE Error: ",  total_error / y.shape[1])
    print("Correct Class Assignment:  %6d /%7d" % (correct_class, y.shape[1]))
    
    for i in range(y.shape[2]):
        print("%4s: Correctly Predicted / Predicted / Total:    %6d/%6d/%7d" %(a[i], y_corr_pred_class[i], y_pred_class[i], y_class[i]))

    Xdf = Xdf * std
    Xdf = Xdf + mean

    yp_p = yp.reshape((yp.shape[1],yp.shape[2]))
    #print(yp_p)

    ydf2 = pd.DataFrame(yp_p, columns=['buy','sell','hold'])
    Xdf2 = Xdf.reset_index(drop=True)
    Xdf2 = pd.concat([Xdf2,ydf2], axis = 1)

    Xdf2['signal'] = 0.
    print(Xdf2)

    xy_df = pd.concat([Xdf, pd.DataFrame(y_labels, columns=['buy','sell','hold'], index=Xdf.index)], axis=1)
    xy_df = xy_df.rename(columns={2: "bidpx_", 3: "bidsz_", 4: "askpx_", 5: "asksz_"})


    # store everything in signal
    # -1 for short, 1 for long...
    Xdf2['signal'] = Xdf2.apply(lambda row: (1  if row['buy']  > row['hold'] and row['buy']  > row['sell'] else 0 ), axis=1)
    Xdf2['signal'] = Xdf2.apply(lambda row: (-1 if row['sell'] > row['hold'] and row['sell'] > row['buy'] else row['signal'] ), axis=1)

    invested_tics = 0
    pnl = 0.
    position = 0.
    last_row = None
    nr_trades = 0
    trade_pnl = 0.

    for (index, row) in Xdf2.iterrows():
        (pnl_, position, is_trade) = calculate_pnl(position, last_row, row, fee_per_roundtrip=0.0)
        pnl += pnl_
         
        last_row = row
        if position < -0.1 or position > 0.1:
            invested_tics +=1
        if is_trade:
            nr_trades += 1
            trade_pnl = 0.
        trade_pnl += pnl_

    sig_pnl, sig_trades = get_pnl(xy_df)
    print("Signals PnL: {}, # of trades: {}".format(sig_pnl, sig_trades))

    print ("Nr of trades: %5d /%7d" % (nr_trades, y.shape[1]))
    print ("PnL: %8.2f InvestedTics: %5d /%7d" % (pnl, invested_tics, y.shape[1]))
    
### END


def get_pnl(df, max_position=1, comission=0):
    deals = []
    pnl = 0
    position = 0
    df_with_signals = df[(df['sell'] != 0) | (df['buy'] != 0)]

    for idx, row in df_with_signals.iterrows():
        if row['buy'] == 1 and position < max_position:
            print(row)
            current_trade = -row['buy'] * row["askpx_"]
            position += 1
            pnl = pnl + current_trade - comission
            deals.append(current_trade)
            print("Running PnL: {}, position: {}".format(pnl, position))
        elif row['sell'] == 1 and position > -max_position:
            print(row)
            current_trade = row['sell'] * row["bidpx_"]
            position -= 1
            pnl = pnl + current_trade - comission
            deals.append(current_trade)
            print("Running PnL: {}, position: {}".format(pnl, position))

    if position == 1:
        day_closing_trade = df.iloc[-1]["bidpx_"]
        pnl = pnl + day_closing_trade - comission
        deals.append(day_closing_trade)
        print("Close last hanging deal on the end of the day, PnL: {}, position: {}".format(pnl, position))
    elif position == -1:
        day_closing_trade = -df.iloc[-1]["askpx_"]
        pnl = pnl + day_closing_trade - comission
        deals.append(day_closing_trade)
        print("Close last hanging deal on the end of the day, PnL: {}, position: {}".format(pnl, position))

    print("Check PnL: {} vs {}".format(pnl, np.sum(deals)))
    return pnl, len(deals)


def calculate_pnl(position, row, next_row, fee_per_roundtrip=0.):
    if row is None:
        return (0.,0., False)

    old_position = position

    pnl = 0.

    if position < -0.1:
        pnl = position * (next_row[4] - row[4]) # ASK

    if position >  0.1:
        pnl = position * (next_row[2] - row[2]) # BID


    signal = row['signal']

    #  if we are short and need to go long...
    if position < -0.1 and signal > 0.1:
        position = 0.

    #  if we are long and need to go short...
    if position > 0.1 and signal < -0.1:
        position = 0.

    trade = False
    if position == 0. and abs(signal) > 0.1:
        position = signal
        if position < -0.1:
            pnl = position * (next_row[4] - row[2]) # ASK

        if position >  0.1:
            pnl = position * (next_row[2] - row[4]) # BID
        pnl -= fee_per_roundtrip
        trade = True

    #print ("SIGNAL:",signal, ", old_position: ", old_position, " position:", position, ", pnl: ",pnl, "Bid: ",row[2],next_row[2],", ASK ",row[4], next_row[4] )
    return (pnl, position, trade)
    ## End calculate_pnl



def get_tracking_data (sequence_length=5000, count=2000, D=10, delta=0.3, omega_w=0.005, omega_ny=0.005):
    """ get tracking data for a target moving in a square with 2D side length 
        delta ... radius of the round target
        omega_ ... random noise strength
    """
    
    A = np.array([[1,1,0,0],[0,1,0,0],[0,0,1,1],[0,0,0,1]])

    X = np.zeros((count,sequence_length,1))
    y = np.zeros((count,sequence_length,2))
 
    
    for i in range(count):
        z_t = np.random.normal(1,.5,4)
        g_t = np.random.normal(1,.5,4)
    
        x_t  = z_t[0]
        xp_t = z_t[1]
        y_t  = z_t[2]
        yp_t = z_t[3]

        for j in range(sequence_length):     

            # reflect at the border of the square with length 2D
            if -D + delta < x_t and x_t < D - delta:
                xp_new_t = xp_t
            elif -D + delta <= x_t:
                xp_new_t = -abs(xp_t)
            else:
                xp_new_t = abs(xp_t)

            if -D + delta < y_t and y_t < D - delta:
                yp_new_t = yp_t
            elif -D + delta <= y_t:
                yp_new_t = -abs(yp_t)
            else:
                yp_new_t = abs(yp_t)

            g_t[0] = x_t
            g_t[1] = xp_new_t
            g_t[2] = y_t
            g_t[3] = yp_new_t
      
            w_t = np.random.normal(0.,0.5*omega_w,4)
            w_t[1] = 0.
            w_t[3] = 0.

            ny_t = np.random.normal(0.,0.5*omega_ny,1)
 
            z_t = np.dot(A, g_t) + w_t

       

            x_t  = z_t[0]
            xp_t = z_t[1]
            y_t  = z_t[2]
            yp_t = z_t[3]
            

            theta = np.arctan(y_t/x_t) + ny_t[0]

            # params for the nn
            # learn to predict x&y by bearing (theta)
            X[i][j][0] = theta
            y[i][j][0] = x_t
            y[i][j][1] = y_t
            #print ("X_T: ", x_t, ", Y_T: ",y_t)

    return (X,y)
 
    
def get_simulation(write_spans = True):
    """
    Make trading competition-like input and output data from the cosine function
    """
    from signals import find_all_signals, make_spans, set_positions, pnl
    from datetime import date
    
    df = pd.DataFrame(data={"askpx_": np.round(gen_cosine_amp(k=0, period=10, amp=20)[:, 0, 0]+201),
                                "bidpx_": np.round(gen_cosine_amp(k=0, period=10, amp=20)[:, 0, 0]+200)})
    df = find_all_signals(df) 
    df = make_spans(df, 'Buy')
    df = make_spans(df, 'Sell')
    print("Simulation PnL", pnl(df))
    
    Xdf = df[["askpx_", "bidpx_"]]
    df['buy'] = df['Buy'] if not write_spans else df['Buys']
    df['sell'] = df['Sell'] if not write_spans else df['Sells']
    ydf = df[["buy", "sell"]]
    
    Xdf['Milliseconds'] = Xdf.index
    Xdf['Date'] = pd.to_datetime(date.today())
    Xdf = Xdf.set_index(['Date', 'Milliseconds'], append=False, drop=True)
    #print(Xdf.index[0:100])
    
    ydf['Milliseconds'] = ydf.index
    ydf['Date'] = pd.to_datetime(date.today())
    ydf = ydf.set_index(['Date', 'Milliseconds'], append=False, drop=True)
    #print(ydf.index[0:100])
    
    Xdf, mean, std = standardize_inputs(Xdf, colgroups=[["askpx_", "bidpx_"], ])
    
    ydf['hold'] = ydf.apply(lambda row: (1 if row['buy'] == 0 and row['sell'] == 0 else 0 ), axis=1)
    
    print("Buy signals:", ydf[ydf['buy'] !=0 ].shape[0])
    print("Sell signals:", ydf[ydf['sell'] !=0 ].shape[0])
    print("% of activity signals", float(ydf[ydf['buy'] !=0 ].shape[0] + ydf[ydf['sell'] !=0 ].shape[0])/float(ydf.shape[0]))
    
    print(Xdf.shape, Xdf.columns)
    print(ydf.shape, ydf.columns)    
    
    return (Xdf,ydf,mean,std)
    
    
        

#########################################################
## Test the net with damped cosine  / remove later...
#########################################################


if len(sys.argv) < 2 :
    print ("Usage: UFCNN1.py action    with action from [cos_small, cos, tradcom, tradcom_simple, tracking] [model_name]")
    print("       ... with model_name = name of the saved file (without addition like _architecture...) to load the net from file")

    sys.exit()

action = sys.argv[1]

if len(sys.argv) == 3:
    model_name = sys.argv[2]
else:
    model_name = None


sequence_length = 64        # same as in Roni Mittelman's paper - this is 2 times 32 - a line in Ronis input contains 33 numbers, but 1 is time and is omitted
features = 1                # guess changed Ernst 20160301
nb_filter = 150             # same as in Roni Mittelman's paper
filter_length = 5           # same as in Roni Mittelman's paper
output_dim = 1              # guess changed Ernst 20160301

if action == 'cos_small':
    print("Running model: ", action)
    UFCNN_1 = ufcnn_model(sequence_length=sequence_length)
    print_nodes_shapes(UFCNN_1)
    case_1 = train_and_predict_regression(UFCNN_1, sequence_length=sequence_length)

    print('Ploting Results')
    plt.figure(figsize=(18,3))
    plt.plot(case_1['expected_output'].reshape(-1)[-10000:]) #, predicted_output['output'].reshape(-1))
    plt.plot(case_1['predicted_output']['output'].reshape(-1)[-10000:])
    #plt.savefig('sinus.png')
    plt.show()


if action == 'cos':
    print("Running model: ", action)
    UFCNN_2 = ufcnn_model()
    print_nodes_shapes(UFCNN_2)
    case_2 = train_and_predict_regression(UFCNN_2)

    print('Ploting Results')
    plt.figure(figsize=(18,3))
    plt.plot(case_2['expected_output'].reshape(-1)[-10000:]) #, predicted_output['output'].reshape(-1))
    plt.plot(case_2['predicted_output']['output'].reshape(-1)[-10000:])
    #plt.savefig('sinus.png')
    plt.show()

if action == 'tradcom':
    print("Running model: ", action)
    sequence_length = 500
    features = 4
    output_dim = 3
    # Roni used rmsprop
    sgd = SGD(lr=0.005, decay=1e-6, momentum=0.9, nesterov=True) 

    UFCNN_TC = ufcnn_model(regression = False, output_dim=output_dim, features=features, 
       loss="categorical_crossentropy", sequence_length=sequence_length, optimizer=sgd )

    #print_nodes_shapes(UFCNN_TC)

    case_tc = train_and_predict_classification(UFCNN_TC, features=features, output_dim=output_dim, sequence_length=sequence_length, epochs=50, training_count=10, testing_count = 6 )

if action == 'tracking':
    print("Running model: ", action)
    sequence_length = 5000
    count=20
    output_dim = 2
    # Roni used rmsprop
    sgd = SGD(lr=0.00005, decay=1e-6, momentum=0.9, nesterov=True) 
    rms = RMSprop(lr=0.001, rho=0.9, epsilon=1e-06)

    model = ufcnn_model_concat(regression = True, output_dim=output_dim, features=features, 
       loss="mse", sequence_length=sequence_length, optimizer=rms )

    #print_nodes_shapes(UFCNN_TC)
    (X,y) = get_tracking_data (sequence_length=sequence_length, count=count)

    X = np.subtract(X,X.mean())
    y = np.subtract(y,y.mean())

    #plt.figure()
    #plt.plot(x1, y1) 
    #plt.savefig("TrackingTracking.png")


    history = model.fit({'input': X, 'output': y},
                      verbose=1,
                      nb_epoch=300)
    print(history.history)


if action == 'tradcom_simple':
    simulation = False # Use True for simulated cosine data, False - for data from files
    training_count = 20 # FIXED: Does not work with other numbers - the treatment of X and y in prepare_tradcom_classification needs to be changed
    validation_count = 2
    testing_count = 8
    sequence_length = 5000

    #features_list = list(range(0,2)) # list(range(2,6)) #list(range(1,33))

    if not simulation:
        features_list = list(range(2,6))   ## to run with Bid/Ask price/vol only
        features_list = list(range(1,33))  ## FULL

        file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))[:training_count]
        print ("Training file list ", file_list)
        (X, y, mean, std) = prepare_tradcom_classification(training=True,
                                                           ret_type='df',
                                                           sequence_length=sequence_length,
                                                           features_list=features_list,
                                                           output_dim=3,
                                                           file_list=file_list)

        file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))[training_count:training_count+validation_count]
        print ("Validation file list ", file_list)
        (X_val, y_val, mean_, std_) = prepare_tradcom_classification(training=True,
                                                                   ret_type='df',
                                                                   sequence_length=sequence_length,
                                                                   features_list=features_list,
                                                                   output_dim=3,
                                                                   file_list=file_list,
                                                                   mean=mean,
                                                                   std=std,
                                                                   training_count=training_count)

    else:
        features_list = list(range(0,2))
        print("Using simulated data for training...")
        (X, y, mean, std) = get_simulation()
    #
    print("X shape: ", X.shape)
    # print(X)
    print("Y shape: ", y.shape)
    #
    # print("Mean")
    # print(mean)
    # print("Std")
    # print(std)
   
    #for _d in generator(X, y):
    #    print(_d)

    sgd = SGD(lr=0.0001, decay=1e-6, momentum=0.9, nesterov=True)
    #rmsprop = RMSprop (lr=0.00001, rho=0.9, epsilon=1e-06)  # for sequence length 500
    rmsprop = RMSprop (lr=0.000005, rho=0.9, epsilon=1e-06) # for sequence length 5000


    # load the model from disk if model name is given...
    if model_name is not None:
        model = load_neuralnet(model_name)
    else:
        model = ufcnn_model_concat(regression = False, output_dim=3, features=len(features_list), 
                                   loss="categorical_crossentropy", sequence_length=sequence_length, optimizer=rmsprop )
        
    print_nodes_shapes(model)

    #draw_model(model)
    #history = model.fit({'input': X, 'output': y},
    #                 verbose=2,
    #                 nb_epoch=5,
    #                 shuffle=False,
    #                 batch_size=1)

    start_time = time.time()
    epoch = 400
    history = model.fit_generator(generator(X, y),
                      nb_worker=1,
                      samples_per_epoch=training_count,
                      verbose=1,
                      nb_epoch=epoch,
                      show_accuracy=True,
                      validation_data=generator(X_val, y_val),
                      nb_val_samples=validation_count)
    print(history.history)
    print("--- Fitting: Elapsed: %d seconds per iteration %5.3f" % ( (time.time() - start_time),(time.time() - start_time)/epoch))

    save_neuralnet (model, "ufcnn_sim") if simulation else save_neuralnet (model, "ufcnn_concat")

    if not simulation:
        # and get the files for testing
        file_list = sorted(glob.glob('./training_data_large/prod_data_*v.txt'))[training_count:training_count+testing_count]

        (X_pred, y_pred, mean_, std_) = prepare_tradcom_classification(training=False,
                                                                       ret_type='df',
                                                                       sequence_length=sequence_length,
                                                                       features_list=features_list,
                                                                       output_dim=3,
                                                                       file_list=file_list,
                                                                       mean=mean,
                                                                       std=std,
                                                                       training_count=training_count)
    else:
        print("Using simulated data for training...")
        (X_pred, y_pred, mean_, std_) = get_simulation()

    print(X_pred.iloc[0:200])
    print(y_pred.iloc[0:200])

    i=1  
    for date_idx in X_pred.index.get_level_values(0).unique():

        X_array = X_pred.loc[date_idx].values
        y_array = y_pred.loc[date_idx].values
        X_samples = X_array.reshape((1, X_array.shape[0], X_array.shape[1]))
        y_samples = y_array.reshape((1, y_array.shape[0], y_array.shape[1]))
        print(y_samples[0, 0:200, :])

        inp = {'input': X_samples, 'output': y_samples}

        print("Predicting: day ",i ,": ", date_idx)
        predicted_output = model.predict({'input': X_samples,}, batch_size=1, verbose = 2)

        check_prediction(X_pred.loc[date_idx], y_samples, predicted_output['output'], mean, std)
        i += 1
