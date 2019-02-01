from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt 

from keras.datasets import mnist
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation, Flatten, Reshape
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.utils import np_utils

from keras.layers.convolutional_transpose import Convolution1D_Transpose


"""
   modified from https://github.com/loliverhennigh/All-Convnet-Autoencoder-Example 
   An autoencoder with 2D Convolution-Transpose layer in TF
"""

def save_neuralnet (model, model_name):
    json_string = model.to_json()
    open(model_name + '_architecture.json', 'w').write(json_string)
    model.save_weights(model_name + '_weights.h5', overwrite=True)

def load_neuralnet (model_name):
    # The Convolution1D_Transpose class needs to be stated while loading!
    model = model_from_json(open(model_name+'_architecture.json').read(),{'Convolution1D_Transpose':Convolution1D_Transpose})
    model.load_weights(model_name+'_weights.h5')
    return model



batch_size = 100 # total number of elements in the X_ and Y_ (60000 train, 10000 test) arrays must be a multiple of batch_size!
nb_epoch = 500

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
Y_train = X_train.reshape(-1,1,784)
Y_test  = X_test.reshape(-1,1,784)

print("Y SHAPE",Y_train.shape)


model = Sequential()
nb_filter = 16

# input  28 * 28, output 24 * 24
model.add(Convolution2D(nb_filter, 5, 5, input_shape=((1, img_rows, img_cols)), border_mode = 'valid'))
model.add(Activation('relu'))

# input  24 * 24, output 20 * 20
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  20 * 20, output 16 * 16
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  16 * 16, output 12 * 12 * 16
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  12 * 12, output 8 * 8 * 16
model.add(Convolution2D(nb_filter, 5, 5, border_mode = 'valid'))
model.add(Activation('relu'))

# input  8 * 8, output 7 * 7 * 16
model.add(Convolution2D(5, 2, 2, border_mode = 'valid'))
model.add(Activation('relu'))


model.add(Flatten())
model.add(Dropout(0.2))

#model.add(Reshape((1,1,98)))
model.add(Reshape((5,49)))

# input  input 98, needs to be blown up 8 fold 
W_shape = [2, 5, 5] 
b_shape = [5]
strides = [1,2,1]
padding='valid'

# keep everything 1:1

# double everything
#deconv_shape = [batch_size, output_size_y, output_size_x, number_of_filters]
deconv_shape = [batch_size, 98*1, 5]
model.add(Convolution1D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding)) 
model.add(Activation('relu'))

deconv_shape = [batch_size, 98*2, 5]
model.add(Convolution1D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding))  
model.add(Activation('relu'))

deconv_shape = [batch_size, 98*4, 5]
model.add(Convolution1D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding))  
model.add(Activation('relu'))

deconv_shape = [batch_size, 98*8, 1] ## 98 * 8 ist OUTPUT ROWS, 1 Output COLS!
W_shape = [2, 1, 5] 
b_shape = [1]
model.add(Convolution1D_Transpose(deconv_shape=deconv_shape,  W_shape=W_shape, b_shape=b_shape, strides=strides, padding=padding))  
model.add(Activation('relu'))

#model.add(Reshape((1,28,28)))

print(model.summary())

model.compile(loss='mse', optimizer='rmsprop')
print("Before FIT")

model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch, verbose=1)

score = model.evaluate(X_test, Y_test, verbose=0, batch_size=batch_size)

print('Test score:', score)

y_pred = model.predict(X_test[0:batch_size], verbose=0, batch_size=batch_size)

for i in range(batch_size):
    plt.imsave(arr=y_pred[i].reshape((28,28)),fname='number_'+str(i)+'_is_'+str(y_test[i])+'.png')

    #print ('Number: ',i,' is ', y_test[i])
    # if your machine has a display attached, you can use this instead (better graphics)
    #imgplot = plt.imshow(y_pred[0].reshape((28,28)))
    #plt.savefig('new_run_'+str(i)+'.png'

save_neuralnet (model, 'mnistauto')

                                    
