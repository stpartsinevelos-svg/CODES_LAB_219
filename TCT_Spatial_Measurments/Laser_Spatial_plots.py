
import struct
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import erf

waveform_length = 1000
file_path = r"C:\Users\ehep\Desktop\iv_exec\LGADS_TCTboard_IV_Gain\yscan_SPOT_size_V2-2TR-TW2.np"
waveforms = []
measurements = []
x_positions=[]
y_positions=[]
z_positions=[]


def gaussian(x, A, mu, sigma):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2))

def trapezoidal_integration(x, y):
    return np.abs(np.trapezoid(x, y))

def error_func(x, A, x0, sigma, B):
    return A * erf((x - x0) / sigma) + B

with open(file_path, "rb") as f:

    # skip header
    while True:
        line = f.readline()
        if line.startswith(b"FORMAT:"):
            break

    while True:

        # x,y,z
        pos_bytes = f.read(24)
        if len(pos_bytes) < 24:
            break

        x, y, z = struct.unpack("3d", pos_bytes)

        # amplitude, area
        meas_bytes = f.read(16)
        if len(meas_bytes) < 16:
            break

        amplitude, area = struct.unpack("2d", meas_bytes)

        # waveform
        waveform = np.fromfile(
            f,
            dtype=np.int8,
            count=waveform_length
        )

        if len(waveform) < waveform_length:
            break

        measurements.append({
            "x": x,
             "y": y,
             "z": z,
             "amplitude": amplitude,
             "area": area
        })

        waveforms.append(waveform)

        x_positions.append(x)
        y_positions.append(y)
        z_positions.append(z)
    # for i in range(10):
    #     print(f"{measurements[i]["x"]}")

print(f"Loaded {len(waveforms)} waveforms")


def compute_max_charge_all_z():

    from collections import defaultdict
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.optimize import curve_fit

    groups = defaultdict(lambda: {"y": [], "waveforms": []})

    # Group data by z
    for y, z, waveform in zip(y_positions, z_positions, waveforms):
        groups[z]["y"].append(y)
        groups[z]["waveforms"].append(waveform)

    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12

    z_list = []
    fwhm_list = []

    for z, data in sorted(groups.items()):

        y = np.array(data["y"])
        charges = []

        # Compute charge using the absolute waveform
        for waveform in data["waveforms"]:
            voltage = np.abs((waveform - YOFF) * YMULT + YZERO)
            time = np.arange(len(voltage)) * XINCR
            charge = np.trapezoid(voltage, time)
            charges.append(charge)

        charges = np.array(charges)

        # Initial guess
        p0 = [
            (np.max(charges) - np.min(charges)) / 2,
            np.mean(y),
            0.1 * (np.max(y) - np.min(y)),
            np.mean(charges)
        ]

        # Fit
        popt, pcov = curve_fit(
            error_func,
            y,
            charges,
            p0=p0,
            maxfev=20000
        )

        sigma = popt[2]
        FWHM = 2.355 * sigma

        z_list.append(z)
        fwhm_list.append(FWHM)

        # Plot fit for this z
        x_fit = np.linspace(y.min(), y.max(), 500)
        y_fit = error_func(x_fit, *popt)

        plt.figure(figsize=(8, 4))
        plt.scatter(y, charges, label="Data")
        plt.plot(x_fit, y_fit, "r", label="Fit")
        plt.title(f"z = {z:.3f}, FWHM = {FWHM:.4f}")
        plt.xlabel("y")
        plt.ylabel("Charge")
        plt.grid(True)
        plt.legend()
        plt.show()

    # Plot FWHM vs z
    plt.figure(figsize=(8, 4))
    plt.scatter(z_list, fwhm_list)
    plt.plot(z_list, fwhm_list, "-")
    plt.xlabel("z")
    plt.ylabel("FWHM")
    plt.title("FWHM vs z")
    plt.grid(True)
    plt.show()

    return z_list, fwhm_list


