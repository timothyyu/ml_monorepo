from keras.models import Model
from keras.layers import Input
from keras.optimizers import RMSprop
from keras.callbacks import ModelCheckpoint

import os
import sys
sys.path.insert(0, '..')
from nalu import NALU
from experiments.data_utils import generate_static_dataset


if not os.path.exists('weights'):
    os.makedirs('weights')


# hyper parameters
units = 2
num_samples = 1000

# task
task_name = 'addition'
task_fn = lambda x, y: x + y

# generate the model
ip = Input(shape=(100,))
x = NALU(units)(ip)
x = NALU(1)(x)

model = Model(ip, x)
model.summary()

optimizer = RMSprop(0.1)
model.compile(optimizer, 'mse')

# Generate the datasets
X_train, y_train = generate_static_dataset(task_fn, num_samples, mode='interpolation')
X_test, y_test = generate_static_dataset(task_fn, num_samples, mode='extrapolation')

# Prepare callbacks
weights_path = 'weights/%s_weights.h5' % (task_name)
checkpoint = ModelCheckpoint(weights_path, monitor='val_loss',
                             verbose=1, save_weights_only=True, save_best_only=True)

callbacks = [checkpoint]

# Train model
model.fit(X_train, y_train, batch_size=64, epochs=500,
          verbose=2, callbacks=callbacks, validation_data=(X_test, y_test))

# Evaluate
model.load_weights(weights_path)

scores = model.evaluate(X_test, y_test, batch_size=128)

print("Mean Squared error : ", scores)
