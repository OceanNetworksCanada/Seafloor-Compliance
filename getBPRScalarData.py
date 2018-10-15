# -*- coding: utf-8 -*-
"""
Created on Tue Oct 09 13:35:55 2018

@author: mheesema
"""

import requests
from getToken import Token
from requests.exceptions import HTTPError
import pandas as pd
from obspy import UTCDateTime, Stream, Trace
import matplotlib.dates as dates
import numpy as np
import warnings
import matplotlib.pyplot as plt
#get your Oceans 2.0 token
token = Token()

class NoDataError(Exception):
    pass

class ScalarData(object):
    def __init__(self):
        """
        Set up to grab 3 hoursof BPR scalar data using user token.
            -   Grab 1 minute of data on either end to ensure enough data is 
                present to perform the necessary "datafill" method in the 
                subsequent gap check -- ensures continuous data over the 
                3 hours requested
        """
        self.baseurl = 'https://data.oceannetworks.ca/api/scalardata'
        print("---\nDownloading BPR Data")
        locCode = input('\tStation Code: ')
        startDate = UTCDateTime(input('\tStart Date: ')) - 60
        print("---")
        endDate = (startDate + 3*60*60 + 120).strftime('%FT%H:%M:%S.%f')[:-3]+'Z' #take 3 hours and 1 second of data
        startDate = startDate.strftime('%FT%H:%M:%S.%f')[:-3]+'Z'
        
        self.params = {
                'locationCode' : locCode, 
                'deviceCategoryCode' : 'BPR',
                'token' : token, 
                'dateFrom' : startDate, 
                'dateTo' : endDate
                }

    def getByLocation(self,params):
        params['method'] = 'getByLocation'
        r = requests.get(self.baseurl, params=params)
        if not r.ok:
            if not '"errorCode": 23,' in r.text:
                print(r.text)
            raise HTTPError('Could not get by location',r)
        return r

    def getScalar(self, params):
        df_list=[]
        dateFrom = params['dateFrom']
        while dateFrom:
            
            params['dateFrom'] = dateFrom
            try:
                r = scalardata.getByLocation(params)
            except HTTPError as e:
                if not '"errorCode": 23,' in e[1].text:
                    print(e,e[1].url)
                break
            
            j=r.json()
            
            ts_list=[]
            
            try:
                for tseries_json in j['sensorData']:
                    ts_list.append(pd.Series(data=tseries_json['data']['values'], 
                                             index=pd.DatetimeIndex(tseries_json['data']['sampleTimes']), 
                                             name=tseries_json['sensorCode']))
            
                df_list.append(pd.concat(ts_list,axis=1))
                dateFrom = j['next']['parameters']['dateFrom']
            except TypeError as e:
                if j['sensorData'] == None or j['next'] == None:
                    break
                else:
                    print(r.url)
                    raise e
                
        if len(df_list) == 0:
            print(r.url)
            raise NoDataError('Could not find data in time range')
            
        return pd.concat(df_list)