def compute_max_sigma():
    from collections import defaultdict
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.optimize import curve_fit

    # Constants
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0

    # Group data by z position
    groups = defaultdict(lambda: {"x": [], "waveforms": []})

    for x, z, waveform in zip(x_positions, z_positions, waveforms):
        groups[z]["x"].append(x)
        groups[z]["waveforms"].append(waveform)

    results = []
 
    # Process each z group
    for z, data in sorted(groups.items()):

        x = np.array(data["x"])

        # Maximum voltage of each waveform
        voltages = np.array([
             np.max((wf - YOFF) * YMULT + YZERO)
         for wf in data["waveforms"]])

       # voltages[x < 4244] = 0.04
         

      

        # Make sure lengths match
        if len(x) != len(voltages):
            print(f"Skipping z={z}: x and voltages have different lengths.")
            continue

        # Initial parameter guesses
        p0 = [
            (voltages.max() - voltages.min()) / 2,   # amplitude
            np.mean(x),                              # center
            0.1 * (x.max() - x.min()),               # sigma
            np.mean(voltages)                        # offset
        ]

        try:
            popt, _ = curve_fit(
                error_func,
                x,
                voltages,
                p0=p0,
                maxfev=20000
            )

            sigma = abs(popt[2])
            FWHM = 2.355 * sigma

            results.append((z, FWHM))

            # Plot fit
            x_fit = np.linspace(x.min(), x.max(), 500)
            y_fit = error_func(x_fit, *popt)

            # plt.figure(figsize=(8,4))
            # plt.scatter(x, voltages, label="Data")
            # plt.plot(x_fit, y_fit, 'r', label="Fit")
            # plt.title(f"z = {z:.3f}, FWHM = {FWHM:.4f}")
            # plt.xlabel("x")
            # plt.ylabel("Maximum Voltage (V)")
            # plt.grid(True)
            # plt.legend()
            # plt.show()

        except RuntimeError:
            print(f"Fit failed for z = {z}")

    # Plot FWHM vs z
    if results:
        z_list = [r[0] for r in results]
        fwhm_list = [r[1] for r in results]

        plt.figure(figsize=(8,4))
        plt.scatter(z_list, fwhm_list)
        plt.plot(z_list, fwhm_list, '-')
        plt.xlabel("z")
        plt.ylabel("FWHM")
        plt.title("FWHM vs z")
        plt.grid(True)
        plt.show()

    return results
# def plot_heatmap_xy(mode="max"):
#     ys = []
#     zs = []
#     YMULT = 20e-3
#     YOFF = 0
#     YZERO = 0
#     values = []

#     for m, waveform in zip(measurements, waveforms):
#         voltage = (waveform - YOFF) * YMULT + YZERO

#         if mode == "max":
#             value = np.max(np.abs(voltage))
#             title = "XY Heatmap of Max |Voltage|"
#             cbar_label = "Max |Voltage| [V]"

#         elif mode == "mean":
#             value = np.mean(np.abs(voltage))
#             title = "XY Heatmap of Mean |Voltage|"
#             cbar_label = "Mean |Voltage| [V]"

#         else:
#             raise ValueError("mode must be 'max' or 'mean'")

#         ys.append(m["y"])
#         zs.append(m["z"])
#         values.append(value)

#     ys = np.round(np.array(ys), 6)
#     zs = np.round(np.array(zs), 6)
#     values = np.array(values)

#     y_unique = np.sort(np.unique(ys))
#     z_unique = np.sort(np.unique(zs))

#     Z = np.full((len(z_unique), len(y_unique)), np.nan)

#     for y, z, value in zip(ys, zs, values):
#         y_index = np.where(y_unique == y)[0][0]
#         z_index = np.where(z_unique == z)[0][0]

#         Z[z_index,y_index] = value

#     plt.figure(figsize=(8, 6))

#     img = plt.imshow(
#         Z,
#         origin="lower",
#         aspect="auto",
#         interpolation="nearest",
#         extent=[
#             y_unique.min(),
#             y_unique.max(),
#             z_unique.min(),
#             z_unique.max()
#         ],
#         cmap="viridis"
#     )

