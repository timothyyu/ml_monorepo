# A3C Trading

Integration of our Trading Framework into [miyosuda's A3C code] (https://github.com/miyosuda/async_deep_reinforce) based on the paper "Asynchronous Methods for Deep Reinforcement Learning" , published in [Arxiv] (https://arxiv.org/abs/1602.01783) by V. Mnih et al.. The implemented algorithms are A3C and A3C LSTM.

Network layout is changed only for LSTM, so A3C FF  is currently not working

The code runs and produces good results for a large Sine curve (Sine_Long.csv).

The File constants.py contains important constants, e.g. use LSTM or not, number of threads, use GPU,.... and needs to be modified.

The jobs run (almost) forever. Only if you stop a job via <CTRL> C (interactive job) or `kill -INT processid` (Job in the background), the program writes data in the checkpoints/ dir that contains all necessary data to restart. Please note that if you change a network parameter in constants.py, you must remove or rename the checkpoints/ directory, otherwise a3c.py might terminate with an error message.

Sine_long.csv must be renamed into prod_data_20130103v.txt and placed in the training_data_large/ directory

To start the optimization, run `python a3c.py`

To view the results of an optimisation on the testing days, run `python Tradingresults.py`. You will need a checkpoint first, and the testing days need to be set in constants.py

## System Requirements

- python 3.2 or later
- TensorFlow
- numpy, pandas, matplotlib, ...


## Restrictions

The system requires sequences of 168 x 4 (that are internally folded into 84 x 8). Features are the features 2,3,4,5 from the input file. 


## TODO

- run it over unseen data
- use other network topolgies
- Fix the network parameters for A3C FF

