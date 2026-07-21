import os
import struct
import logging
import itertools
from datetime import datetime
from TCTData import TCTData
import numpy as np
import matplotlib.pyplot as plt



class TCTWaveform:
    def __init__(self,data):
        
        self.TCTData=data
        pass


    def truncate(self,start = 180,stop=250):
        self.TCTData.W = self.TCTData.W[:,:,:,start:stop]
        pass
    
    def rise_time(self):
        pass
    
    def baseline_correction(self):
        pass

    def filter_correction(self):
        pass