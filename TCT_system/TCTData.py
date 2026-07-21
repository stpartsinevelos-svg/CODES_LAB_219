from dataclasses import dataclass, field
import numpy as np
from typing import Optional


@dataclass
class TCTHeader:
    # Header Extraction part 
    # TODO fix the datatypes and the Optionals and add necessary features

    file_type: int
    date: np.datetime64
    x0: float
    y0: float
    z0: float
    dx: float
    dy: float
    dz: float
    Nx: int
    Ny: int
    Nz: int
    Nxyz: int
    channels: tuple
    Nchannels: int
    offset: int
    NU1: int
    U1: np.ndarray
    NU2: int
    U2: np.ndarray
    t0: float
    dt: float
    NP: int

    # Optionals
    T: Optional[float] = None
    source: Optional[str] = None
    user: Optional[str] = None
    sample: Optional[str] = None
    comment: Optional[str] = None
    
    # User added
    time_scale: Optional[float] = 1e-9
    



@dataclass
class TCTData:

# This is valid for the Particulars DAQ system

    # DO NOT MODIFY
    # ===========================
    header:TCTHeader
    # Optionals  
    X: Optional[np.ndarray]=None
    Y: Optional[np.ndarray]=None
    Z: Optional[np.ndarray]=None
    W: Optional[np.ndarray]=None
    raw: Optional[list]=None
    cube: Optional[np.ndarray]=None
    # ===========================
    ChargeMap:Optional[np.ndarray]=None
    MaxMap:Optional[np.ndarray]=None
    TIME:Optional[np.ndarray]=None
    ErrTarget: Optional[np.ndarray]=None

    # Add a check here!!!!

    def r(self, i: int, j: int, k: int) -> np.ndarray:
        """Return space vector r = (x, y, z) at grid index (i, j, k)."""
        return np.array([self.X[i, j, k],
                         self.Y[i, j, k],
                         self.Z[i, j, k]], dtype=float)
    

    # Add min max check for out of bounds indexes
    def nearest_grid_point(self,x,y,z):

        i = np.abs(self.X[:,0,0] - x).argmin()
        j = np.abs(self.Y[0,:,0] - y).argmin()
        k = np.abs(self.Z[0,0,:] - z).argmin()

        return np.array([i,j,k],dtype=np.int32)

    def nearest_grid_x(self,x):
        i = np.abs(self.X[:,0,0] - x).argmin()
        return i

    def nearest_grid_y(self,y):
        j = np.abs(self.Y[0,:,0] - y).argmin()
        return j

    def nearest_grid_z(self,z):
        k = np.abs(self.Z[0,0,:] - z).argmin()
        return k

    def grid_limits(self):
        print("X limits: ",self.X[:,0,0].min(),",",self.X[:,0,0].max())
        print("Y limits: ",self.Y[0,:,0].min(),",",self.Y[0,:,0].max())
        print("Z limits: ",self.Z[0,0,:].min(),",",self.Z[0,0,:].max())

    