class BPRProcessing():
    def __init__(self):
        self.initdate = UTCDateTime('1970-01-01') #Used to calculate Gregorian days since
        self.utcLogger = []
        self.utcShore = []
        self.deltaShoreLogger = []
    
    def _estimateMSEEDStartTime(self, df):
        """
        Helper function for estimating the BPR MSEED file starttime based on
        shore and logger timestamp differences.
            
        Returns :
            
            md :    The median difference in seconds between the Shore Station 
                    and Logger timestamps
                    
            es :    The estimated starttime of the BPR MSEED file
            
            lt :    The estimated time it takes in seconds for a data packet to 
                    transit from the instrument to the shore station
        
        """
        #estimate MSEED start time
        md = df['deltaSL'].median()
        es = (df['utcLogger'].values[0] + df['deltaSL'].median())
        lt = es - df.index.values[0]
        
        return md, es, lt
    
    def timeCorrection(self, df, params, plot=True):
        """
        Helper function for converting Gregorian Days since January 1, 1970 to 
        UTC and calculate the difference in seconds between the logger and 
        shore station timestamp.
        
        Have the option of plotting shore-logger clock offset to inspect logger 
        clock drift, and show the best estimated MSEED starttime.
        """
        
        #check we are dealing with a BPR
        if "BPR" not in params.values(): raise Warning('calculateTimes intended for BPR time conversion.')
        
        for i, time in enumerate(df['clock'].values):
            utctime = UTCDateTime(dates.num2date(719163.0 + float(time)))
            self.utcLogger.append(utctime)
            _utcShore = UTCDateTime(df.index[i].to_pydatetime())
            self.utcShore.append(_utcShore)
            self.deltaShoreLogger.append(_utcShore - utctime)
        
        df.index = self.utcShore
        df['utcShore'] = self.utcShore
        df['utcLogger'] = self.utcLogger
        df['deltaSL'] = self.deltaShoreLogger
        
        if plot:
            utcShore_mdates = [t.datetime for t in df.index.values]
            
            fig = plt.figure(figsize=(15, 8))
            ax1 = fig.add_subplot(111)
            ax1.plot_date(utcShore_mdates, df['deltaSL'].values, 'o', 
                          alpha=0.5, 
                          markeredgecolor=(1, 0.1, 0.2), 
                          markerfacecolor=(1, 0.1, 0.2))
            
            ax1.set_ylabel('$\Delta$$t$ [Shore - Logger] (sec)')
            ax1.set_xlabel('{}\nShore Station Timestamp [3-hours] (UTC)'.format(df.index.values[0].strftime('%Y-%m-%d')))
    
            md, es, lt = self._estimateMSEEDStartTime(df)
            ax1.plot_date(utcShore_mdates, np.ones_like(utcShore_mdates)*md, 'k--', 
                          linewidth=2, 
                          label='median'.format(lt))
            ax1.legend(loc='upper left')
            
            plt.title('Estimated BPR MSEED Start Time: {}\nShore Timestamp Lagtime (sec): {}'.format(es, lt))
            plt.tight_layout()
        
        return df
    
    def dataGaps(self, df, fillmethod='interpolate'):
        """
        Check for instances of data gaps and issue warnings.
            -   Up to May 2018, data gaps are tyically found at the beginning 
                of the day and 10 seconds in length, which are interpolated 
                ("fillmethod")
        """
        
        gaps = np.where(df['utcLogger'].diff().values[1:] != 1.0)[0]
        if np.size(gaps) != 0:
            #then we found a gap
            print('Found {} gap(s)'.format(len(gaps)))
            for i in gaps:
                warnings.warn('\n\nData gap found between {} and {} [Uncorrected Logger Time in UTC]\n---\nData will be interpolated between these times.\n---'.format(df['utcLogger'].values[i], df['utcLogger'].values[i+1]))
            
            #interpolate the data gaps (create Pandas friendly datetimes)
            pLoggerTimes = [time.datetime for time in df['utcLogger'].values]
            df_inter = pd.DataFrame(data=df['utcShore'].values, index=pLoggerTimes, columns=['utcShore'])
            df_inter['Pressure'] = df['Pressure'].values
            df_inter['Temperature'] = df['Temperature'].values
            df_inter['Uncompensated_Seafloor_Pressure'] = df['Uncompensated_Seafloor_Pressure'].values
            df_inter = df_inter.resample('1S').asfreq()
            df_inter.interpolate(method='linear', inplace=True)
            
            return df_inter
            
            
        #second sanity check        
        elif not (len(df.index.values) - 120)/60/60 == 3.0: 
            raise Exception('{}/10920 samples (3 hrs 2 minutes) were returned for the time range: {} -- {} [Shore Time in UTC].'.format(len(df.index.values), df.index.values[0], df.index.values[-1]))
        else: #no data gaps, everything is fine, phew.
            return df
        
    def process(self, df, params, plot=False):
        df = self.timeCorrection(df, params, plot=plot)
        es = self._estimateMSEEDStartTime(df)[1]
        correctedLoggerTimestamps = pd.DatetimeIndex(start=es.datetime, end=(es+119+60*60*3).datetime, freq='1S')
        df_nogaps = self.dataGaps(df)
        df_corrected = pd.DataFrame(data=df_nogaps['Pressure'].values, index=correctedLoggerTimestamps, columns=['Pressure'])
        df_corrected['Uncompensated_Seafloor_Pressure'] = df_nogaps['Uncompensated_Seafloor_Pressure'].values
        df_corrected['Temperature'] = df_nogaps['Temperature'].values
        df_corrected = df_corrected.truncate(before=(UTCDateTime(scalardata.params['dateFrom'])+60).datetime, after=(UTCDateTime(scalardata.params['dateFrom']) + 61 + 3*3600).datetime)
        return df_corrected

def BPR_Stream():
    """
    Retrieve BPR scalar data, do some processing and return an ObsPy Stream object.
    """
    df1 = scalardata.getScalar(scalardata.params)
    df2 = bpr.process(df1, scalardata.params, plot=False)
    data = df2['Uncompensated_Seafloor_Pressure'].values
    stats = {
            'network' : 'NV',
            'station' : scalardata.params['locationCode'],
            'channel' : 'DS', #S=seafloor
            'sampling_rate' : 1.0,
            'starttime' : UTCDateTime(str(df2.index.values[0]))
            }
    tr = Trace(data=data, header=stats)
    st = Stream(traces=tr)
    return st

scalardata = ScalarData()
bpr = BPRProcessing()
if __name__ == "__main__":
    st = BPR_Stream()
