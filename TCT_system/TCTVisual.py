import matplotlib.pyplot as plt
import numpy as np
from math_utils import *

class TCTVisual:
    def __init__(self,data):
        self._TCTData = data
        pass

    # private functions
    def _plot_in_time(self,i,j,k):
        # For time reconstruction
        start = self._TCTData.header.t0
        dt = self._TCTData.header.dt
        NP = self._TCTData.header.NP
        stop = start + dt*NP
        # data
        waveform =  self._TCTData.W[i,j,k]
        t = np.linspace(start,stop,NP)
        plt.plot(waveform)

   
    def _plot_in_space(self,x,y):
        # For time reconstruction
        plt.plot(x,y)

    # public functions 
    def plot_err_func(self,y,z):
        
        j = self._TCTData.nearest_grid_y(y)
        k = self._TCTData.nearest_grid_z(z)
        if self._TCTData.ChargeMap is not None:
            
            _err_data = np.abs(self._TCTData.ChargeMap[:,j,k])
            plt.plot(self._TCTData.X[:,j,k],_err_data)
            if self._TCTData.ErrTarget is None or self._TCTData.ErrTarget[j,k,:].sum() ==0:
                print("Error fit data not found")
            else:
                _x_err_fit = np.linspace(self._TCTData.X[0,j,k],self._TCTData.X[-1,j,k],1000)
                print(self._TCTData.ErrTarget[j,k])
                _y_err_fit = erf_model(
                    x = _x_err_fit, 
                    A = self._TCTData.ErrTarget[j,k,0],
                    x0 = self._TCTData.ErrTarget[j,k,1],
                    sigma = self._TCTData.ErrTarget[j,k,2],
                    C = self._TCTData.ErrTarget[j,k,3])
                plt.plot(_x_err_fit,_y_err_fit)

        else:
            print("Charge Map is not defined")
        pass


    def plot_from_coords(self,i,j,k):
        
        self._plot_in_time(i,j,k)

    
    def plot_from_position(self,x,y,z):

        i,j,k = self._TCTData.nearest_grid_point(x,y,z)
        self._plot_in_time(i,j,k)
    


    # CONTOUR PLOTING
    def contour_plot_planar(self,k, repr = "charge", x_region = None,y_region=None):
        if x_region is not None:
            x_start = self._TCTData.nearest_grid_x(x_region[0])
            x_stop = self._TCTData.nearest_grid_x(x_region[1])
            if x_stop - x_start <= 1:
                print("Minimum x region")
                x_start = 0
                x_stop = -1    
        else:
            x_start = 0
            x_stop = -1

        
        if y_region is not None:
            y_start = self._TCTData.nearest_grid_y(y_region[0])
            y_stop = self._TCTData.nearest_grid_y(y_region[1])
            if y_stop-y_start <= 1:
                print("Minimum y region")
                y_start = 0
                y_stop = -1    
        else:
            y_start = 0
            y_stop = -1

        match repr:
            case "charge":
                if self._TCTData.ChargeMap is not None:
                    
                    _surface = self._TCTData.ChargeMap[x_start:x_stop,y_start:y_stop,k]
                    cs = plt.contourf(self._TCTData.X[x_start:x_stop,y_start:y_stop,k], self._TCTData.Y[x_start:x_stop,y_start:y_stop,k],_surface)
                    plt.colorbar(cs)

                else:
                    print("Charge Map is not defined")
            case "max":
                if self._TCTData.MaxMap is not None:
                    
                    _surface = self._TCTData.MaxMap[x_start:x_stop,y_start:y_stop,k]
                    cs = plt.contourf(self._TCTData.X[x_start:x_stop,y_start:y_stop,k], self._TCTData.Y[x_start:x_stop,y_start:y_stop,k],_surface)
                    plt.colorbar(cs)

                else:
                    print("Max Map is not defined")
            case _ :
                print("unknown representation") 

    def contour_plot_transverse_xz(self,j, repr = "charge", z_region = None,x_region=None):
        if z_region is not None:
            z_start = self._TCTData.nearest_grid_z(z_region[0])
            z_stop = self._TCTData.nearest_grid_z(z_region[1])
            if z_stop - z_start <= 1:
                print("Minimum z region")
                z_start = 0
                z_stop = -1    
        else:
            z_start = 0
            z_stop = -1

        
        if x_region is not None:
            x_start = self._TCTData.nearest_grid_x(x_region[0])
            x_stop = self._TCTData.nearest_grid_x(x_region[1])
            if x_stop-x_start <= 1:
                print("Minimum x region")
                x_start = 0
                x_stop = -1    
        else:
            x_start = 0
            x_stop = -1

        match repr:
            case "charge":
                if self._TCTData.ChargeMap is not None:
                    
                    _surface = self._TCTData.ChargeMap[x_start:x_stop,j,z_start:z_stop]
                    cs = plt.contourf(self._TCTData.X[x_start:x_stop,j,z_start:z_stop], self._TCTData.Z[x_start:x_stop,j,z_start:z_stop],_surface)
                    plt.colorbar(cs)

                else:
                    print("Charge Map is not defined")
            case "max":
                if self._TCTData.MaxMap is not None:
                    
                    _surface = self._TCTData.MaxMap[x_start:x_stop,j,z_start:z_stop]
                    cs = plt.contourf(self._TCTData.X[x_start:x_stop,j,z_start:z_stop], self._TCTData.Z[x_start:x_stop,j,z_start:z_stop],_surface)
                    plt.colorbar(cs)

                else:
                    print("Max Map is not defined")
            case _ :
                print("unknown representation") 

    def contour_plot_transverse_yz(self,i, repr = "charge", z_region = None, y_region=None):
        if z_region is not None:
            z_start = self._TCTData.nearest_grid_z(z_region[0])
            z_stop = self._TCTData.nearest_grid_z(z_region[1])
            if z_stop - z_start <= 1:
                print("Minimum z region")
                z_start = 0
                z_stop = -1    
        else:
            z_start = 0
            z_stop = -1

        
        if y_region is not None:
            y_start = self._TCTData.nearest_grid_y(y_region[0])
            y_stop = self._TCTData.nearest_grid_y(y_region[1])
            if y_stop-y_start <= 1:
                print("Minimum y region")
                y_start = 0
                y_stop = -1    
        else:
            y_start = 0
            y_stop = -1

        match repr:
            case "charge":
                if self._TCTData.ChargeMap is not None:
                    
                    _surface = self._TCTData.ChargeMap[i, y_start:y_stop,z_start:z_stop]
                    cs = plt.contourf(self._TCTData.Y[i,y_start:y_stop,z_start:z_stop], self._TCTData.Z[i,y_start:y_stop,z_start:z_stop],_surface)
                    plt.colorbar(cs)

                else:
                    print("Charge Map is not defined")
            case "max":
                if self._TCTData.MaxMap is not None:
                    
                    _surface = self._TCTData.MaxMap[i,y_start:y_stop,z_start:z_stop]
                    cs = plt.contourf(self._TCTData.Y[i,y_start:y_stop,z_start:z_stop], self._TCTData.Z[i,y_start:y_stop,z_start:z_stop],_surface)
                    plt.colorbar(cs)

                else:
                    print("Max Map is not defined")
            case _ :
                print("unknown representation") 

    def surface_plot():
        pass