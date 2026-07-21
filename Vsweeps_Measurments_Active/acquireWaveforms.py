import time
import logging

#import MALTA_PSU
import numpy as np
#from SerialCom import SerialCom
from datetime import datetime
import os
import sys
logger = logging.getLogger(__name__)
import matplotlib.pyplot as plt

# Add the 'sic-analysis' directory to the Python path
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'share')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sic-analysis')))

# Add sibling folders (created when this project was categorized into subfolders) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'power_supply_control')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'oscilloscope_control')))

# import power supply
from power_supply import PSU

#osc control
import tektronix

#from plot_wf import loadconfig
#from log import logger, ch

# Set this to your config and IP address
CONFIG_PATH = "./configs/cassia_example_settings.yml"
OSC_IP = "USB0::0x0699::0x0530::C064620::INSTR" #On OSC check utility -> I/O

OSC_CONFIG_JSON = r"C:\Users\ehep\tctsw\tctfw\OscControl\Diode.json"  # Αρχείο με τις παραμέτρους του παλμογράφου (setup_from_json) - εδώ ορίζεται π.χ. το time window
WAVEFORM_LENGTH = 1000  # Μήκος κυματομορφής (samples) που διαβάζουμε από τον παλμογράφο - ΠΡΟΣΟΧΗ: αν αλλάξεις το time window στο OSC_CONFIG_JSON, πρέπει να αλλάξεις ΚΑΙ αυτό, γιατί καθορίζει τα άκρα ολοκληρώματος για το charge από έναν παλμό

# ---------------------------------
# Scan parameters
# ---------------------------------
V_start = 0            # Τάση εκκίνησης (V)
V_end = -60             # Τάση τερματισμού (V)
V_step = 1              # Μέγεθος βήματος τάσης (V) - το πρόσημο προσαρμόζεται αυτόματα ανάλογα με την κατεύθυνση

t_settle = 10           # Χρόνος αναμονής (sec) ΜΕΤΑ την αλλαγή τάσης και ΠΡΙΝ την απόκτηση κυματομορφών
t_between_steps = 2     # Χρόνος αναμονής (sec) ΜΕΤΑ την απόκτηση και ΠΡΙΝ αλλάξει ξανά η τάση
t_ramp_step_delay = 2   # Χρόνος αναμονής (sec) ανάμεσα σε κάθε ενδιάμεσο βήμα του 1V - εδώ χρησιμοποιείται σε ΚΑΘΕ αλλαγή τάσης, όχι μόνο στην πρώτη
I_compliance = 1E-4     # Compliance ρεύματος (A) - ΠΡΟΣΟΧΗ: δεν εφαρμόζεται ακόμα, το psu.setMaxCurrent() για k_6517B είναι σπασμένο στο power_supply.py (task #13)

MATRIX = "M3_central"
#outputPath = "F:/CASSIA/OnlyCentralBiased/" #output path in the oscilloscope
outputPath="C:/Users/ehep/Desktop/iv_exec/LGADS_TCTboard_IV_Gain"
signalChannel= "CH3" # the channel connected to the sensor
signalChannel_2 = "CH4"
dosisgnalChannel_2 = False
specialDesc = "LaserOn" #special describtion for output # can be laserOn, CC
# ---------------------------------

step_signed = abs(V_step) if V_end >= V_start else -abs(V_step)
voltages = np.arange(V_start, V_end + step_signed, step_signed).tolist()
voltages = [round(v, 6) for v in voltages]

# Power supply init
psu = PSU()
PSName = "k_6517B"
target = "NW"
psu.addPSU(target, 103, str(PSName))
#fIlim = 1E-6

def set_bias_voltage(voltage, step=1, ramp_delay=t_ramp_step_delay, settle_time=2, max_retries=3, tolerance=0.5):
    """
    Ramps up/down the bias voltage to a specified target value, with retry on failure.

    Parameters:
    - voltage (float): Target bias voltage in volts.
    - step (float): Voltage increment per step.
    - ramp_delay (float): Time in seconds to wait between each intermediate ramp step.
    - settle_time (float): Time in seconds to wait after reaching target voltage.
    - max_retries (int): Maximum number of attempts in case of failure.
    - tolerance (float): Allowed deviation from target voltage.
    """
    for attempt in range(1, max_retries + 1):
        try:
            current_voltage = psu.getVoltage(target)
            logger.info(f"[Attempt {attempt}] Current voltage: {current_voltage:.2f} V. Ramping to {voltage:.2f} V...")

            # Decide ramp direction
            if current_voltage < voltage:
                logger.info("Ramping UP voltage...")
                psu.rampUpVoltage(psuSelected=target, startVoltage=current_voltage, endVoltage=voltage, step=step, delay=ramp_delay)
            else:
                logger.info("Ramping DOWN voltage...")
                psu.rampDownVoltage(psuSelected=target, startVoltage=current_voltage, endVoltage=voltage, step=step, delay=ramp_delay)

            logger.info(f"Voltage ramp completed. Waiting {settle_time}s for stabilization...")
            time.sleep(settle_time)

            final_voltage = psu.getVoltage(target)
            if abs(final_voltage - voltage) <= tolerance:
                logger.info(f"Voltage stabilized at {final_voltage:.2f} V.")
                return
            else:
                logger.warning(f"Voltage {final_voltage:.2f} V is outside tolerance ({tolerance} V). Retrying...")

        except Exception as e:
            logger.error(f"[Attempt {attempt}] Error setting voltage: {e}")

        time.sleep(1)  # Small delay before retrying

    logger.critical(f"Failed to set voltage to {voltage:.2f} V after {max_retries} attempts.")
    raise RuntimeError(f"Voltage setting failed for {voltage:.2f} V")


# Setup logger
logger.setLevel(logging.INFO)
#ch.setLevel(logging.INFO)

