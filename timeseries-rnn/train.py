import numpy as np
import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('data_dir', help='directory with csv files')
parser.add_argument('--epochs', help='number of training epochs', type=int, default=300)
parser.add_argument('--learning_rate', help='learning rate of RMSprop', type=float, default=0.001)  # TODO: What to choose as default learning rate?
parser.add_argument('--layers', help='number of LSTM layers', type=int, default=1)
parser.add_argument('--neurons', help='number of neurons per LSTM layer', type=int, default=10)  # TODO: Make this accept list.
parser.add_argument('--mixture_components', help='number of Gaussians in the mixture distribution', type=int, default=10)
parser.add_argument('--change', help='use change of data for training (good for cumulative sequences)', action='store_true')
parser.add_argument('--stds', help='number of standard deviations to normalize the data to', type=float, default=1.)
args = parser.parse_args()

# Store every timeseries in a csv file where row is time and column is x_i at that time.
# No header, whitespace as delimiter.
# TODO: Maybe add header and delimiter as options.


# TODO: Maybe refactor this to preprocessing script so you don't have to run it each time. 
# TODO: At least save this as npz archive at first run.
data_dir = args.data_dir
filenames = os.listdir(data_dir)
timeseries = []

print "Reading files from", data_dir

for filename in filenames:
    ts = np.genfromtxt(os.path.join(data_dir, filename))
    if ts.ndim == 1:  # csv file has only one column, ie one variable
        ts = ts[:, np.newaxis]
    timeseries.append(ts)
timeseries = np.array(timeseries)
if args.change:
    timeseries = np.diff(timeseries, axis=1)


# TODO: Check that all time series have the same number of timesteps and dimensions
num_timeseries, num_timesteps, num_dims = timeseries.shape

print "Read {} time series with {} time steps and {} dimensions".format(num_timeseries, num_timesteps, num_dims)


# TODO: Save this somewhere so we can reuse it in prediction and generation.
means = np.mean(timeseries, axis=(0, 1))
stds = args.stds * np.std(timeseries, axis=(0, 1))  # Scaled by number of stds to normalize the data to.
#traj_stds[traj_stds == 0] = 1.  # Fix zero stds by setting them to 0.
np.savez('model/preprocessing.npz', means=means, stds=stds, change=args.change)


# TODO: Make num stds as parameter for script. 
def normalize(x):
    return np.nan_to_num((x - means) / stds)

def denormalize(x):
    return x * stds + means


timeseries = normalize(timeseries)
np.savetxt('out.txt', timeseries, fmt='%s')


print timeseries


print "Building network... (this can take a while)"

from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout
from keras.layers import LSTM
from keras.optimizers import RMSprop
from gmm import GMMActivation, gmm_loss

model = Sequential()
if args.layers == 1:
    model.add(LSTM(args.neurons, batch_input_shape=(num_timeseries, 1, num_dims), return_sequences=False, stateful=True))
else:
    model.add(LSTM(args.neurons, batch_input_shape=(num_timeseries, 1, num_dims), return_sequences=True, stateful=True))
    for i in range(args.layers - 2):
        model.add(LSTM(args.neurons, return_sequences=True, stateful=True))
    model.add(LSTM(args.neurons, return_sequences=False, stateful=True))

num_mixture_components = args.mixture_components
model.add(Dense((num_dims + 2) * num_mixture_components))
model.add(GMMActivation(num_mixture_components))
model.compile(loss=gmm_loss, optimizer=RMSprop(lr=args.learning_rate))


print "Starting training..."
for epoch in range(1, args.epochs+1):
    print 'Epoch', epoch,
    losses_epoch = []
    for i in range(num_timesteps - 1):
        results = model.train_on_batch(timeseries[:, i:i+1], timeseries[:, i+1])
        losses_epoch.append(results[0])
    mean_loss = np.mean(losses_epoch)
    print '- loss:', mean_loss
    model.reset_states()


print "Saving model..."

# TODO: Save model periodically (every ... epochs).
# TODO: Overwrite?
# TODO: Allow picking up this model and training it further.
with open('model/model.json', 'w') as out:
    out.write(model.to_json())
model.save_weights('model/weights.h5', overwrite=True)
