"""
lstmApp
Author: Nicholas Fentekes

Demonstration LSTM model to predict categorical price increases greater than a
specified tolerance from current and past indicators as input.
Dataset must be built by datasetBuild.py or conform to its schema.
"""
import numpy as np
import math
import tensorflow as tf
import pandas as pd
from keras.models import Sequential
from keras.layers import Dense, Embedding, LSTM
from keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import normalize
from math import sqrt
from numpy import concatenate
from pandas import read_csv
from pandas import DataFrame
from pandas import concat
import argparse
pd.options.display.max_columns = 999
y_name = 'CategoricalIncrease'
WEEKLY_TRAIN_PATH   = "data/btcpricetrainingdataweekly2.csv"
WEEKLY_TEST_PATH    = "data/btcpricetestingdataweekly2.csv"
DAILY_TRAIN_PATH    = "data/btcpricetrainingdatadaily2.csv"
DAILY_TEST_PATH     = "data/btcpricetestingdatadaily2.csv"
HR12_TRAIN_PATH     = "data/btcpricetrainingdata12hr2.csv"
HR12_TEST_PATH      = "data/btcpricetestingdata12hr2.csv"
CSV_COLUMN_NAMES = list((pd.read_csv(HR12_TEST_PATH)).columns.values)
CSV_COLUMN_NAMES[0]="Index"
CATEGORICALINCREASE = ['NoIncreaseMoreThanTol', 'IncreaseMoreThanTol']
parser = argparse.ArgumentParser(description='Specify LSTM hyperparameters')
parser.add_argument('-layers', metavar='L', type=int, nargs='+', default=2,
                   help='Number of LSTM layers')
parser.add_argument('-layer_size', metavar='S', type=int, nargs='+', default=75,
                   help='Integer value for the size (numer of neurons) of each LSTM layer')
parser.add_argument('-epochs', metavar='E', type=int, nargs='+', default=250,
                   help="Number of epochs to train")
parser.add_argument('-batch_size', metavar='B', type=int, nargs='+', default=16,
                   help='Batch size to train on')
args = parser.parse_args()

def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
	n_vars = 1 if type(data) is list else data.shape[1]
	df = DataFrame(data)
	cols, names = list(), list()
	for i in range(n_in, 0, -1):
		cols.append(df.shift(i))
		names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
	for i in range(0, n_out):
		cols.append(df.shift(-i))
		if i == 0:
			names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
		else:
			names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
	# put it all together
	agg = concat(cols, axis=1)
	agg.columns = names
	# drop rows with NaN values
	if dropnan:
		agg.dropna(inplace=True)
	return agg