#     plt.colorbar(img, label=cbar_label)
#     plt.xlabel("x position")
#     plt.ylabel("y position")
#     plt.title(title)
#     plt.show()

   
def plot_max_voltage_map():
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    YMULT = 20e-3
    YOFF = 0
    YZERO = 0

    rows = []

    # Compute one value (maximum voltage) for each measurement
    for m, waveform in zip(measurements, waveforms):

        voltage = (waveform - YOFF) * YMULT + YZERO
        vmax = np.min(voltage)

        rows.append((m["y"], m["z"], vmax))

    # Create DataFrame
    df = pd.DataFrame(rows, columns=["y", "z", "Vpulse"])

    # Create 2D grid
    heat = df.pivot(index="y", columns="z", values="Vpulse")
    #heat = heat.fillna(0)
    y = np.sort(df["y"].unique())
    z = np.sort(df["z"].unique())
    print("Heatmap shape:", heat.shape)
    print("Unique y:", len(heat.columns), heat.columns.values)
    print("Unique z:", len(heat.index), heat.index.values)
      # Plot
    plt.figure(figsize=(8,6))
    plt.figure(figsize=(8,4))
    plt.imshow(
        heat.values.astype(float),
        origin="lower",
        aspect="auto",
        extent=[
            heat.columns.min(),
            heat.columns.max(),
            heat.index.min(),
            heat.index.max()
        ]
    )

    plt.colorbar(label="Maximum Voltage (V)")
    plt.xlabel("y (μm)")
    plt.ylabel("z (μm)")
    plt.title("Maximum Voltage Heatmap")

    plt.tight_layout()
    plt.show()
    
    
    
    # 
 


def plot_waveform(x_target, y_target, z_target):
   

    # Scope parameters (adjust if needed)
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds
    min_dist = float('inf')
    best_index = None
   
    for i, m in enumerate(measurements):
        
        dist = ( (m["x"] - float(x_target))**2 +
                 (m["y"] - float(y_target))**2 +
                 (m["z"] - float(z_target))**2 )
        if dist < min_dist:
            min_dist = dist
            best_index = i
            #print(  m["amplitude"],  m["area"])

     
    if best_index is None:
        print("No matching waveform found.")
        return None

    waveform = waveforms[best_index]

    voltage = (waveform - YOFF) * YMULT + YZERO
    time = np.arange(len(voltage)) * XINCR
   # dv_dt = np.gradient(voltage, time)
 
    plt.figure(figsize=(10,4))
    plt.plot(time, voltage)
    plt.title(f"Waveform near x={x_target}, y={y_target}, z={z_target}")
    plt.xlabel("Time [s]")
    plt.ylabel("Voltage [V]")
    plt.grid(True)
    plt.show()

def charge_calculation():
      # Scope parameters (adjust if needed)
  
    charges=[]
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds

    for i, waveform in enumerate(waveforms):
      
     voltage = (waveform - YOFF) * YMULT + YZERO
     time = np.arange(len(voltage)) * XINCR

     charge=trapezoidal_integration(voltage,time)
     charges.append(-charge)
    
    print(charges)
    plt.hist(charges, bins=4)
    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title("Histogram")
    plt.show()

def compute_max_voltage():
     # Scope parameters (adjust if needed)
    voltages=[]
    maximum=[]
    charges=[]
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds
    


    for i, waveform in enumerate(waveforms):
       voltage = (waveform - YOFF) * YMULT + YZERO
       print(f"Waveform {i}: max = {np.max(voltage)}")
       time = np.arange(len(voltage)) * XINCR

       charge=trapezoidal_integration(voltage,time)
       charges.append(charge)
    
       maximum.append(np.max(voltage))
       voltages.append(voltage)
    
    plt.figure(figsize=(10,4))
    plt.scatter(z_positions, charges)
    plt.xlabel("x")
    plt.ylabel("voltage [V]")
    plt.grid(True)
    plt.show()
  
