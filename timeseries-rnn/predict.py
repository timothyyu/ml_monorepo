import sys
import os
import numpy as np


data_dir = sys.argv[1]
filenames = os.listdir(data_dir)
timeseries = []

preprocessing = np.load('model/preprocessing.npz')
timeseries_means = preprocessing['means']
timeseries_stds = preprocessing['stds']
change = preprocessing['change']


print "Reading files from", data_dir

for filename in filenames:
    ts = np.genfromtxt(os.path.join(data_dir, filename))
    if ts.ndim == 1:  # csv file has only one column, ie one variable
        ts = ts[:, np.newaxis]
    timeseries.append(ts)
timeseries = np.array(timeseries)
if change:
    timeseries = np.diff(timeseries, axis=1)


# TODO: Check that all time series have the same number of timesteps and dimensions
num_timeseries, num_timesteps, num_dims = timeseries.shape

print "Read {} time series with {} time steps and {} dimensions".format(num_timeseries, num_timesteps, num_dims)




# TODO: Make num stds as parameter for script. 
def normalize(x):
    return np.nan_to_num((x - timeseries_means) / timeseries_stds)

def denormalize(x):
    return x * timeseries_stds + timeseries_means
    # TODO: This gives 0 values if stddev = 0.


timeseries = normalize(timeseries)


print "Loading model... (this can take a while)"

from keras.models import model_from_json
from gmm import GMMActivation, gmm_loss

with open('model/model.json') as model_file:
	model = model_from_json(model_file.read(), {'GMMActivation': GMMActivation, 'gmm_loss': gmm_loss})

model.load_weights('model/weights.h5')


num_mixture_components = model.get_config()['layers'][-1]['M']

# Predict next timesteps using the training data as input (i. e. not the predictions themselves!).
model.reset_states()
predicted = []
predicted.append(timeseries[:, 0])  # Take first timestep from training data so predicted and expected have the same dimensions.

print "Predicting..."

for i in range(num_timesteps - 1):
    pred_parameters = model.predict_on_batch(timeseries[:, i:i+1])[0]
    means = pred_parameters[:, :num_mixture_components * num_dims]
    sds = pred_parameters[:, num_mixture_components * num_dims:num_mixture_components * (num_dims + 1)]
    weights = pred_parameters[:, num_mixture_components * (num_dims + 1):]
    
    # Reshape arrays to allow broadcasting of means (3-dimensional vectors) and sds/weights (scalars).
    means = means.reshape(-1, num_mixture_components, num_dims)
    sds = sds[:, :, np.newaxis]
    weights = weights[:, :, np.newaxis]
    
    pred = weights * np.random.normal(means, sds)
    pred = np.sum(pred, axis=1)
    predicted.append(pred)
    
predicted_dir = 'predicted'
print "Saving predicted time series to", predicted_dir

predicted = np.array(predicted)
predicted = predicted.transpose((1, 0, 2))
predicted = denormalize(predicted)
for i, pred in enumerate(predicted):
	if change:
		pred = np.append(np.zeros((1, num_dims)), np.cumsum(pred, axis=0), axis=0)
	np.savetxt('{}/{}.dat'.format(predicted_dir, i), pred)
