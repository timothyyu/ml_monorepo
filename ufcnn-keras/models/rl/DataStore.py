

import numpy as np
import pandas as pd
import os
import glob
import re
import time
import datetime
import itertools


class DataStore(object):
    """ Load and Store Data from the Trading Competition """

    def __init__(self, sequence_length=500, features_list=[1,2,3,4], path='./training_data_large/', training_days=0, testing_days = 0, mean = None, std = None):
        """ 
             if data is already stored in pickle format, read it from dist, otherwise create it 
             path ... where to find the training data to load 
             training_days ... how many days are needed for training
             testing_days  ... how many days are needed for testing, is 0 if only training is used
                   if testing_days <> 0, then test data will be loaded

        """ 
        self.sequence_length = sequence_length
        self.Xdf_array_list = []
        self.XdfBidAsk_array_list = []
        self.Xdf_array_day = []
        self.features_length = len(features_list) + 2 # Bid & Ask get appended onto the features list

        if testing_days == 0: 
            if mean is not None or std is not None:
                print(" When specifiying traiing days only, mean and std must not be given. Aborting.")
                raise ValueError

        if testing_days != 0: 
            if mean is None or std is None:
                print(" When specifiying testing days, mean and std must be given. Aborting.")
                raise ValueError

        ## Are there already files given
        output_file_name = path + "/TradcomSave"+str(training_days)+"_"+str(testing_days)+".pickle" 

        Xdf = pd.DataFrame()

        if os.path.isfile(output_file_name):
            Xdf = pd.read_pickle(output_file_name)
        else:
	    # We need to create the file ourselves...
            file_list = sorted(glob.glob(path+'/prod_data_*v.txt'))

            if len(file_list) == 0:
                print ("Files "+path+"prod_data_*txt are needed. Please copy them into "+path+". Aborting.")
                raise ValueError

            if testing_days != 0: 
                start = training_days
                end = training_days + testing_days
            else:
                start = 0
                end = training_days

            for filename in file_list[start:end]:
                print("Working on Input file: ",filename)

                # get the date...
                r = re.compile('^\D*(\d*)\D*', re.UNICODE)
                date = re.search(r, filename).group(1)
                print("Date is ",date)
                date_ux = time.mktime(datetime.datetime.strptime(date,"%Y%m%d").timetuple())

                # load dataframes and reindex
                Xdf_loc = pd.read_csv(filename, sep=" ", header = None,)

                # print(Xdf_loc.iloc[:3])

                Xdf_loc['Milliseconds'] = Xdf_loc[0]
                Xdf_loc['Date'] = pd.to_datetime(date_ux*1000*1000*1000)
                Xdf_loc = Xdf_loc.set_index(['Date', 'Milliseconds'], append=False, drop=True)
                # print(Xdf_loc.iloc[:3])

                Xdf = pd.concat([Xdf, Xdf_loc])
                #print(Xdf.index[0])
                #print(Xdf.index[-1])


            ## Store all the data in the file
       
            Xdf.to_pickle(output_file_name)


        #select by features_list
        colgroups = [[2, 4], [3, 5]]
        Xdf = Xdf[features_list]
      
        # keep the bid and ask unmodified
        unmodified_group = [2,4]
        self.Xdf, self.mean, self.std = self.standardize_inputs(Xdf, colgroups=colgroups, mean=mean, std=std, unmodified_group=unmodified_group)
        self.XdfBidAsk = self.Xdf[[2,4,'U2','U4']]


        # split the Xdf along the days... 
        #print (self.Xdf)
        for date_idx in self.Xdf.index.get_level_values(0).unique():
            self.Xdf_array_list.append(self.Xdf.loc[date_idx].values)
            self.XdfBidAsk_array_list.append(self.XdfBidAsk.loc[date_idx].values)
            self.Xdf_array_day.append(date_idx)

        ## TODO remove ?
        self.Xdf['U2'] = 0.
        self.Xdf['U4'] = 0.


    def standardize_columns(self, colgroup):
        """
        Standardize group of columns together
        colgroup: Pandas.DataFrame
        returns: Pandas.DataFrames: Colum Group standardized, Mean of the colgroup, stddeviation of the colgroup
        """
        _me = np.mean(colgroup.values.flatten())
        centered = colgroup.sub(_me)
        me = pd.DataFrame(np.full(len(colgroup.columns),_me), index=colgroup.columns)

        _st = np.std(colgroup.values.flatten())
        standardized = centered.div(_st)
        st = pd.DataFrame(np.full(len(colgroup.columns),_st), index=colgroup.columns)

        return standardized, me, st

    def standardize_inputs(self, Xdf, colgroups=None, mean=None, std=None, unmodified_group=None):
        """
        Standardize input features.
        Groups of features could be listed in order to be standardized together.
        Xdf: Pandas.DataFrame
        colgroups: list of lists of groups of features to be standardized together (e.g. bid/ask price, bid/ask size)
        returns Xdf ...Pandas.DataFrame, mean ...Pandas.DataFrame, std ...Pandas.DataFrame
        """

        new_unmod_group = []
        for unmod in unmodified_group:
           # copy the unmodified column group
           new_name = 'U'+str(unmod)
           Xdf[new_name] = Xdf[unmod]
           new_unmod_group.append(new_name)

        df = pd.DataFrame()
        me = pd.DataFrame()
        st = pd.DataFrame()

        for colgroup in colgroups:
            _df,_me,_st = self.standardize_columns(Xdf[colgroup])
            # if mean & std are given, do not multiply with colgroup mean
            if mean is not None and std is not None:
                _df = Xdf[colgroup]

            df = pd.concat([df, _df], axis=1)
            me = pd.concat([me, _me])
            st = pd.concat([st, _st])
    
        #     _temp_list = list(itertools.chain.from_iterable(colgroups))

        separate_features = [col for col in Xdf.columns if col not in list(itertools.chain.from_iterable(colgroups))]

        if mean is None and std is None:
            _me = Xdf[separate_features].mean()
            _me[new_unmod_group] = 0.
            _df = Xdf[separate_features].sub(_me)
            _st = Xdf[separate_features].std()
            _st[new_unmod_group] = 1.
            _df = _df[separate_features].div(_st)
            
        else:
            _df = Xdf[separate_features]

        df = pd.concat([df, _df], axis=1)
        me = pd.concat([me, _me])
        st = pd.concat([st, _st])
    
        me = pd.Series(me[0])
        st = pd.Series(st[0])

        if mean is not None and std is not None:
            mean[new_unmod_group] = 0.
            std[new_unmod_group] = 1.

            df = df.sub(mean)
            df = df.div(std)

        return df, me, st


    def get_number_days(self):
        """
        number of days
        """
        return len(self.Xdf_array_list)

    def get_day_length(self, day_index=0):
        """
        Find out how many index entries are available for this day
        """
        arr = self.Xdf_array_list[day_index]
        return len(arr)

    def get_sequence(self, day_index=0, line_id=None):
        """
        get the last sequence_length elements from the Xdf by the index id
        """
        #return self.Xdf.ix[id-self.sequence_length:id].values
        if day_index > len(self.Xdf_array_list):
            raise ValueError
        arr = self.Xdf_array_list[day_index]
        return arr[line_id-self.sequence_length+1:line_id+1]

    def get_bid_ask(self, day_index=0, line_id = None):
        """ 
        returns Bid normalized, Bid, Ask normalized, Ask
        """ 
    
        arr = self.XdfBidAsk_array_list[day_index]
        return arr[line_id][0], arr[line_id][2], arr[line_id][1], arr[line_id][3]

    def get_day(self, day_index=0):
        """
        get the last sequence_length elements from the Xdf by the index id
        """
        return self.Xdf_array_day[day_index]

    def get_features_length(self):
        return self.features_length 
