from TCTData import TCTData
from math_utils import *
import numpy as np

class TCTAnalysis:
    def __init__(self,data):
       
        self._TCTData = data
        pass
    


    def rise_time_extraction(self,coords):

    
        pass


    def fall_time_extraction(self,coords):
    
        pass

    def fit_err_func(self,y=0,z=0):
        j = self._TCTData.nearest_grid_y(y)
        k = self._TCTData.nearest_grid_z(z)

        if self._TCTData.ErrTarget is None:
            self._TCTData.ErrTarget = np.zeros((self._TCTData.header.Ny,self._TCTData.header.Nz,4))
        else:
            pass

        if self._TCTData.ChargeMap is not None:

            V = np.abs(self._TCTData.ChargeMap[:,j,k])
            x = self._TCTData.X[:,j,k]

            # Fitting process
            # --- initial guesses  
            A0 = V.max() - V.min()
            X0_0 = x[np.argmax(np.gradient(V))]
            sigma0 = (x.max() - x.min()) / 20
            C0 = V.min()

            p0 = [A0, X0_0, sigma0, C0]

            # --- fit ---
            popt, pcov = curve_fit( erf_model, x, V, p0=p0,  maxfev=20000)
            
            A, x0, sigma, C = popt
            self._TCTData.ErrTarget[j,k] = A, x0, sigma, C
            perr = np.sqrt(np.diag(pcov))
            
        else:
            print("Charge Map is not defined")



    def charge_map(self,axis=3 ,region=None):

        dt = self._TCTData.header.dt*self._TCTData.header.time_scale
        if region is not None:
            data = self._TCTData.W[:,:,:,region[0]:region[1]]
        else:
            data = self._TCTData.W
        print("Warning... not actual charge map but close...")
        _charge_map = int_methods(method="sum",data = data, dx = dt, axis = axis)

        self._TCTData.ChargeMap = _charge_map

    def max_map(self,axis = 3,region=None):
        if region is not None:
            data = self._TCTData.W[:,:,:,region[0]:region[1]]
        else:
            data = self._TCTData.W
        data[:,:,:] = np.abs(data[:,:,:])
        _max_map = data.max(axis=axis)

        self._TCTData.MaxMap = _max_map

        


    