def compute_max_charge(x_positions):
     # Scope parameters (adjust if needed)
    voltages=[]
    maximum=[]
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds
    


    for i, waveform in enumerate(waveforms):
       voltage = (waveform - YOFF) * YMULT + YZERO
       print(f"Waveform {i}: max = {np.max(voltage)}")
       maximum.append(np.max(voltage))
       voltages.append(voltage)
    
    # plt.figure(figsize=(10,4))
    # plt.scatter(x_positions, maximum)
    # plt.xlabel("x")
    # plt.ylabel("voltage [V]")
    # plt.grid(True)
    # plt.show()
   
    charges = []

    for waveform in waveforms:
     voltage = (waveform - YOFF) * YMULT + YZERO

     time = np.arange(len(voltage)) * XINCR

     charge = np.trapezoid(voltage, time)
     charges.append(charge)

    x_positions = np.array(x_positions)
    charges = np.array(charges)

    p0 = [ (np.max(charges) - np.min(charges)) / 2,  # A
           np.mean(x_positions),                     # x0
           0.1 * (np.max(x_positions) - np.min(x_positions)),  # sigma
         np.mean(charges)                          # B
        ]
    
    popt, pcov = curve_fit(error_func,  x_positions,  charges,  p0=p0,  maxfev=20000 )
    x_fit = np.linspace(min(x_positions), max(x_positions), 1000)
    y_fit = error_func(x_fit, *popt)

    plt.figure(figsize=(10,4))
    plt.scatter(x_positions, charges, label="Data")
    plt.plot(x_fit, y_fit, 'r-', label="erf fit")

    plt.xlabel("x position")
    plt.ylabel("charge")
    plt.legend()
    plt.grid()
    plt.show()
    sigma = popt[2]
    FWHM = 2.355 * sigma
    print("FWHM =", FWHM)   
    
    
    
    
def waveform_to_voltage(waveform):
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    return (waveform - YOFF) * YMULT + YZERO

def get_plane_coordinates(m, plane):
    if plane == "xy":
        return m["x"], m["y"], "x position", "y position"

    elif plane == "xz":
        return m["x"], m["z"], "x position", "z position"

    elif plane == "yz":
        return m["y"], m["z"], "y position", "z position"

    else:
        raise ValueError("plane must be 'xy', 'xz', or 'yz'")



def plot_heatmap(mode="max", plane="xy"):
    a_positions = []
    b_positions = []
    values = []

    for m, waveform in zip(measurements, waveforms):
        voltage = waveform_to_voltage(waveform)

        if mode == "max":
            value = np.max(np.abs(voltage))
            title_quantity = "Max |Voltage|"
            value_label = "Max |Voltage| [V]"

        elif mode == "mean":
            value = np.mean(np.abs(voltage))
            title_quantity = "Mean |Voltage|"
            value_label = "Mean |Voltage| [V]"

        else:
            raise ValueError("mode must be 'max' or 'mean'")

        a, b, a_label, b_label = get_plane_coordinates(m, plane)

        a_positions.append(a)
        b_positions.append(b)
        values.append(value)

    a_positions = np.round(np.array(a_positions, dtype=float), 6)
    b_positions = np.round(np.array(b_positions, dtype=float), 6)
    values = np.array(values, dtype=float)

    mask = (
        np.isfinite(a_positions) &
        np.isfinite(b_positions) &
        np.isfinite(values)
    )

    a_positions = a_positions[mask]
    b_positions = b_positions[mask]
    values = values[mask]

    if len(values) == 0:
        print("No valid data points found.")
        return

    a_unique = np.sort(np.unique(a_positions))
    b_unique = np.sort(np.unique(b_positions))

    print("Number of points:", len(values))
    print(f"Unique {a_label}:", len(a_unique))
    print(f"Unique {b_label}:", len(b_unique))

    a_to_index = {a: i for i, a in enumerate(a_unique)}
    b_to_index = {b: i for i, b in enumerate(b_unique)}

    strip_width = 1.0

    if len(a_unique) > 1 and len(b_unique) == 1:
        Z = np.full((1, len(a_unique)), np.nan)

        for a, value in zip(a_positions, values):
            a_index = a_to_index[a]
            Z[0, a_index] = value

        b0 = b_unique[0]

        plt.figure(figsize=(8, 2.5))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a_unique.min(),
                a_unique.max(),
                b0 - strip_width / 2,
                b0 + strip_width / 2
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)
        plt.yticks([b0], [f"{b0:g}"])
        plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
        plt.show()
        return

    if len(a_unique) == 1 and len(b_unique) > 1:
        Z = np.full((len(b_unique), 1), np.nan)

        for b, value in zip(b_positions, values):
            b_index = b_to_index[b]
            Z[b_index, 0] = value

        a0 = a_unique[0]

        plt.figure(figsize=(3.5, 6))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a0 - strip_width / 2,
                a0 + strip_width / 2,
                b_unique.min(),
                b_unique.max()
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)
        plt.xticks([a0], [f"{a0:g}"])
        plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
        plt.show()
        return

    
    if len(a_unique) == 1 and len(b_unique) == 1:
        Z = np.array([[values[0]]])

        a0 = a_unique[0]
        b0 = b_unique[0]

        plt.figure(figsize=(4, 4))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a0 - strip_width / 2,
                a0 + strip_width / 2,
                b0 - strip_width / 2,
                b0 + strip_width / 2
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)

        
        plt.xticks([a0], [f"{a0:g}"])
        plt.yticks([b0], [f"{b0:g}"])

        plt.title(f"{plane.upper()} Heatmap - Single Point - {title_quantity}")
        plt.show()
        return

    
    Z = np.full((len(b_unique), len(a_unique)), np.nan)

    for a, b, value in zip(a_positions, b_positions, values):
        a_index = a_to_index[a]
        b_index = b_to_index[b]
        Z[b_index, a_index] = value

    plt.figure(figsize=(8, 6))

    img = plt.imshow(
        Z,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=[
            a_unique.min(),
            a_unique.max(),
            b_unique.min(),
            b_unique.max()
        ],
        cmap="viridis"
    )

    plt.colorbar(img, label=value_label)
    plt.xlabel(a_label)
    plt.ylabel(b_label)
    plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
    plt.show()
    