# Load config
#config = loadconfig(CONFIG_PATH)
#logger.info("Config loaded.")

# Connect to oscilloscope
#osc_0 = osccontrol.TektronixMSO(OSC_IP)
scope =tektronix.TektronixMSO(OSC_IP)
time.sleep(1)
#osc.reset_instrument()
#osc.load_setup("C:/cassia_settings.set")
time.sleep(2)
measurements=[]
scope.setup_from_json(OSC_CONFIG_JSON)  # measurement channel, timebase, trigger, etc. all come from this JSON now
# Voltage loop
try:
    for voltage in voltages:
        set_bias_voltage(voltage)
        time.sleep(t_settle)

        area_readings = []
        for i in range(2):  # Take two measurements per voltage
            # Clear and acquire
           # scope.reset_instrument()
            scope.control_acquisition("on")
            logger.info(f"Acquisition {i+1}/2 started at {voltage} V.")
            time.sleep(2)

            scope.oscilloscope.write('ACQ:STATE RUN')
            meas_data =scope.measurement_read()

            data_waveform = scope.read_waveform_buffer("ch3", WAVEFORM_LENGTH)
            logger.info(f"Acquisition {i+1}/2 started at {voltage} V.")
            wf_filename = f"waveform_{voltage}_{i}.npy"
            np.save(f"{outputPath}/{wf_filename}", data_waveform)

            area_readings.append(meas_data[1])

          #  time.sleep(2)
             # while osc.check_acq():
            #     num_acq = osc.get_num_acq()
            #     logger.info("Current acquisitions: %s", num_acq)
            #     time.sleep(2)

            # Save waveform
            filename = f"{MATRIX}.{voltage}.{specialDesc}_{i}"
           # osc.save_to_wfm(filename, outputPath, signalChannel)
            logger.info(f"Saved waveform {i+1}/2 for {voltage} V")

            # if dosisgnalChannel_2:
            #     filename = f"{MATRIX}.OtherPixels.{voltage}.{specialDesc}_{i}"
            #     osc.save_to_wfm(filename, outputPath, signalChannel_2)
            #     logger.info(f"Saved waveform {i+1}/2 for {voltage} V for Channel {signalChannel_2}")

        # Average the 2 measurements at this voltage into a single data point
        measurements.append({
          "voltage": voltage,
          # "max_amp": meas_data[0],
           "area_charge": float(np.mean(area_readings)),
             "waveform_file": wf_filename
              })

        time.sleep(t_between_steps)

finally:
    logger.info("Powering Off PS")
    try:
        set_bias_voltage(0)
    except Exception as e:
        logger.error(f"Failed to power down safely: {e}")
    try:
        scope.close_connection()
    except Exception as e:
        logger.error(f"Failed to close oscilloscope connection: {e}")
    logger.info("Voltage scan complete.")

measured_voltages = np.array([m["voltage"] for m in measurements])
#max_amp = np.array([m["max_amp"] for m in measurements])
area = np.array([m["area_charge"] for m in measurements])
waveforms = [np.load(f"{outputPath}/{m['waveform_file']}") for m in measurements]
data = np.column_stack((measured_voltages, area))

np.savetxt(
    f"{outputPath}/testwierd.txt",
    data,
    header="Voltage[V] MaxAmp AreaCharge",
    fmt="%.6e"
)

#np.savez(f"{outputPath}/PulseVoltage.npz",
     #    voltage=voltages,
     ##    max_amp=max_amp,
       #  area_charge=area,
       #  waveforms=waveforms)


# plt.figure()
# plt.plot(voltages, max_amp/max_amp[0], marker='o')
# plt.xlabel("Voltage (V)")
# plt.ylabel("Max Amplitude")
# plt.title(f"gain Curve - {MATRIX} ({specialDesc})")
# plt.grid(True)

# plot_file = f"{outputPath}/IV_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
# plt.savefig(plot_file, dpi=300)

# logger.info(f"Saved IV curve to {plot_file}")
# plt.show()

# plt.figure()
# plt.plot(voltages, max_amp/0.0047 , marker='o')
# plt.xlabel("Voltage (V)")
# plt.ylabel("gain")
# plt.title(f"amp gain Curve - {MATRIX} ({specialDesc})")
# plt.grid(True)

# plot_file = f"{outputPath}/IV_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
# plt.savefig(plot_file, dpi=300)

# logger.info(f"Saved  curve to {plot_file}")
# plt.show()




plt.figure()
plt.plot(measured_voltages, area/area[0], marker='o')
plt.xlabel("Voltage (V)")
plt.ylabel("gain")
plt.title(f" charge gain Curve - {MATRIX} ({specialDesc})")
plt.grid(True)

plot_file = f"{outputPath}/IV_curve_norm0_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(plot_file, dpi=300)

logger.info(f"Saved IV curve to {plot_file}")
plt.show()


plt.figure()
plt.plot(measured_voltages, area/area[25], marker='o')
plt.xlabel("Voltage (V)")
plt.ylabel("gain")
plt.title(f" charge gain Curve - {MATRIX} ({specialDesc})")
plt.grid(True)

plot_file = f"{outputPath}/IV_curve_norm25_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
plt.savefig(plot_file, dpi=300)

logger.info(f"Saved IV curve to {plot_file}")
plt.show()

# plt.figure()
# plt.plot(voltages, area/0.0000000016, marker='o')
# plt.xlabel("Voltage (V)")
# plt.ylabel("gain")
# plt.title(f" charge gain curve - {MATRIX} ({specialDesc})")
# plt.grid(True)

# plot_file = f"{outputPath}/IV_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
# plt.savefig(plot_file, dpi=300)

# logger.info(f"Saved IV curve to {plot_file}")
# plt.show()
