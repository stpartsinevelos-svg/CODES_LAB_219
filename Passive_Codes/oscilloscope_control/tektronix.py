"""Module for controlling the Tektronix 4/5/6 series MSO

This should work for:
4 Series MSO (MSO44, MSO46, MSO44B, MSO46B)
5 Series MSO (MSO54, MSO56, MSO58, MSO54B, MSO56B,
MSO58B, MSO58LP)
6 Series MSO (MSO64, MSO64B, MSO66B, MSO68B)
6 Series Low Profile Digitizer (LPD64)

Test by executing the script with the IP address of the oscilloscope:
$ python osccontrol.py -ip <ip_address>
"""
import os
import argparse
import logging  
import logging
import sys
logger = logging.getLogger(__name__)
import pyvisa
from pyvisa.constants import StopBits, Parity
from time import sleep
#from SerialCom import SerialCom
import numpy as np
import time
import json
import math



 #USB0::0x0699::0x0530::C064620::INSTR

class TektronixMSO:
    """Control of oscilloscope."""

    def __init__(self, portname,identify=True, baudrate=9600, timeout=5000):

        if "USB0" in portname and "::INSTR" in portname:
            # VISA instrument
            rm = pyvisa.ResourceManager()
            self.oscilloscope = rm.open_resource(portname)
            self.oscilloscope.timeout = timeout
            self.oscilloscope.timeout = 60000
            self.verbose = True
            if identify:
                print("Success")
                print(self.oscilloscope.query("*IDN?"))
        else:
                print('nein')
                #self.oscilloscope = SerialCom(portname,baudrate=baudrate,timeout=0.5)
    

    def close_connection(self):
        """
        Docstring for Close_connection
        Closing connection with the oscilloscope
        :param self: Description
        """
        self.oscilloscope.close()
        logger.info("Oscilloscope Connection closed")
            

        
    # General Functions group
    def reset_instrument(self):
        """
        Clear errors and reset the instrument.
        
        Args:
            None
        
        Returns:
            None
        """
        logger.info("Clearing errors and reset instrument..")
        self.oscilloscope.write("*CLS")  # Clear any existing errors
        self.oscilloscope.write("*RST")  # Reset the instrument
        Channels=["CH1","CH2","CH3","CH4"]
        for channel in Channels:
         self.oscilloscope.write(f"SEL:{channel} {"off"}")
        if self.verbose:
            print("Reset Succesfull")
        

    def interpret_status_byte(self, status_byte):
        """
        Interpret the status byte from the oscilloscope.
        
        Args:
            status_byte (int): The status byte to interpret.
        
        Returns:
            list: A list of status messages.
        """
        status_bits = {
            7: "PON (Power On)",
            6: "URQ (User Request)",
            5: "CME (Command Error)",
            4: "EXE (Execution Error)",
            3: "DDE (Device Error)",
            2: "QYE (Query Error)",
            1: "RQC (Request Control)",
            0: "OPC (Operation Complete)"
        }

        status_messages = []
        for bit in range(8):
            if status_byte & (1 << bit):
                status_messages.append(status_bits[bit])
                if not bit==7:
                    logger.debug("%s", status_bits[bit])

        return status_messages

    def control_channel(self, state, channel="CH3"):
        if state=="on":
            print('enabling channel')
            self.oscilloscope.write(f"SEL:{channel} {state}")
        elif state== "off" :
            print("disabling  channel")
            self.oscilloscope.write(f"SEL:{channel} {state}")
     
    def check_status(self):
        """
        Checks the status reported by the instrument.

        Args:
            None

        Returns:
            str: The status message
        """
        status_byte = int(self.oscilloscope.query("*ESR?"))
        logger.debug("Oscilloscope status_byte: %s", status_byte)
        logger.debug("Oscilloscope status: %s", self.interpret_status_byte(status_byte))

        return status_byte
     
    # Trigger Group Functions

    def set_acquisition_count(self, count):
        """
        Set the number of acquisitions.
        
        Args:
            count (int): The number of acquisitions to set.
        
        Returns:
            None
        """
        self.oscilloscope.write(f'ACQ:SEQ:NUMSEQ {count}')
        logger.info('Number of acquisitions set to %s.', count)

    def set_trigger(self, level, source='CH3', edge='RIS'):
        """
        Set the trigger settings for the oscilloscope.
        
        Args:
            level (float): Trigger level in volts.
            source (str): Trigger source (e.g., 'CH3').
            edge (str): Trigger edge ('RIS' for rising, 'FALL' for falling, 'EIT' for either).
        
        Returns:
            None
        """
        self.oscilloscope.write(f'TRIG:A:EDGE:SOU {source}')
        self.oscilloscope.write(f'TRIG:A:EDGE:SLO {edge}')
        self.oscilloscope.write('TRIG:A:MOD Auto')
        self.oscilloscope.write(f'TRIG:A:HOLD:TIM {20e-9}')
        self.oscilloscope.write(f'TRIG:A:LEV:{source} {level}')

        logger.info('Trigger set to %s at level %s with %s edge.', source, level, edge)

    # Acquisition Group Functions
    def acquisition_mode(self,mode,num_avg=16,num_env=False, sample_rate=None, fast_frame=False, highres_filter=None):
        """
        determines the acquisition mode
        Parameters:
        input : the mode {SAMple|PEAKdetect|HIRes|AVErage|ENVelope }
        num_avg (int): number of waveforms for AVErage mode
        num_env (int): number for  Envelope/Peak Detect
        sample_rate (float):   sample rate
        highres_filter (str|None): filter for  High Res
        """
        match mode.upper():
            case "SAMPLE" | "SAM":
                self.oscilloscope.write("ACQ:MOD SAM")

            case "PEAKdetect" | "PEAK":
                self.oscilloscope.write("ACQ:MOD PEAK")
                self.oscilloscope.write(f"ACQ:NUMENV {num_env}")

            case "HIRes" | "HIR":
                self.oscilloscope.write("ACQ:MOD HIR")
                self.oscilloscope.write(f"ACQ:FILT {highres_filter}")

            case "AVErage" | "AVE":
                self.oscilloscope.write("ACQ:MOD AVE")
                self.oscilloscope.write(f"ACQ:NUMAVG {num_avg}")
                number_of_acq=self.oscilloscope.query("ACQuire:NUMACq?")
                print(number_of_acq)
                waveform=self.oscilloscope.query("ACQuire:NUMAVg?")

            case "ENVelope" | "ENV":
                self.oscilloscope.write("ACQ:MOD ENV")

            case _:
                raise ValueError(f"Invalid acquisition mode: {mode}")

    def acquisition_setup():
        pass

    def fastframe_control(self,state, number_of_frames=False,count=False):
        """
        Turns off the "Enable Acquisition History" and "Visual Trigger" modes such
        that the oscilloscope can be used in FastFrame mode. Then enable fast frame
        mode for number_of_frames. Please note that there is a maximum frame count 
        so where this is important also use number_fastFrames_taken
        
        Inputs:
            number_of_frames (int).
            state ,on for enabling it and off  for disabling it
        """
        if state == "on" :
            self.oscilloscope.write('HORIZONTAL:HISTORY:STATE OFF') # Disable "Enable Acquisition History"
            self.oscilloscope.write('VISUAL:ENABLE OFF') # Disable visual trigger

            self.oscilloscope.write('HORIZONTAL:FASTFRAME:STATE ON')
            self.oscilloscope.write('HORIZONTAL:FASTFRAME:COUNT {}'.format(number_of_frames))
            self.oscilloscope.write('ACQ:STOPAFTER SEQUENCE')
            self.oscilloscope.write('ACQ:STATE RUN')
             
    
                # Turn on overlay mode so that all frames can be seen
            self.oscilloscope.write(':HORizontal:FASTframe:MULtipleframes:MODe OVERlay')   

            logger.info('FastFrame mode enabled.')
        elif state == "off":
            self.oscilloscope.write('HORIZONTAL:FASTFRAME:STATE OFF')
            number_of_frames=0
            logger.info('FastFrame mode disabled.')

    def number_fastFrames_taken(self):
        """
        Docstring for number_fastFrames_taken
        
        Inputs:
        None
        Return:
        Number of fast frames taken
        :param self: Description
        """
        logger.info('Number off fastframes taken are')
        return int(self.oscilloscope.read('ACQUIRE:NUMFRAMESACQUIRED?'))
    
    def control_acquisition(self,mode):

        match mode.upper():

            case "ON" :
                self.oscilloscope.write('ACQ:STATE RUN')
                logger.info('Acquisition started.')
            case "OFF" :
                self.oscilloscope.write('ACQ:STATE STOP')
                logger.info('Acquisition stopped.')
    
    
    # High level functions

    def set_horizontal(self, scale, position):
        """
        Set the horizontal scale and position.
        
        Args:
            scale (float): The horizontal scale.
            position (float): The horizontal position.
        
        Returns:
            None
        """
        self.oscilloscope.write(f'HOR:MOD:SCA {scale}')
        self.oscilloscope.write(f'HOR:POS {position}')

    def trigger_search(self):
 

    # Start from high trigger
      self.set_trigger(0.7)

      time.sleep(1)

      for trigger_mv in range(600, 6, -1):

        trigger_v = trigger_mv / 1000.0

        # Set trigger level FIRST
        self.set_trigger(trigger_v)

        # Start acquisition
        self.oscilloscope.write('ACQ:STATE RUN')

        # Wait for acquisition
        time.sleep(0.5)

        # Read trigger state
        state = self.oscilloscope.query('TRIG:STATE?').strip()

        print(f"Testing trigger = {trigger_v:.3f} V -> {state}")

        # Trigger found
        if state == "TRIG":

            print(f"Trigger found at {trigger_v:.3f} V")

            # Keep this trigger level
            self.set_trigger(trigger_v)

            return trigger_v

        print("No trigger found")

      return None
    

    def trigger_search_binary(self):
      self.set_trigger(0.7)
      time.sleep(1)

      tr_maxV_mV  = 300
      tr_minV_mV  = 5
      tr_lastV_mV = 0
      tr_curV_mV  = tr_maxV_mV
      tr_V = tr_curV_mV / 1000.0
      
      state = "NO STATE"

      # IMPLEMENT BINARY SEARCH
      while ((state != "TRIG") or (abs(tr_lastV_mV - tr_curV_mV) != 1)) and (tr_curV_mV > tr_minV_mV):
        self.set_trigger(tr_V)
        self.oscilloscope.write('ACQ:STATE RUN')
        time.sleep(1)
        state = self.oscilloscope.query('TRIG:STATE?').strip()
        
        temp = tr_curV_mV
        if state == "TRIG":
          tr_curV_mV = tr_curV_mV + math.ceil( abs(tr_curV_mV - tr_lastV_mV) / 2 )
        else:
          tr_curV_mV = tr_curV_mV - math.ceil( abs(tr_curV_mV - tr_lastV_mV) / 2 )
        
        tr_lastV_mV = temp
        print(f"Testing trigger = {tr_V:.3f} V -> {state}")

        tr_V = tr_curV_mV / 1000.0


      if(tr_curV_mV < tr_minV_mV):
        tr_curV_mV = tr_minV_mV
        tr_V = tr_curV_mV / 1000.0
        print(f"Using minimum trigger voltage of {tr_V:.3f} V")

      print(f"Trigger found at {tr_V:.3f} V")
      self.set_trigger(tr_V)                         # Keep this trigger level
      return tr_V

     
    def set_vertical(self, scale, position, invert,source, term=50):
        """
        Set the vertical scale, position, and termination.
        
        Args:
            scale (float): The vertical scale.
            position (float): The vertical position.
            invert (bool): Inverts the signal.
            term (int, optional): The termination resistance.
        
        Returns:
            None
        """
        self.oscilloscope.write(f'{source}:SCA {scale}')
        self.oscilloscope.write(f'{source}:TER {term}')
        self.oscilloscope.write(f'{source}:POS {position}')
        if invert=="ON":
            logger.warning(f"Inverting signal on {source}!")
        self.oscilloscope.write(f'{source}:INV {invert}')

   
  
    
    def set_vis_trigger(self):

        """
        Set the visual trigger settings for the oscilloscope.
        Note: this is a very specific configuration for the SiC project.
        
        Args:
            None
        
        Returns:
            None
        """
        self.oscilloscope.write('VIS:ENA ON')
        self.oscilloscope.write('VIS:AREA1:SHAPE RECT')
        self.oscilloscope.write('VIS:AREA1:SOU CH3')
        self.oscilloscope.write('VIS:AREA1:HITT OUT')
        self.oscilloscope.write(f'VIS:AREA1:WIDTH {20e-9}')
        self.oscilloscope.write(f'VIS:AREA1:HEIG {0.2}')
        self.oscilloscope.write(f'VIS:AREA1:XPOS {7e-9}')
        self.oscilloscope.write(f'VIS:AREA1:YPOS {-0.2}')

        self.oscilloscope.write('VIS:AREA2:SHAPE RECT')
        self.oscilloscope.write('VIS:AREA2:SOU CH3')
        self.oscilloscope.write('VIS:AREA2:HITT OUT')
        self.oscilloscope.write(f'VIS:AREA2:WIDTH {10e-9}')
        self.oscilloscope.write(f'VIS:AREA2:HEIG {0.3}')
        self.oscilloscope.write(f'VIS:AREA2:XPOS {12e-9}')
        self.oscilloscope.write(f'VIS:AREA2:YPOS {0.3}')

        self.oscilloscope.write('VIS:SHOWAR ON')





    def save_and_transfer_waveform(self, mode, file_name, dest, signalChannel="CH1"):
        """
        Save or transfer waveform from the oscilloscope in one function.

        Args:
            mode (str): 'save' ή 'transfer'
            file_name (str): file name with no extension
            dest (str): file 
            channel (str):   'CH1', 'CH2'  
        """
        self.set_cwd(dest)

        if mode.lower() == "save_csv":
            # save waveform as CSV
            self.oscilloscope.write(f'SAV:WAVE {signalChannel}, "{file_name}.csv"')
            logger.info("Saved %s.csv to %s.", file_name, dest)
            return True

        elif mode.lower() == "save_wfm":
            # save waveform as WFM
            self.oscilloscope.write(f'SAV:WAVE {signalChannel}, "{file_name}.wfm"')
            logger.info("Saved %s.wfm to %s.", file_name, dest)
            return True

        elif mode.lower() == "transfer":
            file_name = file_name + ".wfm"
            outputPathOscilloscope = "C:/TCT/"
            self.set_cwd(outputPathOscilloscope)

            # Query the scope for all files
            self.oscilloscope.write('FILESystem:DIR?')
            dir_list = self.oscilloscope.read()  # Tektronix may return multi-line or comma-separated string

            # Remove leading command if present
            if dir_list.startswith(':FILESYSTEM:DIR "'):
                dir_list = dir_list[len(':FILESYSTEM:DIR "'):]

            # Split by lines and commas, strip spaces and quotes
            files = []
            for line in dir_list.splitlines():
                for f in line.split(','):
                    clean_name = f.strip().strip('"')
                    if clean_name:
                        files.append(clean_name)

            logger.warning("Files on the Tektronix scope:")
            for f in files:
                logger.warning(f)

            # Check if the specific filename exists
            if file_name in files:
                logger.warning(f"File found on scope: {file_name}")
            else:
                logger.warning("The file has not been found. Stopping the program now.")
                sys.exit()
            logger.warning(
                "Transferring large .CSV through VISA is slow (~600 kB/s)! 25k waveforms are usually around 800 MB."
            )

            # Save default chunk size
            default_chunk_size = self.oscilloscope.chunk_size
            if default_chunk_size != 102400:
                logger.info("Changing the chunk size from %s to 102400 (100 KB)", default_chunk_size)
            self.oscilloscope.chunk_size = 102400

            logger.warning("Reading file contents in chunks. No status check available.")

            # Ensure destination folder exists
            os.makedirs(os.path.dirname(dest), exist_ok=True)

            os.makedirs(dest, exist_ok=True)
            dest = os.path.join(dest, file_name) 
            self.oscilloscope.write(f'FILES:READF "{file_name}"')

            # Read first 15 bytes (contains file size)
            header = self.oscilloscope.read_bytes(15)

            # bytes 11-14 = number of bytes to EOF (little endian)
            bytes_to_eof = int.from_bytes(header[11:15], "little")

            total_size = 15 + bytes_to_eof

            print("Total file size:", total_size)

            with open(dest, "wb") as f:
                f.write(header)

                remaining = bytes_to_eof
                while remaining > 0:
                    chunk = self.oscilloscope.read_bytes(min(102400, remaining))
                    f.write(chunk)
                    remaining -= len(chunk)
        else:
            raise ValueError(f"Unknown mode: {mode}")

   
    
    def acquire_fastframe_raw(
        self,
        signalChannel="CH3",
        number_of_frames=100):
     self.oscilloscope.write('HORIZONTAL:HISTORY:STATE OFF')    # Disable incompatible modes
     self.oscilloscope.write('VISUAL:ENABLE OFF')
     self.oscilloscope.write('HOR:FASTFRAME:STATE ON')    # Enable FastFrame
     self.oscilloscope.write(f'HOR:FASTFRAME:COUNT {number_of_frames}')
     self.oscilloscope.write('ACQ:STOPAFTER SEQUENCE')    # Single acquisition
     self.oscilloscope.write('ACQ:STATE RUN')
     while int(self.oscilloscope.query('ACQ:STATE?')):  # Wait until acquisition completes
        time.sleep(0.05)
     self.oscilloscope.write(f'DATA:SOURCE {signalChannel}')     # Waveform transfer setup
     self.oscilloscope.write('DATA:ENC RIBINARY')
     self.oscilloscope.write('DATA:WIDTH 1')
     self.oscilloscope.write('HEADER 0')
     record_length = int(    self.oscilloscope.query('HORizontal:RECOrdlength?') ) # Determine record length
     total_points = record_length * number_of_frames
     self.oscilloscope.write('DATA:START 1')
     self.oscilloscope.write(f'DATA:STOP {total_points}')
     raw = self.oscilloscope.query_binary_values(
        'CURVE?',
        datatype='b'
     )
     raw = np.array(raw)

    # Try reconstructing frames
     if raw.size % number_of_frames == 0:
        frames = raw.reshape(
            number_of_frames,
            raw.size // number_of_frames
        )
     else:
        frames = raw

     return frames
        
    def read_waveform_buffer(self, signalChannel="CH3", npoints=5000):
        """
        Read waveform data directly from oscilloscope acquisition buffer.

        Args:
            signalChannel (str): channel to read (CH1, CH2, etc.)
            npoints (int): number of points to transfer

        Returns:
            raw waveform bytes
        """

        self.oscilloscope.write(f'DATA:SOURCE {signalChannel}')
        self.oscilloscope.write('DATA:ENC BINARY')
        self.oscilloscope.write('DATA:WIDTH 1')
        self.oscilloscope.write('HEADER 0')

        self.oscilloscope.write('DATA:START 1')
        self.oscilloscope.write(f'DATA:STOP {npoints}')

        data = self.oscilloscope.query_binary_values(
       'CURVE?',
        datatype='b',
        container=np.array
        )

        return data
    

     
    def measurement_functions(self, Channel):
      
        """
        Set measurement functions (AMPLITUDE, AREA, RISETIME, FALLTIME) and get their values
        from a Tektronix MSO scope.

        """

        # Set measurement source channel
        self.oscilloscope.write(f"MEASU:IMM:SOUR {Channel}")
        measurements = ["AMPLITUDE", "AREA", "RISETIME", "FALLTIME"]

        for  meas in measurements:
            # Add measurement to scope
            self.oscilloscope.write(f'MEASU:ADDMEAS {meas}')
            self.oscilloscope.write(f"MEASU:IMM:TYPE {meas}")

    def measurement_read(self):
        """
        Read measurements and store them in a list.
        """

        measurements = ["AMPLITUDE", "AREA", "RISETIME", "FALLTIME"]
        results = []  

        default_timeout = self.oscilloscope.timeout
        self.oscilloscope.timeout = 20000

        for meas_id, meas in enumerate(measurements, start=1):
            value = float(self.oscilloscope.query(f"MEASU:MEAS{meas_id}:RESU:CURR:MEAN?").strip())
            results.append(value)  # append to list
          

        self.oscilloscope.timeout = default_timeout
        return results  # returns a simple list of values
                
    def busy(self,timeout):
     
     start = time.time()

     while True:
         
         busy = scope.oscilloscope.query("BUSY?").strip()

         if busy == "0":
           break
         
         #if busy =="1":
         #    break

         if   time.time() - start > timeout:
          print("Timeout: acquisition still busy after 5 seconds")
          break
           

     time.sleep(0.1)

    
    def setup_from_json(self, config_json):

        with open(config_json, "r") as config_in_json:
            config = json.load(config_in_json)

        # CHANNEL SETUP
        # -------------------------
        for ch, settings in config["channels"].items():

            # enable / disable channel
            if settings["trace"].upper() == "ON":
                self.control_channel("on", ch)
            else:
                self.control_channel("off", ch)

            # vertical settings
            self.set_vertical(
                scale=settings["volt_div"],
                position=settings["offset"],
                invert=settings.get("invert", "OFF"),
                source=ch,
                term=settings.get("termination", 50)
            )

        # TRIGGER
        self.set_trigger(
            level=config["trigger"]["level"],
            source=config["trigger"]["source"],
            edge=config["trigger"]["slope"]
        )
    
        # HORIZONTAL
        # -------------------------
        self.set_horizontal(
            scale=config["timebase"]["time_div"],
            position=config["timebase"]["trig_delay"]
          
        )

        # -------------------------
        # ACQUISITION
        # -------------------------
        acq = config["acquisition"]

        self.acquisition_mode(
            mode=acq["mode"],
            num_avg=acq.get("num_avg", 16),
            num_env=acq.get("num_env", False)
        )

        # -------------------------
        # FASTFRAME (optional)
        # -------------------------
        if "fastframe" in config:
            ff = config["fastframe"]

            if ff["state"].lower() == "on":
                self.fastframe_control("on", ff["count"])
            else:
                self.fastframe_control("off")

        # -------------------------
        # MEASUREMENTS (optional)
        # -------------------------
        if "measurements" in config:
            self.measurement_functions(Channel=config["measurements"]["channel"])

        print("Scope configured from JSON successfully.")
    



        

         
    def set_cwd(self, dest):
        """
        Set the current working directory on the oscilloscope.
        
        Args:
            dest (str): Destination to change into.
        
        Returns:
            None
        """
        logger.info("Current working directory: %s", self.oscilloscope.query('FILES:CWD?'))
        logger.info("Changing to %s", dest)
        self.oscilloscope.write(f'FILES:CWD "{dest}"')


    def get_parameters_scope(self,CHANNEL):

        self.oscilloscope.write(f"DATA:SOURCE {CHANNEL}")
        self.oscilloscope.write("DATA:ENC RIBINARY")
        self.oscilloscope.write("DATA:WIDTH 1")

        print("\nWaveform scaling parameters:")

        commands = [
            "WFMOUTPRE:YMULT?",
            "WFMOUTPRE:YOFF?",
            "WFMOUTPRE:YZERO?",
            "WFMOUTPRE:XINCR?",
            "WFMOUTPRE:XZERO?",
            "WFMOUTPRE:PT_OFF?",
            "WFMOUTPRE:BYT_NR?",
            "WFMOUTPRE:BIT_NR?",
            "WFMOUTPRE:ENCDG?",
            "WFMOUTPRE:BN_FMT?",
            "WFMOUTPRE:BYT_OR?",
            "WFMOUTPRE:NR_PT?"
        ]
        for cmd in commands:
            try:
                ans = self.oscilloscope.query(cmd).strip()
                print(f"{cmd:<22} {ans}")
            except Exception as e:
                print(f"{cmd:<22} ERROR: {e}")

     
    