def plot_integral_heatmap(plane="xy", use_charge=False ):
    a_positions = []
    b_positions = []
    values = []

    XINCR = 20e-12

    for m, waveform in zip(measurements, waveforms):
        voltage = waveform_to_voltage(waveform)
        time = np.arange(len(voltage)) * XINCR

        integral = np.trapezoid(np.abs(voltage), time)

        if use_charge:
            value = integral  
            title_quantity = "Integrated Absolute Charge"
            value_label = "Integrated |Charge| [C]"
        else:
            value = integral
            title_quantity = "Integrated Absolute Voltage"
            value_label = "Integrated |Voltage| [V·s]"

        a, b, a_label, b_label = get_plane_coordinates(m, plane)

        a_positions.append(a)
        b_positions.append(b)
        values.append(value)

    a_positions = np.round(np.array(a_positions, dtype=float), 6)
    b_positions = np.round(np.array(b_positions, dtype=float), 6)
    values = np.array(values, dtype=float)

    mask = (
        np.isfinite(a_positions) &
        np.isfinite(b_positions) &
        np.isfinite(values)
    )

    a_positions = a_positions[mask]
    b_positions = b_positions[mask]
    values = values[mask]

    if len(values) == 0:
        print("No valid data points found.")
        return

    a_unique = np.sort(np.unique(a_positions))
    b_unique = np.sort(np.unique(b_positions))

    print("Number of points:", len(values))
    print(f"Unique {a_label}:", len(a_unique))
    print(f"Unique {b_label}:", len(b_unique))

    a_to_index = {a: i for i, a in enumerate(a_unique)}
    b_to_index = {b: i for i, b in enumerate(b_unique)}

    
    strip_width = 1.0

    
    if len(a_unique) > 1 and len(b_unique) == 1:
        Z = np.full((1, len(a_unique)), np.nan)

        for a, value in zip(a_positions, values):
            a_index = a_to_index[a]
            Z[0, a_index] = value

        b0 = b_unique[0]

        plt.figure(figsize=(8, 2.5))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a_unique.min(),
                a_unique.max(),
                b0 - strip_width / 2,
                b0 + strip_width / 2
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)

        
        plt.yticks([b0], [f"{b0:g}"])

        plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
        plt.show()
        return

   
    if len(a_unique) == 1 and len(b_unique) > 1:
        Z = np.full((len(b_unique), 1), np.nan)

        for b, value in zip(b_positions, values):
            b_index = b_to_index[b]
            Z[b_index, 0] = value

        a0 = a_unique[0]

        plt.figure(figsize=(3.5, 6))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a0 - strip_width / 2,
                a0 + strip_width / 2,
                b_unique.min(),
                b_unique.max()
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)

        
        plt.xticks([a0], [f"{a0:g}"])

        plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
        plt.show()
        return

    
    if len(a_unique) == 1 and len(b_unique) == 1:
        Z = np.array([[values[0]]])

        a0 = a_unique[0]
        b0 = b_unique[0]

        plt.figure(figsize=(4, 4))

        img = plt.imshow(
            Z,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=[
                a0 - strip_width / 2,
                a0 + strip_width / 2,
                b0 - strip_width / 2,
                b0 + strip_width / 2
            ],
            cmap="viridis"
        )

        plt.colorbar(img, label=value_label)
        plt.xlabel(a_label)
        plt.ylabel(b_label)

        
        plt.xticks([a0], [f"{a0:g}"])
        plt.yticks([b0], [f"{b0:g}"])

        plt.title(f"{plane.upper()} Heatmap - Single Point - {title_quantity}")
        plt.show()
        return

    
    Z = np.full((len(b_unique), len(a_unique)), np.nan)

    for a, b, value in zip(a_positions, b_positions, values):
        a_index = a_to_index[a]
        b_index = b_to_index[b]
        Z[b_index, a_index] = value

    plt.figure(figsize=(8, 6))

    img = plt.imshow(
        Z,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=[
            a_unique.min(),
            a_unique.max(),
            b_unique.min(),
            b_unique.max()
        ],
        cmap="viridis"
    )

    plt.colorbar(img, label=value_label)
    plt.xlabel(a_label)
    plt.ylabel(b_label)
    plt.title(f"{plane.upper()} Heatmap - {title_quantity}")
    plt.show()




  
