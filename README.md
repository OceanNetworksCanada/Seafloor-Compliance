# Seafloor Compliance
getToken.py, getBPRScalarData, getSeismicData are scripts that are called from master.py to return (near) concurrent 1 sps BPR and OBS data. 

In getToken.py, a user-specific Token is retrieved from Oceans 2.0 via login credentials and written to disk the first time it is called for subsequent API queries.

In getBPRScalarData.py, ONC API web services are used to download seafloor pressure, uncompensated seafloor pressure, and temperature data for a BPR instrument. When this script is called, the user is asked to enter the station code for the instrument (Location Code in Oceans 2.0) and the starttime of the data query. By defualt, the program returns three hours of data and only the uncompensated seafloor pressure as an ObsPy Stream object, "st_bpr". 

- **Time Corrections**
  
  - The logger clock of the BPR drifts, but is a good reference time because it increments by exactly 1 second, unlike the Shore Station timestamp, which increments at irregular intervals. To circumvent the issue of a drifting logger clock and an irregular Shore Station timestamp, the median difference between the logger and Shore Station times over the three hour time period is found and added to the first logger timestamp of the three hour time period. This "corrected" timestamp is used as the start time for writing the ObsPy Stream object, with all subsequent timestamps incremented by 1 second. The plot parameter can be set to "True" on line 223:  "`df2 = bpr.process(df1, scalardata.params, plot=False)`" to plot the data behind the logic for the time corrections.

- **Data Gaps**

  - Preceding 2018-05-19, the driver at ONC was querying the BPR instrument for its memory size and has not been interpreting the command properly, resulting in a typical loss of 11 samples starting at midnight. As a (catch-all) fix, the code by default implements a linear interpolation, which is intended to interpolate over any encountered data gap. The code will print to terminal the data gaps it has encountered for subseuqent inspection. So far, the memory query data gaps are the only kind we've encountered. As a precaution, the code automatically extends the data query to 1 minute before the requested start time and 1 minute after the 3 hours following the requested start time. 
  
In getSeismicData.py, the IRIS Client is used to request low-rate (8 Hz) broadband seismometer data using the timeseries web service. Upon its first call, the most current StationXML file is downloaded from the ONC repository and written to disk for subsequent use. This file is read in as an ObsPy Inventory object and contains all the metadata for the station in question (including current instrument response information). An ObsPy Stream object (st_obs) is returned with seismic data for the instrument specified, decimated to bring the sampling rate to 1 sps. The decimation operation, by default, includes an anti-aliasing filter, but other than this, no processing has been applied to the data. The attached Inventory (SD.inv) can be used to correct for instrument response and get to geophysical units. 

Besides for making preferential changes the code in the three aforementioned scripts, the user only needs to run master.py to retrieve near concurrent 1 sps BPR and BBS data. There are terminal prompts, as well as the "instrcode" in line 10 of master.py that the user can use to download data for different stations besides the default ('ENWF'). 
