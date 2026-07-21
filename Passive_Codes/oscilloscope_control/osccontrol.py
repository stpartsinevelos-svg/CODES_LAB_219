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

import pyvisa
import logging
logger = logging.getLogger(__name__)

# from ftplib import FTP
# ch = logging.StreamHandler()

class TektronixMSO:
    """Control of oscilloscope."""
     
 

   
    def __init__(self, ip_address):
        """
        Initialize the connection to the Tektronix MSO64B oscilloscope.
        
        Args:
            ip_address (str): The IP address of the oscilloscope.
        
        Return:
            None
        """
        self.rm = pyvisa.ResourceManager('@py')
        try:
            self.resource_name = f'TCPIP0::{ip_address}::INSTR'
            self.oscilloscope = self.rm.open_resource(self.resource_name)

        except pyvisa.errors.VisaIOError as e:
            logger.critical("Could not connect to oscilloscope at %s", ip_address)
            raise e

        logger.info("Connected to: %s", self.read('*IDN?'))
    
    def ftp_get_wfm(self, ip, scope_path, filename, pc_folder):
        
        ftp = FTP(ip)

        ftp.login()  

        ftp.cwd(scope_path)

        os.makedirs(pc_folder, exist_ok=True)
        local_path = os.path.join(pc_folder, filename)

        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {filename}", f.write)

        ftp.quit()
        print(f"✅ WFM downloaded via FTP: {local_path}")


    def config(self, config):
        """
        Configure the oscilloscope with default settings.
        Note: this is a very specific configuration for the SiC project.
        
        Args:
            config (dict): Configuration dictionary.
        
        Returns:
            None
        """
        self.set_horizontal(
            scale=config["Oscilloscope"]["Horizontal"]["scale"],
            position=config["Oscilloscope"]["Horizontal"]["position"]
        )
        self.set_vertical(
            scale=config["Oscilloscope"]["Vertical"]["scale"],
            position=config["Oscilloscope"]["Vertical"]["position"],
            invert=config["Oscilloscope"]["Vertical"]["invert"]
        )
        self.set_trigger(
            level=config["Oscilloscope"]["Trigger"]["level"],
            source=config["Oscilloscope"]["Trigger"]["source"],
            edge=config["Oscilloscope"]["Trigger"]["edge"]
        )
        if config["Oscilloscope"]["Trigger"]["visual_trigger"]:
            self.set_vis_trigger()

        self.set_acquisition_mode()
        self.set_acquisition_count(config["Oscilloscope"]["Acquisition"]["counts"])

        self.add_meas(config["Oscilloscope"]["Measurements"])

    def write(self, command):
        """
        Wrapper for instrument write with error check.
        
        Args:
            command (str): SCPI command
            
        Returns:
            None

        Raises:
            ValueError: write did not work
        """
        try:
            logger.debug("To write: %s", command)
            self.oscilloscope.write(command)
            status = self.check_status()

        except Exception as e:
            logger.error(e)
            logger.error("Write SCPI command: %s", command)

            raise ValueError("Write did not work!") from e

        if status:
            logger.error("Error for write command: %s", command)
            logger.error("%s", self.interpret_status_byte(status))

    def read(self, command):
        """
        Wrapper for instrument read with error check.
        
        Args:
            command (str): SCPI command
            
        Returns:
            str: The response from the instrument.

        Raises:
            ValueError: read did not work
        """
        try:
            logger.debug("To read: %s", command)
            read = self.oscilloscope.query(command).strip()
            logger.debug("return: %s", read)
            status = self.check_status()

        except Exception as e:
            logger.error(e)
            logger.error("Read SCPI command: %s", command)
            self.check_status()

            raise ValueError("Read did not work!") from e

        if status:
            logger.error("Error for read command: %s", command)
            logger.error("%s", self.interpret_status_byte(status))

        return read
    

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

    def load_setup(self, setup_file_path):
        """
        Recall a saved oscilloscope setup (.set or .stp file).

        Args:
            setup_file_path (str): Full path to the setup file on the oscilloscope (e.g., 'C:/Setups/my_config.set').

        Returns:
            None
        """
        logger.info("Recalling oscilloscope setup from %s", setup_file_path)
        self.write(f'RECALL:SETUP "{setup_file_path}"')

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

    def set_horizontal(self, scale, position):
        """
        Set the horizontal scale and position.
        
        Args:
            scale (float): The horizontal scale.
            position (float): The horizontal position.
        
        Returns:
            None
        """
        self.write(f'HOR:MOD:SCA {scale}')
        self.write(f'HOR:POS {position}')

    def set_vertical(self, scale, position, invert, term=50):
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
        self.write(f'CH3:SCA {scale}')
        self.write(f'CH3:TER {term}')
        self.write(f'CH3:POS {position}')
        if invert=="ON":
            logger.warning("Inverting signal on CH3!")
        self.write(f'CH3:INV {invert}')

    def set_trigger(self, level, source='CH3', edge='FALL'):
        """
        Set the trigger settings for the oscilloscope.
        
        Args:
            level (float): Trigger level in volts.
            source (str): Trigger source (e.g., 'CH3').
            edge (str): Trigger edge ('RIS' for rising, 'FALL' for falling, 'EIT' for either).
        
        Returns:
            None
        """
        self.write(f'TRIG:A:EDGE:SOU {source}')
        self.write(f'TRIG:A:EDGE:SLO {edge}')
        self.write('TRIG:A:MOD NORM')
        self.write(f'TRIG:A:HOLD:TIM {20e-9}')
        self.write(f'TRIG:A:LEV:{source} {level}')

        logger.info('Trigger set to %s at level %s with %s edge.', source, level, edge)

    def set_vis_trigger(self):
        """
        Set the visual trigger settings for the oscilloscope.
        Note: this is a very specific configuration for the SiC project.
        
        Args:
            None
        
        Returns:
            None
        """
        self.write('VIS:ENA ON')
        self.write('VIS:AREA1:SHAPE RECT')
        self.write('VIS:AREA1:SOU CH3')
        self.write('VIS:AREA1:HITT OUT')
        self.write(f'VIS:AREA1:WIDTH {20e-9}')
        self.write(f'VIS:AREA1:HEIG {0.2}')
        self.write(f'VIS:AREA1:XPOS {7e-9}')
        self.write(f'VIS:AREA1:YPOS {-0.2}')

        self.write('VIS:AREA2:SHAPE RECT')
        self.write('VIS:AREA2:SOU CH3')
        self.write('VIS:AREA2:HITT OUT')
        self.write(f'VIS:AREA2:WIDTH {10e-9}')
        self.write(f'VIS:AREA2:HEIG {0.3}')
        self.write(f'VIS:AREA2:XPOS {12e-9}')
        self.write(f'VIS:AREA2:YPOS {0.3}')

        self.write('VIS:SHOWAR ON')

    def save_waveforms(self, file_name, dest):
        """
        Save waveforms to a specified file.
        
        Args:
            file_name (str): The name of the file to save the waveforms.
            dest (str): The destination directory.
        
        Returns:
            None
        """
        self.set_cwd(dest)
        self.write(f'SAV:WAVE CH3, "{file_name}.csv"')
        logger.info("Saved %s to %s..", file_name, dest)

    def save_to_wfm(self, file_name, dest, Channel):
        """
        Save waveforms to a specified file.
        
        Args:
            file_name (str): The name of the file to save the waveforms.
            dest (str): The destination directory.
        
        Returns:
            None
        """
        self.set_cwd(dest)
        self.write(f'SAV:WAVE {Channel}, "{file_name}.wfm"')
        logger.info("Saved %s to %s..", file_name, dest)

    def transfer_waveforms(self, file_path, file_name, dest_loc):
        """
        Transfer waveforms from the oscilloscope to a local file.
        
        Args:
            file_path (str): The path of the file on the oscilloscope.
            file_name (str): The name of the file to transfer.
            dest_loc (str): The local destination path.
        
        Returns:
            None
        """
        logger.warning(
            "Transferring large .CSV through VISA is slow (~600 kB/s)! 25k waveforms are usually around 800 MB."
            )
        self.set_cwd(file_path)

        default_chunk_size = self.oscilloscope.chunk_size
        if not default_chunk_size == 102400:
            logger.info("Changing the chunk size from %s to 1024000 (1 MB)", default_chunk_size)

        self.oscilloscope.chunk_size = 102400
        logger.warning("Reading file contents. No status check available.")
        self.oscilloscope.write(f'FILES:READF "{file_name}"')
        file_data = self.oscilloscope.read_raw()

        if not default_chunk_size == 102400:
            logger.info("Changing back the chunk size..")
            self.oscilloscope.chunk_size = default_chunk_size

        os.makedirs("data/", exist_ok=True)

        logger.info("Writing transferred data to %s", "data/" + dest_loc)

        with open(f'data/{dest_loc}', 'wb') as file:
            file.write(file_data)

    def set_cwd(self, dest):
        """
        Set the current working directory on the oscilloscope.
        
        Args:
            dest (str): Destination to change into.
        
        Returns:
            None
        """
        logger.info("Current working directory: %s", self.read('FILES:CWD?'))
        logger.info("Changing to %s", dest)
        self.write(f'FILES:CWD "{dest}"')

    def start_acquisition(self):
        """
        Start a single sequence acquisition.
        
        Args:
            None
        
        Returns:
            None
        """
        self.write('ACQ:STATE RUN')
        logger.info('Acquisition started.')

    def stop_acquisition(self):
        """
        Stop the current acquisition.
        
        Args:
            None
        
        Returns:
            None
        """
        self.write('ACQ:STATE STOP')
        logger.info('Acquisition stopped.')

    def check_acq(self):
        """
        Check if acquisitions are being taken.

        Args:
            None

        Returns:
            bool: True if recording of acquisitions is ongoing.
        """
        acq = int(self.read('ACQ:STATE?').strip())
        if acq:
            logger.debug("Recording acquisitions ongoing!")
        else:
            logger.debug("Recording acquisitions stopped!")

        return bool(acq)

    def get_num_acq(self):
        """
        Check how many acquisitions have been taken.

        Args:
            None

        Returns:
            int: Number of acquisitions.
        """
        num_acq = int(self.read('ACQ:NUMAC?'))
        logger.debug("Number of acquisitions: %s (ongoing: %s)", num_acq, self.check_acq())

        return num_acq

    def clear_osc(self):
        """
        Clear all acquisitions, measurements, and waveforms of the oscilloscope.

        Args:
            None

        Returns:
            None
        """
        self.write("CLEAR")
        logger.info("All acquisitions, measurements, and waveforms of oscilloscope cleared")

    def set_acquisition_count(self, count):
        """
        Set the number of acquisitions.
        
        Args:
            count (int): The number of acquisitions to set.
        
        Returns:
            None
        """
        self.write(f'ACQ:SEQ:NUMSEQ {count}')
        logger.info('Number of acquisitions set to %s.', count)

    def set_acquisition_mode(self):
        """
        Set the acquisition mode to sequence.

        Args:
            None

        Returns:
            None
        """
        self.write('HOR:HIST:STATE ON')

        self.write('ACQ:STOPA SEQ')

    def autoscale(self):
        """
        Perform an autoscale operation on the oscilloscope.
        
        Args:
            None
        
        Returns:
            None
        """
        self.write('AUTOSCALE')
        logger.info('Autoscale executed.')

    def close(self):
        """
        Close the connection to the oscilloscope.
        
        Args:
            None
        
        Returns:
            None
        """
        self.oscilloscope.close()
        logger.info('Oscilloscope connection closed.')

    def add_meas(self, measurements):
        """
        Add a measurement to the oscilloscope.
        
        Args:
            measurements (list): List of measurements to add.
        
        Returns:
            None
        """
        for meas_id, meas in measurements.items():
            self.write(f'MEASU:ADDMEAS {meas}')
            logger.info('Measurement %s (id: %s) added to oscilloscope.', meas, meas_id)

    def return_meas(self, measurements):
        """
        Return the measurement value.
        
        Args:
            measurements (list): List of measurements to return.
        
        Returns:
        """

        all_results = {}
        meas_values = [
            'MIN',
            'MAX',
            'POPU',
            'STDD',
            'MEAN'
        ]

        for meas_id, meas in measurements.items():
            all_results[meas] = {}
            for value in meas_values:
                read = self.read(f'MEASU:MEAS{meas_id}:RESU:ALLA:{value}?')
                all_results[meas][value] = read

            logger.info('Measurement %s (id: %s) values: %s', meas, meas_id, all_results[meas])

        return all_results

    def fastframe_on(self, number_of_frames):
        """
        Turns off the "Enable Acquisition History" and "Visual Trigger" modes such
        that the oscilloscope can be used in FastFrame mode. Then enable fast frame
        mode for number_of_frames. Please note that there is a maximum frame count 
        so where this is important also use number_fastFrames_taken
        
        Inputs:
            number_of_frames (int).
        """
        self.write('HORIZONTAL:HISTORY:STATE OFF') # Disable "Enable Acquisition History"
        self.write('VISUAL:ENABLE OFF') # Disable visual trigger

        self.write('HORIZONTAL:FASTFRAME:STATE ON')
        self.write('HORIZONTAL:FASTFRAME:COUNT {}'.format(number_of_frames))

        # Turn on overlay mode so that all frames can be seen
        self.write(':HORizontal:FASTframe:MULtipleframes:MODe OVERlay')   

        logger.info('FastFrame mode enabled.')
    
    def fastframe_off(self):
        """Turns off the FastFrame mode on the oscilloscope."""
        self.write('HORIZONTAL:FASTFRAME:STATE OFF')
        logger.info('FastFrame mode disabled.')
    
    def number_fastFrames_taken(self):
        return int(self.read('ACQUIRE:NUMFRAMESACQUIRED?'))

    def fastframe_total_time(self,frame_count):
        """Get the time between the first frame (t=0s) and the {frame_count} frame.
        This can also be used to then find the time between all frames.

        Inputs:
            frame_count (int): The number of frames to consider for the time calculation.

        Returns:
            The total time taken for the frames in seconds (float).
        """
        
        # Set Reference frame to 1
        self.write(":HORIZONTAL:FASTFRAME:REF:FRAME 1")
        # Set selected frame to the last one, taken as input from external script
        self.write(f":HORIZONTAL:FASTFRAME:SELECTED {frame_count}")
        
        time_taken_str = self.read(":HORIZONTAL:FASTFRAME:TIMESTAMP:DELTA?")  # e.g. '"0.83929"'
        time_taken = float(time_taken_str.strip().strip('"'))

        return time_taken
    def transfer_wfm_to_pc(self, scope_folder, wfm_name, pc_folder):
     """
     Transfer a .wfm file from Tektronix oscilloscope to PC.
     """

    # Change directory on scope
     self.oscilloscope.write(f'FILES:CWD "{scope_folder}"')

    # Increase timeout for large binary transfers
     self.oscilloscope.timeout = 30000
     self.oscilloscope.chunk_size = 102400

    # Read file from scope buffer
     self.oscilloscope.write(f'FILES:READF "{wfm_name}"')
     data = self.oscilloscope.read_raw()

    # Write to PC
     os.makedirs(pc_folder, exist_ok=True)
     pc_path = os.path.join(pc_folder, wfm_name)

     with open(pc_path, "wb") as f:
        f.write(data)

     print(f"✅ WFM transferred to PC: {pc_path}")
 
    def download_waveforms2(self, osc_folderpath, osc_filename, output_folderpath):

     self.set_cwd(osc_folderpath)
     self.oscilloscope.timeout = 300000

        # 5 minutes
     self.oscilloscope.chunk_size = 102400

     logger.warning("Reading file contents from oscilloscope...")

     self.oscilloscope.write(f'FILES:READF "{osc_filename}"')
     file_data = self.oscilloscope.read_raw()

     output_filepath = os.path.join(output_folderpath, osc_filename)
 
     with open(output_filepath, "wb") as f:
        f.write(file_data)

     logger.info("Saved file to %s", output_filepath)

    def download_waveforms(self, osc_folderpath, osc_filename, output_folderpath):
        
        """Transfer waveforms from the oscilloscope to a local file.
        
        Inputs:
            osc_folderpath (str): The folderpath of the file on the oscilloscope.
            file_name (str): The name of the file to transfer with .wfm suffix.
            dest_loc (str): The local (oscilloscope) destination path.
        """
        logger.warning(
            "Transferring large .CSV through VISA is slow (~600 kB/s)! 25k waveforms are usually around 800 MB."
            )
        self.set_cwd(osc_folderpath)

        default_chunk_size = self.oscilloscope.chunk_size
        if not default_chunk_size == 102400:
            logger.info("Changing the chunk size from %s to 1024000 (1 MB)", default_chunk_size)

        self.oscilloscope.chunk_size = 102400
        logger.warning("Reading file contents. No status check available.")

        self.oscilloscope.write(f'FILES:READF "{osc_filename}"')
        file_data = self.oscilloscope.read_raw()

        if not default_chunk_size == 102400:
            logger.info("Changing back the chunk size..")
            self.oscilloscope.chunk_size = default_chunk_size

        output_filepath = os.path.join(output_folderpath,osc_filename)
        logger.info("Writing transferred data to %s", output_filepath)

        with open(output_filepath, 'wb') as file:
            file.write(file_data)