def compute_max():
     # Scope parameters (adjust if needed)
    voltages=[]
    maximum=[]
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds
   
    for i, waveform in enumerate(waveforms):
       voltage = (waveform - YOFF) * YMULT + YZERO
       print(f"Waveform {i}: max = {np.max(voltage)}")
       maximum.append(np.min(voltage))
       voltages.append(voltage)
    
    
    plt.figure(figsize=(10,4))
    plt.scatter(z_positions, maximum)
    plt.xlabel("z")
    plt.ylabel("Voltage [V]")
    plt.grid(True)
    plt.show()

def max_histo():
     # Scope parameters (adjust if needed)
    voltages=[]
    maximum=[]
    YMULT = 20e-3
    YOFF = 0
    YZERO = 0
    XINCR = 20e-12  # sampling interval in seconds

    for i, waveform in enumerate(waveforms):
       voltage = (waveform - YOFF) * YMULT + YZERO
       print(f"Waveform {i}: max = {np.max(voltage)}")
       maximum.append(np.max(voltage))
       voltages.append(voltage)

    plt.hist(maximum,bins=20)
    plt.xlabel("Value")
     
    plt.ylabel("Frequency")
    plt.title("Histogram")
    plt.show()



def gaussian_fit_histo( ):
    voltages = []
    maximum = []

    YMULT = 20e-3
    YOFF = 0
    YZERO = 0

    # ---------------------------
    # 1. Extract maxima
    # ---------------------------
    for i, waveform in enumerate(waveforms):
        voltage = (waveform - YOFF) * YMULT + YZERO

        max_val = np.max(voltage)
        maximum.append(max_val)
        voltages.append(voltage)

    maximum = np.array(maximum)

    print("N waveforms:", len(maximum))
    print("Mean:", np.mean(maximum))
    print("Std:", np.std(maximum))

    # ---------------------------
    # 2. Histogram
    # ---------------------------
    counts, bins = np.histogram(maximum, bins=20)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    # remove empty bins
    mask = counts > 0

    # ---------------------------
    # 3. Initial guesses (SAFE)
    # ---------------------------
    mu0 = np.mean(maximum)
    sigma0 = np.std(maximum)

    if sigma0 == 0 or np.isnan(sigma0):
        sigma0 = 1e-6

    p0 = [np.max(counts), mu0, sigma0]

    # ---------------------------
    # 4. Fit (robust settings)
    # ---------------------------
    try:
        popt, pcov = curve_fit(
            gaussian,
            bin_centers[mask],
            counts[mask],
            p0=p0,
            maxfev=20000,
            bounds=(
                [0, min(maximum), 0],
                [np.inf, max(maximum), np.inf]
            )
        )
    except RuntimeError:
        print("Fit failed — returning None")
        return None

    A_fit, mu_fit, sigma_fit = popt

    # ---------------------------
    # 5. Plot
    # ---------------------------
    plt.hist(maximum, bins=20, alpha=0.6, label="Data")

    x_fit = np.linspace(min(maximum), max(maximum), 1000)
    y_fit = gaussian(x_fit, *popt)

    plt.plot(x_fit, y_fit, 'r-', linewidth=2,
             label=f"μ={mu_fit:.4f}, σ={sigma_fit:.4f}")

    plt.xlabel("Maximum Voltage (V)")
    plt.ylabel("Counts")
    plt.title("Gaussian Fit of Waveform Peaks")
    plt.legend()
    plt.grid()
    plt.show()

    print(f"μ = {mu_fit:.6f} V")
    print(f"σ = {sigma_fit:.6f} V")
    print(f"FWHM = {2.355 * sigma_fit:.6f} V")

    return popt, pcov