def main(argv):
	#Setup dataset
	dataset = pd.read_csv(HR12_TRAIN_PATH, header=0, index_col=0)
	temp = dataset["SupportLine1"].tolist()
	tempList 	= dataset["SupportLine1"].tolist()
	tempList2	= dataset["SupportLine2"].tolist()
	tempList3	= dataset["SupportLine3"].tolist()
	for i in range(len(tempList)):
		if np.isinf(dataset.iloc[i]["SupportLine1"]):
			tempList[i]	  = tempList[i-1]+dataset["SupportSlope1"].tolist()[i-1]
			tempList2[i]  = tempList[i]
			tempList3[i]  = tempList[i]
	dataset["SupportLine1"]=tempList
	dataset["SupportLine2"]=tempList2
	dataset["SupportLine3"]=tempList3
	trainWeights = []
	for i in range(len(dataset["Close"])-1):
		if(dataset['Close'].tolist()[i]/dataset['Close'].tolist()[i+1]<=0.98):
			trainWeights.append(abs(dataset['Close'].tolist()[i]-dataset['Close'].tolist()[i+1])/dataset['Close'].tolist()[i])
		else:
			trainWeights.append(abs(dataset['Close'].tolist()[i]-dataset['Close'].tolist()[i+1])/dataset['Close'].tolist()[i])
	trainWeights.append(0)
	for i in range(len(trainWeights)):
	    trainWeights[i]=trainWeights[i]/max(trainWeights)*2
	values = dataset.values
	# integer encode direction
	encoder = LabelEncoder()
	values[:,36] = encoder.fit_transform(values[:,36])
	values = values.astype('float64')
	# normalize features
	scaler = MinMaxScaler(feature_range=(0, 1))
	scaled = scaler.fit_transform(values)
	# frame as supervised learning
	reframed = series_to_supervised(scaled, 1, 1)
	# split into train and test sets
	values = reframed.values
	n_train_hours = math.floor(len(dataset["Open"])*0.8)
	train = values[:n_train_hours, :]
	test = values[n_train_hours:, :]
	# split into input and outputs
	train_X, train_y = train[:, :-1], train[:, -1]
	test_X, test_y = test[:, :-1], test[:, -1]
	# reshape input to be 3D [samples, timesteps, features]
	train_X = train_X.reshape((train_X.shape[0], 1, train_X.shape[1]))
	test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))
	trainWeights = np.array(trainWeights[:n_train_hours])
	trainWeights = normalize(trainWeights[:,np.newaxis], axis=0).ravel()
	# design network
	MINIMUMLOSS=20
	history = []
	train_y = [int(y) for y in train_y]
	with tf.device('gpu:0'):
		model1 = Sequential()
		if args.layers==1:
			model1.add(LSTM(args.layer_size, input_shape=(train_X.shape[1], train_X.shape[2]),activation='relu'))
		elif args.layers>1:
			model1.add(LSTM(args.layer_size, input_shape=(train_X.shape[1], train_X.shape[2]),activation='relu',return_sequences=True))
			for i in range(args.layers-1):
				model1.add(LSTM(args.layer_size,activation='relu',return_sequences=True))
			model1.add(LSTM(args.layer_size,activation='relu'))
		model1.add(Dense(1))
		model1.compile(loss='mae', optimizer='adam')
		hist = model1.fit(train_X, train_y, epochs=args.epochs, batch_size=args.batch_size, class_weight={0:1,1:3},sample_weight=trainWeights,validation_data=(test_X, test_y), verbose=1, shuffle=False).history
		# make a prediction
		yhat = model1.predict_classes(x=test_X)
		numberOf1s,numberOf0s = 	0,0
		sum0Correct,sum0Wrong =		0,0
		sum1Correct,sum1Wrong =		0,0
		falseFlagsLoss = 			0
		falseFlagsMissedGain =		0
		gains =						0
		falseFlags1,falseFlags2 = 	0,0
		y, yh = test_y.tolist(),yhat.tolist()
		close = dataset["Close"].tolist()
		close = close[n_train_hours:]
		for i in range(len(yh)):
			if yh[i][0]!=0:
				if y[i]==0:
					falseFlags1+=1
					if i<len(y)-1:
						falseFlagsLoss+=(close[i]-close[i+1])/close[i]
				else:
					gains+=(close[i+1]-close[i])/close[i]
			else:
				if y[i]==1:
					falseFlags2+=1
					if i<len(y)-1:
						falseFlagsMissedGain+=(close[i+1]-close[i])/close[i]
			if y[i]==0:
				if yh[i][0]==0:
					sum0Correct+=1
				else:
					sum0Wrong+=1
				numberOf0s+=1

			else:
				numberOf1s+=1
				if yh[i][0]==1:
					sum1Correct+=1
				else:
					sum1Wrong+=1
		print("lentesty",len(test_y))
		print("nhours",n_train_hours)
		print("Percentage of times 1 was predicted correctly:",sum1Correct/numberOf1s)
		print("Percentage of times 0 was correctly predicted:",sum0Correct/numberOf0s)
		print("Numer of times 1 was predicted when 1 was correct",sum1Correct)
		print("Numer of times 0 was predicted when 1 was correct",sum1Wrong)
		print("Numer of times 0 was predicted when 0 was correct:",sum0Correct)
		print("Numer of times 0 was predicted when 1 was correct:",sum0Wrong)
		print("False Flags1: :",falseFlags1)
		print("falseFlags2: ",falseFlags2)
		print("numberOf1s: ",numberOf1s)
		print('leny',len(y))
		print("falseflags1/leny",falseFlags1/len(y))
		print('totfalse',(falseFlags1+falseFlags2)/len(y))
		print("Total loss %: ",falseFlagsLoss)
		print("Total Missed %: ",falseFlagsMissedGain)
		print("Total Gained %:", gains)

if __name__=='__main__':
	MINIMUMLOSS = 20
	tf.logging.set_verbosity(tf.logging.INFO)
	tf.app.run(main)