if __name__ == "__main__":
   

    ip_address = "192.168.0.11"   # <<< scope IP
    osc = TektronixMSO(ip_address)

    # Clear previous state
    osc.reset_instrument()
 #   osc.write("DATA:SOURCE CH1")
   # osc.write("CURVE?")
    

    # Make sure CH3 is ON
    osc.write("CH3:STATE ON")
    osc.write("CH1:STATE OFF")

    # Optional: basic setup
    osc.write("CH3:SCA 0.1")      # 100 mV/div (adjust)
    osc.write("CH3:POS 0")
    osc.write("CH3:TER 50")
    osc.set_trigger(level="-60e-3", source='CH3', edge='FALL')
     
    # Start acquisition
    osc.start_acquisition()

    # Wait until acquisition is done (single/sequence mode)
   # while osc.check_acq():
    #    pass

    # Save waveform from CH3 to oscilloscope disk
    

    # Stop acquisition
    osc.save_to_wfm(
    file_name="waveform_2",
    dest="C:",
    Channel="CH3")
    # Close connection
   # osc.download_waveforms2( osc_folderpath="C:",   osc_filename="acq_ch3.wfm", output_folderpath=r"C:\Users\ehep\Desktop\hepPhysicsNtua" )
    
   # osc.transfer_wfm_to_pc(
      #  scope_folder="C:/TCT",
      #  wfm_name="acq_ch3.wfm",
       # pc_folder=r"C:\Users\ehep\Desktop\hepPhysicsNtua"
   # )
    print("✅ Acquisition complete, CH3 waveform saved as acq_ch3.wfm")
    osc.close()
"""
set_cwd
    parser = argparse.ArgumentParser(
        description="Control of the Tektronix 4/5/6 series MSO."
    )

    parser.add_argument(
        "-ip",
        "--ipaddress",
        type=str,
        required=True,
        help="IP adress of the oscilloscope"
    )

    parser.add_argument(
        "-d",
        "--debug",
        type=bool,
        choices=[False, True],
        help="Set logger to debug level"
    )

    args = vars(parser.parse_args())

    if args["debug"]:
        logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        logger.info("Logger level set to DEBUG")

    osc = TektronixMSO(args["ipaddress"])

    osc.check_status()
    osc.close()
 """
     