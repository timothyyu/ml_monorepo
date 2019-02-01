# timeseries-rnn

These scripts implement a recurrent neural network, which can generate new data from existing time series. The idea is inspired by Andrej Karparthy's (@karparthy) [char-rnn](http://karpathy.github.io/2015/05/21/rnn-effectiveness/), which does the same thing for text (see also his [blog post](http://karpathy.github.io/2015/05/21/rnn-effectiveness/)). The network consists of one or more LSTM layers and a layer implementing a Gaussian mixture model (instead of the softmax in char-rnn). Therefore, the network predicts the parameters of a mixture distribution, from which the values of the time series at the next time step can be sampled. See pp. 9-10 in my report [here](https://github.com/jrieke/lstm-biology/blob/master/Project%20Report.pdf) for more details. 

The code is based on [keras](http://keras.io/) and [Theano](http://deeplearning.net/software/theano/) (Note: The Tensorflow backend doesn't work right now because of a custom layer which is implemented in Theano). 

## Usage


### Training

	python train.py data/stocks

Train the network on all files in `data/stocks`. Each file should contain one time series and look like this: 

	1 2
	3 4
	5 6

Columns are variables (here: 2) and rows are time steps (here: 3). The data is automatically normalized to mean 0 and standard deviation 1. If you want to train on the change of the data from time step to time step (this is recommended for time series that continually in- or decrease, e.g. stock prices), use `--change`. The trained network is saved in `model`. 

Note that the network architecture (namely the Gaussian mixture model layer) is quite prone to numeric errors. If you encounter a `nan` loss during training, try to reduce the learning rate (`--learning_rate VALUE`, default 0.001), use more standard deviations to normalize the data (`--stds VALUE`, default 1), or play around with the number of Gaussians in the mixture distribution (`--mixture_components VALUE`, default 10).

Arguments:

	--epochs EPOCHS                             number of training epochs
	--learning_rate LEARNING_RATE               learning rate of RMSprop
	--layers LAYERS                             number of LSTM layers
	--neurons NEURONS                           number of neurons per LSTM layer
	--mixture_components MIXTURE_COMPONENTS     number of Gaussians in the mixture distribution
	--change                                    use change of data for training (good for cumulative sequences)
	--stds STDS                                 number of standard deviations to normalize the data with


### Prediction

	python predict.py data/stocks

Use the saved model to predict the next values in the time series for all files in `data/stocks`. The predicted time series are stored in the format above in the directory `predicted`. 


### Generation

	python generate.py data/stocks

Use the saved model to generate completely new time series. Parts of the CSV files in `data/stocks` are used as seeds to initialize the network state. The generated time series are stored in the format above in the directory `predicted`. 


## Requirements

- Python 2.7
- keras (v0.3.2)
- Theano (v0.8.0.dev0)
- numpy