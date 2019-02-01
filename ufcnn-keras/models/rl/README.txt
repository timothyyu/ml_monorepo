Scripts for running DeepQLearing for the trading competition data.

Run the training:

python main_deepq.py

grep for Epoch to see the progress of the run...
Epoch 00000/99999 | Loss 1109.0891 | Win trades 0 | Total PnL -2420.7999999999956 
Epoch 00001/99999 | Loss 1091.1115 | Win trades 0 | Total PnL -2496.3999999999833 


Loss is the sum of all the trainigs
Win Count: number of winning trades
Total reward: PnL 


Test the results of an optimization:

python analyze_net.py  NAME_OF_THE_WEIGHTFILES without extension, e.g. 
python analyze_net.py atari_rl_best

You can also look in the epoch line printed every epoch - the rndless PnL is the same as the analysis.



Files:

main_deepq.py       ... Main Program to start the run
Deep.py             ... Training the RL, hyperparameters (at the top)
Trading.py          ... rules for trading, P&L, this is the whole RL-environment
DataStore.py        ... reads and stores the training data from the trading competition. Change this for other input data 
ExperienceReplay.py ... stores known data to send it more than once through the net...
Models.py           ... UFCNN or other neural network to approximate the Q function

analyze_net.py      ... Script to run the net over testing days & calculate the PnL

testDataStore.py    ... Script to test the DataStore.py
Catch.py            ... old Catch game. Not used. Only for reference.

For a good intro into Deep Q Learning, see for instance:

https://www.nervanasys.com/demystifying-deep-reinforcement-learning/


