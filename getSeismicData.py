# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 09:54:53 2018

@author: jfarrugia
"""
from getBPRScalarData import *
import requests
from appdirs import user_data_dir
from obspy import read_inventory, Stream
from obspy.clients.iris.client import Client
client = Client()
client.timeout = 100
import os
st_bpr = BPR_Stream()

class SeismicData():
    
    def __init__(self):
        """
        Returns a Stream object with near concurrent low-rate (8 Hz) seismic 
        data to that of st_bpr. 
        
             - self.inv contains the instrument response information for the OBS
        """
        self.invURL = 'https://github.com/OceanNetworksCanada/ONC_StationXML/raw/master/NV_StationXML.xml'
        self.invpath = user_data_dir("ONC-Inventory", "ONC")
        self.r = requests.get(self.invURL)
        try:
            self._inv = read_inventory(self.invpath + r"\NV_StationXML.xml")
        except:
            os.makedirs(self.invpath)
            print("Writing StationXML to {} for future use.".format(self.invpath))
            open(self.invpath + r"\NV_StationXML.xml", "w").write(self.r.text)
            self._inv = read_inventory(self.invpath + r"\NV_StationXML.xml")
        
    def timeseries(self, instrcode="NV.ENWF..MH?"):
        network = instrcode.split('.')[0]
        station = instrcode.split('.')[1]
        location = instrcode.split('.')[2]
        channels = instrcode.split('.')[3]
        self.inv = self._inv.select(station=station, location=location, channel=channels)
        chans = []
        for c in ['E', 'N', 'Z']:
            chans.append(channels[:2] + c)
        # An anti-alias (low-pass) filter is applied when decimation is called.
        print("---\nDownloading Seismic Data.")
        st_obs = Stream()
        for channel in chans:
            st = client.timeseries(network=network, 
                                   station=station, 
                                   location=location, 
                                   channel=channel, 
                                   starttime=str(st_bpr[0].stats.starttime), 
                                   endtime=str(st_bpr[0].stats.endtime + 1.0),
                                   filter=["decimate=1.0"])
            for tr in st:
                st_obs.append(tr)
                
        print("---")
        return st_obs

SD = SeismicData()

if __name__ == "__main__":
    st_obs = SD.timeseries(instrcode="NV.ENWF..MH?")