if __name__ == "__main__":
    scope = TektronixMSO("USB0::0x0699::0x0530::C064620::INSTR")

    # --- Core flow: apply settings from JSON, then read scaling params + waveform ---
    scope.setup_from_json(r"C:\Users\ehep\tctsw\tctfw\OscControl\diode.json")  # channels, trigger, timebase, acquisition, measurements - all settings live here

    scope.get_parameters_scope("ch3")  # Must run AFTER setup_from_json: prints YMULT/YOFF/YZERO/XINCR/etc, the scaling values used to convert raw samples into an actual pulse (voltage/time) for charge integration - these only reflect the config just applied above

    data = scope.read_waveform_buffer()  # Read raw waveform samples (default: CH3, 5000 points)
    print(data.dtype)
    print(data.shape)
    print(data[:20])
    print(len(data))

    # --- Optional tools below (uncomment whichever you need to try) ---

    # Save the raw waveform to a .npy file
    # waveform_data = scope.read_waveform_buffer("ch3")
    # wf_filename = f"waveform.wfm"
    # outputPath = "C:/Users/ehep/Desktop/"
    # np.save(f"{outputPath}/{wf_filename}", waveform_data)

    # Auto-search for a working trigger level (linear scan from high to low)
    # trigger_level = scope.trigger_search()
    # Auto-search for a working trigger level (binary search, faster)
    # trigger_level = scope.trigger_search_binary()
    # print(trigger_level)

    # Manually start/stop acquisition
    # scope.control_acquisition("on")
    # scope.control_acquisition("off")

    # Manually set the trigger (level, source channel, edge)
    # scope.set_trigger(level=-0.000, source="CH4", edge="FALL")
    # scope.set_trigger(level=-0.020, source="CH3", edge="FALL")

    # FastFrame mode: acquire many frames in a single sequence
    # scope.fastframe_control("on", 1000, 1)
    # scope.acquire_fastframe_raw("ch3", 100)

    # Manually set vertical scale/position/inversion/termination for a channel
    # scope.set_vertical(scale=0.015, position=0, invert="OFF", source="ch3", term=50)

    # Manually set horizontal (time/div) scale and position
    # scope.set_horizontal(scale=20e-9, position=10)
    # scope.set_horizontal(scale=0.02, position=0)

    # Set acquisition mode to averaging over N waveforms
    # scope.acquisition_mode("AVE", num_avg=1)
    # scope.acquisition_mode("AVE", num_avg=16)

    # Manually trigger a single acquisition and wait for it to finish
    # scope.oscilloscope.write('ACQ:STATE RUN')
    # scope.busy(timeout=10)
    # print("finished")

    # Read AMPLITUDE/AREA/RISETIME/FALLTIME measurement results
    # res = scope.measurement_read()

    # Save/transfer a waveform to a local file (3 modes)
    # file_name = "kati"
    # signalChannel = 'CH1'
    # dest = "C:/Users/ehep/Desktop/hepPhysicsNtua/"
    # scope.save_and_transfer_waveform("save_wfm", file_name="kati", dest="C:/Users/ehep/Desktop/hepPhysicsNtua/")
    # scope.save_and_transfer_waveform(mode="save_csv", file_name="test_waveform", dest="C:/Temp")
    # scope.save_and_transfer_waveform(mode="transfer", file_name="test_waveform", dest="C:/Users/ehep/Desktop/cassiasw-master/share/test_waveform.wfm")  # "transfer" mode does not work - timeout error

    # DO NOT MODIFY
    scope.close_connection()

    # --- Broken / non-functional leftovers, kept only for reference (do not uncomment as-is) ---
    # scope.get_waveform()                      # method does not exist on this class
    # scope.read_waveform_raw("CH3")             # method does not exist on this class
    # print(scope.oscilloscope.query("CURVE?"))  # leftover duplicate query, not part of any flow