if __name__ == "__main__":

#     read(file_path = r"C:\Users\ehep\Documents\TCT\ScanningFiles\Diode_Cnm_LaserOn.bin")
    #  for i in range(250):
    #     print(f"{measurements[i]["x"]}")
    #   compute_max_charge_all_z()
    #     plot_waveform(f"{measurements[i]["x"]}",f"{measurements[i]["y"]}",f"{measurements[i]["z"]}")
   
   # compute_max_charge(x_positions)
     #results = compute_max_charge_all_z(x_positions,z_positions)
   # plot_max_voltage_map()
   ## gaussian_fit_histo()

   #compute_max_sigma()
   compute_max_charge_all_z()
# For x,y SCAN only ( Mapping )
   # plot_charge_heatmap_xy(use_charge=True,resistance=50)
     #plot_max_voltage_map()
  #  plot_heatmap(mode="max" , plane="yz")
  #  plot_heatmap(mode="mean" , plane="xz")
    # plot_integral_heatmap(plane="xy", use_charge=True)

# -------------------------------------------------------------------------
# Duplicate/shadowed definitions below - each of these functions was defined
# TWICE earlier in this file under the same name. Python silently kept only
# the LATER definition (the one still active above); these earlier versions
# were dead code (never reachable) and are kept here only for reference.
# -------------------------------------------------------------------------

# def plot_waveform(x_target, y_target, z_target):
#     # Scope parameters (adjust if needed)
#     YMULT = 20e-3
#     YOFF = 0
#     YZERO = 0
#     XINCR = 20e-12  # sampling interval in seconds
#     min_dist = float('inf')
#     best_index = None
#
#     for i, m in enumerate(measurements):
#         dist = ( (m["x"] - float(x_target))**2 +
#                  (m["y"] - float(y_target))**2 +
#                  (m["z"] - float(z_target))**2 )
#         if dist < min_dist:
#             min_dist = dist
#             best_index = i
#
#     if best_index is None:
#         print("No matching waveform found.")
#         return None
#
#     waveform = waveforms[best_index]
#     voltage = (waveform - YOFF) * YMULT + YZERO
#     time = np.arange(len(voltage)) * XINCR
#
#     plt.figure(figsize=(10,4))
#     plt.plot(time, voltage)
#     plt.title(f"Waveform near x={x_target}, y={y_target}, z={z_target}")
#     plt.xlabel("Time [s]")
#     plt.ylabel("Voltage [V]")
#     plt.grid(True)
#     plt.show()
#     # identical to the active plot_waveform() defined later in this file

