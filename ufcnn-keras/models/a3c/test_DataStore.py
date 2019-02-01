from DataStore import DataStore

# U3 ... is the unmodified column 3. Works only because 3 is in the unmodified list (see FDAXDataStore.py, search for unmodified_group)
# features_list is the list of features to extract from the input
# TODO: the Input for the unmodified group and where bid and ask are located should be added here also
#d = DataStore(sequence_length=500, features_list=[1,2,'U3',4,5,6,7], path='./training_data_large/', filenames="/FDAX_*.csv", colgroups=[[1,4,6],[5,7]], unmodified_group=[3,4,6], bid_col=4, ask_col=6, training_days=1, testing_days=0, debug=True)
d = DataStore(sequence_length=500, training_days=1, testing_days=0, debug=True)



