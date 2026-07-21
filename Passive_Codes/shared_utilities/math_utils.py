import numpy as np
from numpy import trapezoid
from scipy.optimize import curve_fit
from scipy.special import erf

def filter():
    pass 

def int_methods(method = "trapz",**kwargs):

    match method:
        case "trapz":
            
            return trapezoid(y = kwargs["data"],dx = kwargs["dx"],axis=kwargs["axis"])
        
        case "sum":
            
            return kwargs["data"].sum(axis = kwargs["axis"])*kwargs["dx"]
            

        case _ :
            print("UNKNOWN METHOD") 


def erf_model(x, A, x0, sigma, C):

    return A * 0.5 * (1 + erf((x - x0) / (np.sqrt(2) * sigma))) + C


def intensity_measurment():
    pass
