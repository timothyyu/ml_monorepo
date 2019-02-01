from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt 

from keras.datasets import mnist
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation, Flatten, Reshape
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.utils import np_utils

from keras.layers.convolutional_transpose import Convolution2D_Transpose


"""
   modified from https://github.com/loliverhennigh/All-Convnet-Autoencoder-Example 
   An autoencoder with 2D Convolution-Transpose layer in TF
"""

def save_neuralnet (model, model_name):

    json_string = model.to_json()
    open(model_name + '_architecture.json', 'w').write(json_string)
    model.save_weights(model_name + '_weights.h5', overwrite=True)

def load_neuralnet (model_name):
    # The 2D Convolution2D_Transpose class needs to be stated whil loading!
    model = model_from_json(open(model_name+'_architecture.json').read(),{'Convolution2D_Transpose':Convolution2D_Transpose})
    model.load_weights(model_name+'_weights.h5')
    return model



batch_size = 100 # total number of elements in the X_ and Y_ (60000 train, 10000 test) arrays must be a multiple of batch_size!
nb_epoch = 100

# input image dimensions
img_rows, img_cols = 28, 28
# number of convolutional filters to use
nb_filters = 28 * 14
# size of pooling area for max pooling
nb_pool = 2
# convolution kernel size
nb_conv = 2

# the data, shuffled and split between train and test sets
(X_train, y_train), (X_test, y_test) = mnist.load_data()

X_train = X_train.reshape(X_train.shape[0], 1, img_rows, img_cols)
X_test = X_test.reshape(X_test.shape[0], 1, img_rows, img_cols)
X_train = X_train.astype('float32')
X_test = X_test.astype('float32')
X_train /= 255
X_test /= 255
print('X_train shape:', X_train.shape)
print(X_train.shape[0], 'train samples')
print(X_test.shape[0], 'test samples')

#Y_train = np_utils.to_categorical(y_train, nb_classes)
#Y_test = np_utils.to_categorical(y_test, nb_classes)
Y_train = X_train
Y_test  = X_test

print("Y SHAPE",Y_train.shape)


model = Sequential()
nb_filter = 32

# input  28 * 28, output 24 * 24
model.add(Convolution2D(nb_filter, 5, 5, input_shape=((1, img_rows, img_cols)), border_mode = 'valid'))
model.add(Activation('relu'))

# input  24 * 24, output 20 * 20
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  20 * 20, output 16 * 16
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  16 * 16, output 14 * 14
model.add(Convolution2D(nb_filter, 3, 3, border_mode = 'valid'))
model.add(Activation('relu'))

# input  14 * 14 * 4, output 14 * 14 * 2
model.add(Convolution2D(2, 1, 1, border_mode = 'valid'))
model.add(Activation('relu'))

model.add(MaxPooling2D(pool_size=(2, 2),strides=None, border_mode='valid'))

model.add(Dropout(0.2))

# input  input 14 * 14 * 2, output 28 * 28 * 2 ?
W_shape = [2, 2, 2, 2] # (self.nb_filter, input_dim, self.filter_length, 1)
b_shape = [2]

# keep everything 1:1
#strides = [1,1,1,1]
#deconv_shape = [batch_size, 14, 14, 2]
#padding='same'

# double everything
strides = [1,2,2,1]
#deconv_shape = [batch_size, 28, 28, 2]
deconv_shape = [batch_size, 14, 14, 2]
padding='valid'
model.add(Convolution2D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding)) 
model.add(Activation('relu'))

W_shape = [2, 2, 2, 2] # (self.nb_filter, input_dim, self.filter_length, 1)
deconv_shape = [batch_size, 28, 28, 2]
model.add(Convolution2D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding))  
model.add(Activation('relu'))

model.add(Flatten())
model.add(Dense(784))
model.add(Reshape((1,28,28)))

"""
  W_shape --- shape of the weights - should be calculated internally
   from conv_2d:  (self.nb_filter, input_dim, self.filter_length, x)
          
  b_shape ... shape of the biases - should be calculated internally
   [0] ... nb_filter ?

  deconv_shape
       this is output_shape of TF conv2d_transpose
       [ batch_size, input_cols, input_rows, input_depth]


Also U can set the output_shape(deconv_shape) according to:

def conv_transpose_out_length(input_size, filter_size, border_mode, stride):
    if input_size is None:
        return None
    if border_mode == 'VALID':
        output_size = (input_size - 1) * stride + filter_size
    elif border_mode == 'SAME':
        output_size = input_size
    return output_size

"""

print(model.summary())

model.compile(loss='mse', optimizer='sgd')
print("Before FIT")

model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch, verbose=1)

score = model.evaluate(X_test, Y_test, verbose=0, batch_size=batch_size)

print('Test score:', score)

y_pred = model.predict(Y_test[0:batch_size], verbose=0, batch_size=batch_size)

for i in range(batch_size):
    plt.imsave(arr=y_pred[i].reshape((28,28)),fname='number_'+str(i)+'_is_'+str(y_test[i])+'.png')

    #print ('Number: ',i,' is ', y_test[i])
    # if your machine has a display attached, you can use this instead (better graphics)
    #imgplot = plt.imshow(y_pred[0].reshape((28,28)))
    #plt.savefig('new_run_'+str(i)+'.png'

save_neuralnet (model, 'mnistauto')

                                    
