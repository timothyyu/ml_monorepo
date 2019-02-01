import DataStore as ds

features_list = list(range(1,33))  ## FULL
training_store = ds.DataStore(training_days=10, features_list=features_list)
print("XDF : ",training_store.Xdf)
print("XDF-len : ",training_store.Xdf.count())
print("STD : ",training_store.std)
print("Mean: ",training_store.mean)

print("XDF Mean: ",training_store.Xdf.mean())
print("XDF Std : ",training_store.Xdf.std())

testing_store = ds.DataStore(training_days=10, testing_days=20, features_list=features_list, mean=training_store.mean, std=training_store.std)
print("Test XDF: ",testing_store.Xdf)
print("Test XDF Mean: ",testing_store.Xdf.mean())
print("Test XDF Std : ",testing_store.Xdf.std())


print("A Sequence ",testing_store.get_sequence(1,700))


numdays = testing_store.get_number_days()
for i in range(1, numdays):
   print("Day ",i,", ", testing_store.get_day(i), ", Elements: ",testing_store.get_day_length(i))

print("TESTING GET SEQ")
print (testing_store.get_sequence(3,888))


print("ERROR: ",training_store.get_bid_ask(7,662))

