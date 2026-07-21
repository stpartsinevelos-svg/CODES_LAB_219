import pathlib
import os
from datetime import datetime, timedelta 
import numpy as np
import libximc.highlevel as ximc
import time
import argparse
import logging
logger = logging.getLogger(__name__)
import struct
import sys
import pyvisa
from pyvisa.constants import StopBits, Parity
from time import sleep
#from SerialCom import SerialCom
from tctfw.OscControl.tektronix  import  TektronixMSO


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tctsw_git.stage_control.TCTStage import Stage

from tctfw.TCTData import TCTData
import json

outputPath = "C:/Users/ehep/Desktop/iv_exec/LGADS_TCTboard_IV_Gain" #output path in the oscilloscope
#outputPathOscilloscope = "C:/TCT" #output path in the oscilloscope
signalChannel= "CH3" # the channel connected to the sensor
signalChannel_2 = "CH4"
dosisgnalChannel_2 = False
specialDesc = "V2-2TR-TW2" 
DUT="yscan_SPOT_size"

 
 
   # colorama.init(autoreset=True) #used for colour printing    
def run(pos1, pos2, pos3, channel = "CH3", trigger_level = - 0.020, vertical_scale = 0.02, horizontal_scale = 20e-9, number_avg = 16):

  # channels = ["CH1","CH2","CH3","CH4"]
   axes = {1:"x",2:"y",3:"z"}

   #Set up the MSO64b
   print('Setting up MSO64B.')
   scope = TektronixMSO("USB0::0x0699::0x0530::C064620::INSTR")
   print("reseting scope")
 #  scope.reset_instrument()  
   print("Oscilloscope setup beggins") 
   scope.setup_from_json(r"C:\Users\ehep\tctsw\tctfw\OscControl\Diode.json")
   print("Oscilloscope setup is done")
   scope.get_parameters_scope("ch3")


   logger.setLevel(logging.INFO)

   print("Identfying axis")
   Stage.identify_devices()
   for ax in Stage.axes:
      Stage.devices[ax].open_device()
   Stage.calibration("um")
  
   output_file = os.path.join(outputPath, f"{DUT}_{specialDesc}.np") 
     
   N = np.shape(pos1)
   N_samples=1000
   scope.measurement_functions(Channel=channel)
   TCTData.W = np.zeros((N[0], N[1], N[2], N_samples), dtype=np.int8)
                    
   TCTData.TIME=np.zeros((N[0],N[1],N[2],2))
   TCTData.ChargeMap=np.zeros((N[0],N[1],N[2],1))
   TCTData.MaxMap=np.zeros((N[0],N[1],N[2],1))
   TCTData.X = pos1
   TCTData.Y = pos2
   TCTData.Z = pos3

   #Prints the type of the scan
   scan = []
   for i in range(3):
      if N[i] > 1:
         scan.append(i)
   if len(scan) == 1:
      scan_type = axes[scan[0]+1]
   elif len(scan) == 2:
      scan_type = axes[scan[0]+1]+axes[scan[1]+1]
   elif len(scan) == 3:
      scan_type = axes[scan[0]+1]+axes[scan[1]+1]+axes[scan[2]+1]
   print(f"{scan_type}_Scan")

   for k in range(N[2]):
      for j in range(N[1]):
         for i in range(N[0]):
            position = [pos1[i,j,k],pos2[i,j,k],pos3[i,j,k]]
            Stage.move(position, timestop=500)
            print(f"{i,j,k}: moved to{int(position[0]),int(position[1]),int(position[2])}")
            while any(status & ximc.MvcmdStatus.MVCMD_RUNNING 
               for status in Stage.get_axis_status("MvCmdSts")):
                  pass
            time.sleep(5)
            # print("wait")
            for meas in range(1):
               print("stated measurment")
               scope.control_acquisition("on")
               logger.info(f"Acquisition started at position {position}, meas {meas}")
               time.sleep(2)
      
               scope.oscilloscope.write('ACQ:STATE RUN')

               #scope.busy()
               
               meas_data =scope.measurement_read()
               TCTData.TIME[i,j,k,]=meas_data[2]

               TCTData.MaxMap[i,j,k,]=meas_data[0]
               TCTData.ChargeMap[i,j,k,]=meas_data[1]
               data_waveform = scope.read_waveform_buffer(signalChannel, 1000)
               TCTData.W[i,j,k,]=data_waveform
               print("acquired")
               
               logger.info(f"Saved waveform for position {position}")
               logger.info(f"Saved waveform for position {position}, meas {meas}")

               if dosisgnalChannel_2:
                     filename2 = f"{DUT}.OtherPixels.{position}.{specialDesc}_{meas}"
                     scope.save_to_wfm(filename2, outputPathOscilloscope, signalChannel_2)

   with open(output_file, "wb") as f:

    f.write(f"Scan Type:{scan_type}\n".encode())
    f.write(f"CHANNEL:{signalChannel}\n".encode())
    f.write(b"FORMAT: x y z AMPLITUDE AREA RISETIME FALLTIME waveform\n")

    for k in range(N[2]):
        for j in range(N[1]):
            for i in range(N[0]):

                x = pos1[i,j,k]
                y = pos2[i,j,k]
                z = pos3[i,j,k]

                amplitude = float(TCTData.MaxMap[i,j,k,0])
                area      = float(TCTData.ChargeMap[i,j,k,0])
                waveform = TCTData.W[i,j,k,:]
                print("dtype:", waveform.dtype)
                print("shape:", waveform.shape)
                print("min:", np.nanmin(waveform))
                print("max:", np.nanmax(waveform))
                print("NaNs:", np.isnan(waveform).sum())
                # x,y,z
                f.write(struct.pack("3d", x, y, z))
                # amplitude area risetime falltime
                f.write(struct.pack(
                    "2d",
                    amplitude,
                    area
                ))
                

 
                # waveform
                waveform.tofile(f)

   for ax in Stage.axes:
      Stage.devices[ax].close_device()
                  

def create_position_arrays(p0, p1, N):

   pos1, pos2, pos3 = np.mgrid[p0[0]:p1[0]:N[0],p0[1]:p1[1]:N[1],p0[2]:p1[2]:N[2]]
   return pos1, pos2, pos3


def import_locations(location_file):
   location_array = [[],[],[]]

   with open(location_file) as lf:
      locations = json.load(lf)

      for i in locations["sequence"]:
         location_array[0].append(i["x"])
         location_array[1].append(i["y"])
         location_array[2].append(i["z"])

   return location_array



if __name__ == "__main__":
   pos1, pos2, pos3  = create_position_arrays([-900,1480,-8001],[-899,1541,-8000],[1,2,1])
   print(pos1,pos2,pos3)
   run(pos1,pos2,pos3)
  

#     ps.setup()
#   #  except:
#   #   ERROR('HV SMU setup failed.')
#   #  return 1
#     current_range = psCompliance
#     ps.setCurrentRange(current_range)
#     ps.controlSource('on') #apply voltage
#     print('HV SMU setup successful.') 