# -*- coding: utf-8 -*-
"""
Created on Wed Oct 10 08:10:50 2018

@authors: jfarrugia and mheesema
"""

import requests
import re
import tkinter as tk
from appdirs import user_data_dir
import os
root = tk.Tk()  

def Token():
    global tokenpath
    tokenpath = user_data_dir("ONC-Token", "ONC")
    if os.path.exists(tokenpath + r"\token.txt"):
        print("Token file exists.")
        f = open(tokenpath + r"\token.txt", "r")
        token = f.read()
        f.close()
        return token
    
    else:
        if not os.path.isdir(tokenpath): 
            print("Retrieving new token.")
            NewToken(root)
            root.mainloop() 
            token = NewToken.get_token()
            return token

class NewToken():
    """
    A class to handle login credentials for Oceans 2.0:
        Retrieves user token for API data download.
    """
    def __init__(self, master):
        
        global email, password
        tk.Label(master, text='E-Mail: ').grid(row=0)
        tk.Label(master, text='Password: ').grid(row=1)
        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master, show='*')
        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        enter_button = tk.Button(master, text='Enter', command=self.enter)
        enter_button.grid(row=2, columnspan=2, sticky="WNES")
        email = ""
        password = ""
        
    def enter(self):
        """
        Button. Close the current app and assign e-mail and password global variables.
        """
        global email, password
        email = self.e1.get()
        password = self.e2.get()
        root.destroy() #delete Frame to continue

    def get_token():  
        """
        Return the user specific token for API data download.
        """
        s = requests.Session()
        loginURL = 'https://data.oceannetworks.ca/Login'
        payload = {
                'email' : email, 
                'password' : password, 
                'submit' : 'Login', 
                'action' : 'login'
                }
        r = s.post(loginURL, data=payload)
        r = s.get('https://data.oceannetworks.ca/Profile')
        try: 
            token=str(re.findall('<span id="generated_token">(.*)</span>',r.text)[0])
        except IndexError as e:
            print('Incorrect e-mail and/or password.\n\n', e)
            
        #create directory and store token in file
        os.makedirs(tokenpath)
        f = open(tokenpath + r"\token.txt", "w+")
        f.write(token)
        f.close()
        
        return token
    
if __name__=='__main__':
    token = Token()