import os
import struct
import logging
import itertools
from datetime import datetime
# from TCTData import TCTData
import numpy as np
import matplotlib.pyplot as plt
from TCTData import TCTData, TCTHeader
from sys import exit

# logging.basicConfig(
#     level=logging.DEBUG,  # show DEBUG, INFO, WARNING, ERROR
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

logger = logging.getLogger(__name__)  # get a logger for this module
logger.debug("test")


TCT_SOURCES = {
    0: "red (658 nm)",
    1: "IR (932 nm)",
    2: "IR (1064 nm)",
    3: "alpha particles",
    4: "electrons",
}

class TCTReader:
    


    @staticmethod
    def _extract_header(raw)->"TCTHeader":
        """
        Read a TCT file into a useful format

        Parameters
        ----------
        f:
            The file to read from
        output:
            The output format, currently only 'xarray' is valid

        Returns
        -------
        `xarray.DataArray`
            The pulses of all scan-points stores in a convenient format
        """
    
        file_type, = struct.unpack("<f", raw.read(4))
        file_type = int(file_type)
        logger.debug("File type = %s", file_type)


        data = struct.unpack("<29f", raw.read(4 * 29))

        day, month, year, hour, minute, second = map(int, data[:6])
        date = datetime(year, month, day, hour, minute, second)
        logger.debug("Date/time = %s", date)
        
        # Not sure what abstime is?
        # Seems to be the right day/month time but 66 years in the future!!
        abstime = data[6]

        # Read the number of points in the scan
        x0, dx, Nx, y0, dy, Ny, z0, dz, Nz = data[7:16]
        Nx, Ny, Nz = int(Nx), int(Ny), int(Nz)
        logger.debug("x0 = %s, y0 = %s, z0 = %s", x0, y0, z0)
        logger.debug("dx = %s, dy = %s, dz = %s", dx, dy, dz)
        
        # This indicates the total number of positions scanned
        Nxyz = int(Nx * Ny * Nz)
        logger.debug("Number of positions = %s (X = %s, Y = %s, Z = %s)", Nxyz, Nx, Ny, Nz)

        offset = 1 if file_type in (33, 51, 81, 82) else 0
        
        logger.debug("offset = %s", offset)
        
        # How many osc channels are on
        channels = data[16 : 19 + offset]
        Nchannels = int(sum(channels))

        # The number of voltage scan points and the various values
        # No idea what is that!!!!!!!!!!!
        NU1 = int(data[19 + offset])
        U1 = data[20 + offset : 20 + offset + NU1]
        NU2 = int(data[20 + offset + NU1])
        U2 = data[21 + offset + NU1 : 21 + offset + NU1 + NU2]
        
        logger.debug("NU1 (voltage steps, source 1) = %s", NU1)
        logger.debug("NU2 (voltage steps, source 2) = %s", NU2)
        # Time series recunstruction data
        t0 = data[21 + offset + NU1 + NU2]
        logger.debug("t0 = %s", t0)
        dt = data[22 + offset + NU1 + NU2]
        logger.debug("dt = %s", dt)
        NP = int(data[23 + offset + NU1 + NU2])
        logger.debug("NP = %s", NP)

        # Temperature measured during run!!!!
        T = data[24 + offset + NU1 + NU2]
        logger.debug("Temperature = %s k", T)
        
        # Source Type during run
        source = int(data[25 + offset + NU1 + NU2])
        source = TCT_SOURCES.get(source, "Unknown")
        logger.debug("source = %s", source)

        # First reads the user size which indicates the number of bytes to read right 
        # after for the user name
        user_size, = struct.unpack("<i", raw.read(4))
        user, = struct.unpack(f"{user_size}s", raw.read(user_size))
        logger.debug("user = %s", user)

        # First reads the sample_size which indicates the number of bytes to read right 
        # after for the sample comment
        sample_size, = struct.unpack("<i", raw.read(4))
        sample, = struct.unpack(f"<{sample_size}s", raw.read(sample_size))
        logger.debug("sample = %s", sample)
        
        # First reads the comment size which indicates the number of bytes to read right 
        # after for the user comment
        comment_size, = struct.unpack("<i", raw.read(4))
        comment, = struct.unpack(f"<{comment_size}s", raw.read(comment_size))
        logger.debug("comment = %s", comment)
        
        # # Specific to the file type (this is met)
        # if file_type in (33, 51, 81, 82):
        #     # Temperature
        #     T = data[24 + offset + NU1 + NU2]
        #     # Source
        #     source = int(data[25 + offset + NU1 + NU2])
        #     source = TCT_SOURCES.get(source, "Unknown")
        #     # User who performed the scan
        #     user_size, = struct.unpack("<i", raw.read(4))
        #     print(user_size)
        #     user, = struct.unpack(f"{user_size}s", raw.read(user_size))
        #     user = data[26 + offset + NU1 + NU2]
        #     # exit()

        #     raw.seek((27 + offset + NU1 + NU2) * 4)
         
        #     sample_size, = struct.unpack("<i", raw.read(4))
        #     sample, = struct.unpack(f"<{sample_size}s", raw.read(sample_size))
        #     # A comment entered by the user at the beginning of the scan
        #     comment_size, = struct.unpack("<i", raw.read(4))
        #     comment, = struct.unpack(f"<{comment_size}s", raw.read(comment_size))

        #     logger.debug("Temperature = %s k", T)
        #     logger.debug("source = %s", source)
        #     logger.debug("user = %s", user)
        #     logger.debug("sample = %s", sample)
        #     logger.debug("comment = %s", comment)

        _TCTHeader = TCTHeader(file_type,date,x0,y0,z0,dx,dy,dz,Nx,Ny,Nz,Nxyz,channels,Nchannels,offset,NU1,U1,NU2,U2,t0,dt,NP,T,source,user,sample,comment)
        return _TCTHeader


    @staticmethod
    def _extract_data(header, raw, accuracy = 0,scan_type='xy',snake_xy=False, snake_xz=False)->"tuple":


        # Now need to do the Wavefrom reading...
        x_values = []
        y_values = []
        z_values = []

        all_data = []
        try:
            for _ in itertools.product(range(header.NU1), range(header.NU2)):
                waveform_data = []
                cube = []
                id = 0
                tU1, tU2, tI1, tI2 = struct.unpack("<4f", raw.read(4 * 4))
                n_to_read = {33: 4, 22: 4, 51: 5, 81: 8, 82: 18}[header.file_type]

                corrupted_index = []
                for index in range(header.Nxyz):

                    # Files can become corrupted if the scan crashes halfway through
                    # However, it appears the ROOT examples just carry on regardless
                    # Here we at least print something out
                    # (and should probably raise an exception)
                    data_to_unpack = raw.read(4 * n_to_read)
                    if not data_to_unpack:
                        logger.warning("Reached end of file unexpectedly")
                        break

                    x, y, z, beam_monitor_value, *rest = struct.unpack(
                        f"<{n_to_read}f", data_to_unpack
                    )
                    
                    cube.append([round(x,accuracy),round(y,accuracy),round(z,accuracy)])
                    

                    
                    logger.debug("beam monitor value = %s", beam_monitor_value)
                    logger.debug("time? = %s", rest)
                    waveform_channels = []
                    # fix multichannel
                    
                    for i in header.channels:
                        if not i:
                            continue
                        data = struct.unpack(f"<{header.NP}f", raw.read(4 * header.NP))
                        waveform_channels.append(np.array(data))
                    waveform_data.append(waveform_channels)
                    
                        
        except:
            total_corrupted = header.Nxyz - index
            print(f"Currupted buffer at index {index}")
            print(f"Add padding {header.Nxyz - index} lines")
            for _ in range(total_corrupted):
                for i in header.channels:
                    if not i:
                        continue
                    waveform_channels.append(np.zeros(header.NP))
                waveform_data.append(waveform_channels)
        all_data.append(waveform_data)

        
        _all_data = np.array(all_data)

        print("Fix Offset!!!!!")

        x = np.linspace(header.x0, header.x0 + header.Nx * header.dx, header.Nx)
        y = np.linspace(header.y0, header.y0 + header.Ny * header.dy, header.Ny)
        z = np.linspace(header.z0, header.z0 + header.Nz * header.dz, header.Nz)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")


        # This doesnt work for Z scans
        match scan_type:
            case "xy":
                _W = _all_data[0,:,0,:].reshape(header.Nz, header.Ny, header.Nx, header.NP, order="C")
            case "xz":
                _W = _all_data[0,:,0,:].reshape(header.Nz, header.Ny, header.Nx, header.NP, order="C")
            case "yz":
                _W = _all_data[0,:,0,:].reshape(header.Nz, header.Ny, header.Nx, header.NP, order="C")
            case "xyz":
                _W = _all_data[0,:,0,:].reshape(header.Nz, header.Ny, header.Nx, header.NP, order="C")
            case _:
                print("UNKNOWN SCAN TYPE RETURNING EMPTY W")
                W = np.empty([2,2])
                
        if snake_xy or snake_xz:
            if snake_xy:
                _W[:, 1::2, :,:] = _W[:, 1::2, ::-1,:]
            else:
                _W[1::2, :, :,:] = _W[1::2, :, ::-1,:]

        W = np.transpose(_W, (2, 1, 0, 3 ))
        # Zig Zag and offeset issue....
        # We need a function that fixes the representation and also ac




        # W = np.array(all_data)
            
        # W = np.empty((2,2))
        return X, Y, Z, W, all_data, cube


        # print(all_data)
        # # Check no more bytes left over!
        # assert f.read() == b""

        # # Output format (currently only xarray)
        # if output == "xarray":
        #     import xarray as xr

        #     return xr.DataArray(
        #         waveform_data,
        #         dims=("U1", "U2", "z", "y", "x", "channel", "time"),
        #         coords=[
        #             ("U1", np.array(U1), {"units": "V"}),
        #             ("U2", np.array(U2), {"units": "V"}),
        #             ("z", np.linspace(z0, z0 + Nz * dz, Nz), {"units": "$\mu m$"}),
        #             ("y", np.linspace(y0, y0 + Ny * dy, Ny), {"units": "$\mu m$"}),
        #             ("x", np.linspace(x0, x0 + Nx * dx, Nx), {"units": "$\mu m$"}),
        #             ("channel", [i for i, j in enumerate(wf_on_off, start=1) if j]),
        #             ("time", np.linspace(t0, t0 + NP * dt, NP), {"units": "ns"}),
        #         ],
        #         attrs={
        #             "datetime": date,
        #             "temperature [k]": T,
        #             "source": source,
        #             "user": user,
        #             "sample": sample,
        #             "comment": comment,
        #             "units": "mV",
        #         },
        #     )
        # else:
        #     raise NotImplementedError("Only xarray output is currently implemented")
        

    @staticmethod
    def read(data_path,custom_path=False,snake_xy=False, snake_xz=False,scan_type="xy")->"TCTData":
        """
        This function connects to a database and loads the raw data target path
        """
        
        if custom_path:
            full_data_path = data_path
        else:
            full_data_path = os.environ.get("TCT_DATA_DIR")+"/"+data_path


        if os.path.exists(full_data_path):
            
            # Extract header information
            with open(full_data_path, "rb") as raw:
                _TCTHeader = TCTReader._extract_header(raw)
                
                data = TCTReader._extract_data(_TCTHeader, raw, accuracy= 0, snake_xy=snake_xy, snake_xz=snake_xz,scan_type=scan_type)
                _TCTData = TCTData(_TCTHeader,*data)

        
        else:

            print(f"[tctfw_waveform] invalid data path {full_data_path}")
            exit()
        
        return _TCTData
        
        
        