# def charge_calculation():
#     charges=[]
#     YMULT = 20e-3
#     YOFF = 0
#     YZERO = 0
#     XINCR = 20e-12  # sampling interval in seconds
#
#     for i, waveform in enumerate(waveforms):
#      voltage = (waveform - YOFF) * YMULT + YZERO
#      time = np.arange(len(voltage)) * XINCR
#      charge=trapezoidal_integration(voltage,time)
#      charges.append(-charge)
#
#     print(charges)
#     plt.hist(charges, bins=4)
#     plt.xlabel("Value")
#     plt.ylabel("Frequency")
#     plt.title("Histogram")
#     plt.show()
#     # identical to the active charge_calculation() defined later in this file

# def compute_max_voltage():
#     # NOTE: differs from the active compute_max_voltage() defined later -
#     # this earlier version scatter-plots x_positions vs max voltage per
#     # waveform. The active (later) version instead computes charge and
#     # plots z_positions vs charges, but keeps the same "x"/"voltage [V]"
#     # axis labels - likely a leftover mislabeling worth checking.
#     voltages=[]
#     maximum=[]
#     YMULT = 20e-3
#     YOFF = 0
#     YZERO = 0
#     XINCR = 20e-12  # sampling interval in seconds
#
#     for i, waveform in enumerate(waveforms):
#        voltage = (waveform - YOFF) * YMULT + YZERO
#        print(f"Waveform {i}: max = {np.max(voltage)}")
#        maximum.append(np.max(voltage))
#        voltages.append(voltage)
#
#     plt.figure(figsize=(10,4))
#     plt.scatter(x_positions, maximum)
#     plt.xlabel("x")
#     plt.ylabel("voltage [V]")
#     plt.grid(True)
#     plt.show()

# def compute_max_charge(x_positions):
#     # NOTE: identical to the active compute_max_charge() defined later,
#     # except the active version has the "scatter x_positions vs maximum"
#     # plot block commented out (skips straight to the charge/erf-fit part).
#     voltages=[]
#     maximum=[]
#     YMULT = 20e-3
#     YOFF = 0
#     YZERO = 0
#     XINCR = 20e-12  # sampling interval in seconds
#
#     for i, waveform in enumerate(waveforms):
#        voltage = (waveform - YOFF) * YMULT + YZERO
#        print(f"Waveform {i}: max = {np.max(voltage)}")
#        maximum.append(np.max(voltage))
#        voltages.append(voltage)
#
#     plt.figure(figsize=(10,4))
#     plt.scatter(x_positions, maximum)
#     plt.xlabel("x")
#     plt.ylabel("voltage [V]")
#     plt.grid(True)
#     plt.show()
#
#     charges = []
#     for waveform in waveforms:
#      voltage = (waveform - YOFF) * YMULT + YZERO
#      time = np.arange(len(voltage)) * XINCR
#      charge = np.trapezoid(voltage, time)
#      charges.append(charge)
#
#     x_positions = np.array(x_positions)
#     charges = np.array(charges)
#
#     p0 = [ (np.max(charges) - np.min(charges)) / 2,  # A
#            np.mean(x_positions),                     # x0
#            0.1 * (np.max(x_positions) - np.min(x_positions)),  # sigma
#          np.mean(charges)                          # B
#         ]
#
#     popt, pcov = curve_fit(error_func,  x_positions,  charges,  p0=p0,  maxfev=20000 )
#     x_fit = np.linspace(min(x_positions), max(x_positions), 1000)
#     y_fit = error_func(x_fit, *popt)
#
#     plt.figure(figsize=(10,4))
#     plt.scatter(x_positions, charges, label="Data")
#     plt.plot(x_fit, y_fit, 'r-', label="erf fit")
#     plt.xlabel("x position")
#     plt.ylabel("charge")
#     plt.legend()
#     plt.grid()
#     plt.show()
#     sigma = popt[2]
#     FWHM = 2.355 * sigma
#     print("FWHM =", FWHM)
