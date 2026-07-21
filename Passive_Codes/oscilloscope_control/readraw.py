 

import struct
import numpy as np
import matplotlib.pyplot as plt


def read_struct(f, fmt, offset=None, endian="<"):
    if offset is not None:
        f.seek(offset)
    size = struct.calcsize(fmt)
    data = f.read(size)
    if len(data) != size:
        raise EOFError("Short read")
    return struct.unpack(endian + fmt, data)


def read_wfm_v3(path):

    with open(path, "rb") as f:

        # ------------------------------------------------------------------
        # 1. Verify file signature
        # ------------------------------------------------------------------
        f.seek(0)
        header = f.read(16)

        if b"WFM#" not in header:
            raise ValueError("Not a Tektronix WFM file")

        print("Detected WFM file")

        endian = "<"  # 4/5/6 series are little endian

        # ------------------------------------------------------------------
        # 2. Read format code (this offset is stable in v3)
        # ------------------------------------------------------------------
        fmt_code = read_struct(f, "i", 0x0F0, endian)[0]

        fmt_map = {
            0: ("i2", 2),
            1: ("i4", 4),
            2: ("u4", 4),
            3: ("u8", 8),
            4: ("f4", 4),
            5: ("f8", 8),
            6: ("u1", 1),
            7: ("i1", 1),
        }

        if fmt_code not in fmt_map:
            raise ValueError("Unsupported format code")

        np_type, bytes_per_sample = fmt_map[fmt_code]
        dtype = np.dtype(endian + np_type)

        print("Format code:", fmt_code)

        # ------------------------------------------------------------------
        # 3. Read scaling from dimension blocks (v3 offsets)
        # ------------------------------------------------------------------
        y_scale  = read_struct(f, "d", 0x0A8, endian)[0]
        y_offset = read_struct(f, "d", 0x0B0, endian)[0]

        x_increment = read_struct(f, "d", 0x1E8, endian)[0]
        x_zero      = read_struct(f, "d", 0x1F0, endian)[0]

        print("Y scale:", y_scale)
        print("X increment:", x_increment)

        # If scaling is clearly broken, stop early
        if abs(y_scale) < 1e-20 or abs(x_increment) < 1e-20:
            raise ValueError("Scaling values invalid — header layout mismatch")

        # ------------------------------------------------------------------
        # 4. Find curve buffer safely
        # ------------------------------------------------------------------
        f.seek(0, 2)
        file_size = f.tell()

        # For normal non-fastframe files, waveform is last block
        # We compute number of samples from remaining bytes
        curve_buffer_offset = read_struct(f, "I", 0x10, endian)[0]

        data_bytes = file_size - curve_buffer_offset
        num_samples = data_bytes // bytes_per_sample

        print("Samples:", num_samples)

        f.seek(curve_buffer_offset)
        raw = f.read(num_samples * bytes_per_sample)

        raw_data = np.frombuffer(raw, dtype=dtype)

        # ------------------------------------------------------------------
        # 5. Reconstruct waveform
        # ------------------------------------------------------------------
        voltage = raw_data.astype(np.float64) * y_scale + y_offset
        time = np.arange(num_samples) * x_increment + x_zero

        return time, voltage


# --------------------------------------------------------------------------
# Plot example
# --------------------------------------------------------------------------
if __name__ == "__main__":

    path = r"C:\Users\ehep\Desktop\waveform.wfm"

    time, voltage = read_wfm_v3(path)

    # Remove early samples if needed
    voltage[time < 1e-9] = 0

    plt.figure(figsize=(10, 5))
    plt.plot(time * 1e9, voltage)
    plt.xlabel("Time [ns]")
    plt.ylabel("Voltage [V]")
    plt.title("Tektronix WFM Reconstructed")
    plt.grid(True)
    plt.tight_layout()
    plt.show()