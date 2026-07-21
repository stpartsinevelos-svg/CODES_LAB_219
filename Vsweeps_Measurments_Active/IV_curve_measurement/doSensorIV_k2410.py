#!/usr/bin/env python
import os
import time
import math
import numpy as np
import matplotlib.pyplot as plt
# import Keithley
# import ROOT
#from ROOT import TCanvas, TFile, TH1F, TH2F, gStyle, TGraph, TTree
# import MALTA_PSU
# from SerialCom import SerialCom
# import pymeasure
# from pymeasure.instruments.keithley import Keithley6517B
from datetime import datetime

# import power supply
from power_supply import PSU

# Main part starts here
if __name__ == "__main__":

    psu = PSU()
    PSName = "k_2410" 
    target = "NW"
    psu.addPSU(target, 100, str(PSName))
    fIlim = 1E-6           # Λογισμικό όριο ρεύματος (A) - αν ξεπεραστεί, το script σταματάει τη μέτρηση
    I_compliance = 1E-4    # Compliance ρεύματος (A) - hardware όριο που θέτει το ίδιο το τροφοδοτικό, ανεξάρτητα από το πόσο συχνά διαβάζουμε
    dataPath = "DATA/"
    os.makedirs(dataPath, exist_ok=True)

    # Set auto range
 
    #M1: 25 - 120
    #M2: 25-80 V
    #M3: 80-130 V
    #M4: 80-130 V
    #S5: 20-80V

    # Define voltage sweep range (V_start/V_end/V_step may be negative and/or decimal)
    V_start = 0          # Τάση εκκίνησης (V)
    V_end = 100           # Τάση τερματισμού (V)
    V_step = 2            # Μέγεθος βήματος τάσης (V) - το πρόσημο προσαρμόζεται αυτόματα ανάλογα με την κατεύθυνση

    t_settle = 2          # Χρόνος αναμονής (sec) ΜΕΤΑ την αλλαγή τάσης και ΠΡΙΝ τη μέτρηση
    t_between_steps = 2   # Χρόνος αναμονής (sec) ΜΕΤΑ τη μέτρηση και ΠΡΙΝ ανέβει ξανά η τάση
    t_ramp_step_delay = 1 # Χρόνος αναμονής (sec) ανάμεσα σε κάθε ενδιάμεσο βήμα του 1V όταν η τάση ανεβαίνει/κατεβαίνει σταδιακά (π.χ. αρχικό ανέβασμα αν V_start != 0, ή τελικό γύρισμα στο 0V)

    step_signed = abs(V_step) if V_end >= V_start else -abs(V_step)
    voltages = np.arange(V_start, V_end + step_signed, step_signed).tolist()
    voltages = [round(v, 6) for v in voltages]
    print(voltages)

    # psu.setMaxVoltage(target, V_end+20)

    # Number of measurements per point
    N = 2

    # Initialize lists to store results
    current_values = []

    def set_bias_voltage(voltage, step=1.0, ramp_delay=t_ramp_step_delay, settle_time=2, max_retries=3, tolerance=0.5):
        """
        Ramps up/down the bias voltage to a specified target value, with retry on failure.
        """
        for attempt in range(1, max_retries + 1):
            try:
                current_voltage = psu.getVoltage(target)
                print(f"[Attempt {attempt}] Current voltage: {current_voltage:.2f} V. Ramping to {voltage:.2f} V...")

                if current_voltage < voltage:
                    psu.rampUpVoltage(psuSelected=target, startVoltage=current_voltage, endVoltage=voltage, step=step, delay=ramp_delay)
                elif current_voltage > voltage:
                    psu.rampDownVoltage(psuSelected=target, startVoltage=current_voltage, endVoltage=voltage, step=step, delay=ramp_delay)

                time.sleep(settle_time)

                final_voltage = psu.getVoltage(target)
                if abs(final_voltage - voltage) <= tolerance:
                    print(f"Voltage stabilized at {final_voltage:.2f} V.")
                    return
                else:
                    print(f"Voltage {final_voltage:.2f} V outside tolerance ({tolerance} V). Retrying...")

            except Exception as e:
                print(f"[Attempt {attempt}] Error setting voltage: {e}")

            time.sleep(1)

        print(f"Failed to set voltage to {voltage:.2f} V after {max_retries} attempts.")
        raise RuntimeError(f"Voltage setting failed for {voltage:.2f} V")

    try:
        psu.enable(target)
        psu.setMaxCurrent(target, I_compliance)
        psu.setAutoRange(target)

        # Loop through each voltage, set it, and measure current
        for voltage in voltages:
            set_bias_voltage(voltage)
            time.sleep(t_settle)

            #if voltage == 0: # do not measure V=0 #18.07
            #	time.sleep(840)

            # Take N measurements for the current
            measurements = []
            for _ in range(N):
                
                time.sleep(1)#0.7 2
                current = psu.getCurrent(target)
                # Skip if the current is None or not a valid float
                if current is None or not isinstance(current, (float, int)) or math.isnan(current):
                    print("Invalid current measurement. Skipping.")
                    continue

                measurements.append(abs(current))

                if abs(current) > fIlim:
                    print('Software Limit reached!')
                    break
            
            # Calculate average and standard deviation of the current measurements
            average_current = np.mean(measurements)
            if N > 1:
                uncertainty = np.std(measurements, ddof=1)  # Standard deviation with Bessel's correction
            else:
                uncertainty = 0

            # Print the results
            print(f"Voltage: {voltage}V, Average Current: {average_current:.3e}A, Uncertainty: {uncertainty:.3e}A")

            # Store data
            current_values.append((voltage, average_current, uncertainty))

            # Break the outer loop if limit exceeded
            if abs(average_current) > fIlim:
                print('Software Limit reached!')
                break

            time.sleep(t_between_steps)

    except (KeyboardInterrupt, SystemExit):
        print('Measurement was terminated...')
    finally:
        # Ensure the PSU is safely ramped down and disabled after measurement
        print("Powering Off PS")
        try:
            set_bias_voltage(0)
        except Exception as e:
            print(f"Warning: Failed to power down safely: {e}")
        psu.disable(target)

    # Print  results
    print("IV Measurement Results:")
    for voltage, avg_current, uncertainty in current_values:
        print(f"Voltage: {voltage} V, Average Current: {avg_current:.3e} A, Uncertainty: {uncertainty:.3e} A")

    # Root analysis
    # First Save results to a text file

    now= datetime.now()
    #print(now)
    dt_string = now.strftime("%d%m%Y_%H%M%S")
    print(f"Measurement identifible by {dt_string}")
    
    outName = f"IV_Measurement_{dt_string}"
    with open(f"{dataPath}/{outName}.txt", "w") as file:
        file.write("Voltage (V)\tAverage Current (A)\tUncertainty (A)\n")
        for voltage, avg_current, uncertainty in current_values:
            file.write(f"{voltage}\t{avg_current:.3e}\t{uncertainty:.3e}\n")
    
    arr = np.array(current_values)

    # Remove rows with NaN (important!)
    arr = arr[~np.isnan(arr).any(axis=1)]

    if len(arr) == 0:
        print("No valid data to plot.")
    else:
        V = arr[:, 0]
        I = arr[:, 1]
        err = arr[:, 2]

        # ---- Linear plot ----
        plt.figure()
        plt.errorbar(V, I, yerr=err, fmt='o', capsize=3)
        plt.xlabel("Voltage (V)")
        plt.ylabel("Current (A)")
        plt.title("IV Curve (Linear)")
        plt.grid()

        # ---- Log plot ----
        plt.figure()
        plt.semilogy(np.abs(V), np.abs(I), 'o-')
        plt.xlabel("|Voltage| (V)")
        plt.ylabel("|Current| (A)")
        plt.title("IV Curve (Log Scale)")
        plt.grid(True, which="both")

        plt.show()

    # Plotting with ROOT
    # ROOT.gROOT.SetBatch(True)  # Run in batch mode to avoid GUI
    # c1 = ROOT.TCanvas("c1", "IV Measurement", 800, 600)

    # # Increase canvas margins to fit axis titles
    # c1.SetLeftMargin(0.15)  # Increase left margin
    # c1.SetBottomMargin(0.15)  # Increase bottom margin if needed

    # # Enable gridlines on both X and Y axes
    # c1.SetGridx()  # Enable gridlines along the X-axis
    # c1.SetGridy()  # Enable gridlines along the Y-axis

    # # Set logarithmic y-axis
    # c1.SetLogy()

    # # Creating TGraphErrors
    # graph = ROOT.TGraphErrors(len(current_values))
    # graph.SetTitle("IV Measurement;Voltage (V);Current (A)")

    # for i, (voltage, avg_current, uncertainty) in enumerate(current_values):
    #     graph.SetPoint(i, voltage, avg_current)
    #     graph.SetPointError(i, 0, uncertainty)

    # # Customize the graph
    # graph.SetMarkerStyle(21)
    # graph.SetMarkerColor(ROOT.kBlue)
    # graph.SetLineColor(ROOT.kBlue)

    # # Draw the graph
    # graph.Draw("AP")

    # # Save the graph as PDF
    # c1.SaveAs(f"{dataPath}/{outName}.pdf")

    # # Print to show the graph has been saved
    # print(f"Results saved in {dataPath}")
