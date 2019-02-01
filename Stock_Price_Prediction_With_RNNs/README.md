# Stock Price Prediction With Reccurent Neural Networks (RNNs)

## Synopsis:
Recurrent Neural Networks with LSTMs are known to be particularly good with temporal data which is why they are effective with speech recognition. Good explanations of RNNs and LSTMs can be found here http://karpathy.github.io/2015/05/21/rnn-effectiveness/ and http://colah.github.io/posts/2015-08-Understanding-LSTMs/.  With Yahoo data reader for daily prices and Google’s API for Intraday Prices we used the Open, Close, High, Low attributes for sequences of 25 to be able to predict the next time periods Close. Each sequence was passed through a Gaussian distribution and the 2 Layer LSTM models were trained on that data. 


## Code Example:
The code is separated into two objectives Forex price prediction daily and Intraday price prediction (30 min, 15 min, 5 min, etc.) The parts of code that attribute to each objective is document A. or B. in the notebook where A is for the Forex and B is for the Intraday prediction.

#### A.	Forex
    a.	Daily Data is pulled from Yahoo’s Data Reader
    b.	Only the training set is preprocessed because we create a separate test set later on
    c.	“model_forex” is the model for to build and train.
    d.	Create separate daily test set by specifying dates which start after your training set ends.
    e.	You can see “model_forex” is plugged in here for running the prediction
        predicted_st = predict_standard(X_test_stock,y_test_stock, model_forex)
####  B.	Intraday
    a.	Intraday Data is pulled from Google’s API. The second argument is the time in seconds (900 secs = 15 mins) and the third                argument it the number of days, the max backtrack day for Googles API is 15 days I believe.
         df = get_google_data(INTRA_DAY_TICKER, 900, 150)
    b.	Preprocess the full set of data and train test split it with “train_test_split_intra”
    c.	“model_intra” is the model for to build and train.
    d.	You can see “model_intra” is plugged in here for running the prediction
        predicted_intra = predict_intra(X_test_intra,y_test_intra, model_intra)

## Motivation:
To test the effectiveness of LSTMs on predicting Stock Market Prices.

## Installation:
Make sure you have Theano, Keras, Numpy, Pandas installed. Training on GPUs is advised.

## Tests:
Tests can be run at the A. Forex and B. Intraday sections. From here you can calculate the predicted value of the following day for each sequence. The results are graphed and MAE and RMSE are calculated. From there a policy function is run for different thresholds and LOT_SIZEs and the returns for following the predictions are graphed.
From the RMSE and MAEs the tests show that for Daily price prediction, Forex stocks are work better, as opposed to general equities, because there seems to be less noise. The Forex market is more controlled by supply and demand making recognition of technical patterns more probably for the model. Because of this, I tested this hypothesis on general equities but for intraday data (15 min, 5min, 3 min intervals) where the same of idea of having more technical factors is present. From the results of this it is shown that LSTMs are also effective in predicting intraday movements for any general equity. Looking at the net profits per trade graph (second graph after the policy evaluation) you can see that as you increase the threshold or confidence of the predicted change, there is a consistent increase in profits per trade. 

## Contributors:
canepunma1@gmail.com
