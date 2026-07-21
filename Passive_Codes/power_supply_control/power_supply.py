#!/usr/bin/env python
# ignacio.asensi@cern.ch
import time
import datetime
import sys
from array import array
import argparse
import os
import signal
#import Keithley
# import ROOT
#from ROOT import TCanvas, TFile, TH1F, TH2F, gStyle, TGraph, TTree

#import MALTA_PSU

import numpy as np
import json
import pyvisa
# from SerialCom import SerialCom
from pyvisa import util
# import pymeasure
# from pymeasure.instruments.keithley import Keithley6517B
from datetime import datetime
import math 
########
##PSU###
########

class PSU():
	def __init__(self,address = "192.168.0.10"):
		self.rm=pyvisa.ResourceManager()
		self.address = address
		self.PSUNames = []
		self.addedPSUs = dict()
		self.PSUtypes = dict()
		self.measurementRange = dict()
		self.verbose = True
		return
   

	def _connect_TCP_to_SERIAL_device(self,address,port):
		com = self.rm.open_resource(f"TCPIP::{address}::{port}::SOCKET")
		com.write_termination = "\r\n"
		com.read_termination  = "\r\n"
		com.timeout = 5000
		if self.verbose:
			com.write('*IDN?')
			response = com.read()
			print(response)
		# com.write(":SENS:CURR:RANG:AUTO ON")
		return com,response
		
	
	def addPSU(self, name,port, deviceType):
		if name in self.PSUNames:
			raise Exception("PSU with name %s is already registered. Please select a different name." % name)
		
		if deviceType == "k_2410":
			com,response = self._connect_TCP_to_SERIAL_device(address=self.address,port=port)
			
			if not response :
				raise Exception("No response from device.")
			elif  "2410" not in response :
				raise Exception("Power supply not identified as {deviceType}")
			
		elif deviceType == "k_6517B":
			com,response = self._connect_TCP_to_SERIAL_device(address=self.address,port=port)
			
			if not response :
				raise Exception("No response from device.")
			elif  "6517" not in response :
				raise Exception("Power supply not identified as {deviceType}")           
		
		elif deviceType == "k_6487":
			# com = SerialCom(serialPath,baudrate=19200,timeout=3)
			com,response = self._connect_TCP_to_SERIAL_device(address=self.address,port=port)
			
			if not response :
				raise Exception("No response from device.")
			elif  "6487" not in response :
				raise Exception("Power supply not identified as {deviceType}")           	

		self.PSUNames.append(name)
		self.addedPSUs[name] = com
		self.PSUtypes[name] = deviceType
		self.measurementRange[name] = 20e-12

		return

	def setVoltage(self, psuSelected, voltage):
		if self.PSUtypes[psuSelected] == "k_2410":
			self.addedPSUs[psuSelected].write(":SOURce:VOLTage:LEVel %f" % voltage)
			self.addedPSUs[psuSelected].write(":OUTP ON")
			self.getVoltage(psuSelected)
		elif self.PSUtypes[psuSelected] == "k_6517B":
			self.addedPSUs[psuSelected].write(":SOURce:TTL1:LEVel ON")
			#voltageCorrected = self.overcomeVoltageBurden6517B(voltage)
			#print(voltageCorrected)
			self.addedPSUs[psuSelected].write(":SOUR:VOLT:LEVel:IMMediate:AMPLitude %f" % voltage) #(":SOUR:VOLT %f" % voltage)
			#time.sleep(0.5)
			self.addedPSUs[psuSelected].write(":OUTP1 ON")
			#time.sleep(0.5)
		elif self.PSUtypes[psuSelected] == "k_6487":
			self.addedPSUs[psuSelected].write(":SOURce:VOLTage %f \n;:SOURce:VOLTage:STATe ON \n" % voltage)

			#self.addedPSUs[psu].write(":SOURce:VOLTage:STATe ON")
		print("%s voltage set to %fV" % (psuSelected, voltage))
		return
		
	def disable(self,psu):
		if self.PSUtypes[psu] == "k_2410":
			self.addedPSUs[psu].write(":OUTP OFF")
			return
		elif self.PSUtypes[psu] == "k_6517B":
			time.sleep(0.5)
			self.addedPSUs[psu].write(":OUTP1 OFF")
		elif self.PSUtypes[psu] == "k_6487":
			self.addedPSUs[psu].write(":SOURce:VOLTage:STATe OFF \n")
			return

	def enable(self,psu):
		if self.PSUtypes[psu] == "k_2410":
			self.addedPSUs[psu].write(":OUTP ON")
			return
		elif self.PSUtypes[psu] == "k_6517B":
			time.sleep(0.5)
			self.addedPSUs[psu].write(":OUTP1 ON")
		elif self.PSUtypes[psu] == "k_6487":
			self.addedPSUs[psu].write(":SOURce:VOLTage:STATe ON \n")
			return

	def setMaxVoltage(self, psu, max_vol):
		if self.PSUtypes[psu] == "k_6517B":

			time.sleep(0.5)
			self.addedPSUs[psu].write(":SOUR:VOLT:RANG 1000")
			time.sleep(0.5)
			self.addedPSUs[psu].write(":SOUR:VOLT:LIM %f" % max_vol)
			time.sleep(0.5)
			#self.addedPSUs[psu].write(":SOUR:VOLT:RANG 1000")
			#time.sleep(0.5)
			self.addedPSUs[psu].write(":SOUR:VOLT:LIM:STAT ON")
			#self.addedPSUs[psu].write(":SOUR:VOLT:LIM:STAT ON")
			time.sleep(0.5)
		elif self.PSUtypes[psu] == "k_6487":
			time.sleep(2)
			self.addedPSUs[psu].write(":SOUR:VOLT:RANG 500 \n")
			time.sleep(2)

		#raise Exception("This function does not work yet")
		#self.addedPSUs[psu].write(":SOURce:VOLTage:POSitive:LIMit? [0|%f]" % max_vol)

	def setMaxCurrent(self, psu, max_curr):
		if self.PSUtypes[psu] == "k_2410":
			self.addedPSUs[psu].write(":SOURce:VOLTage:ILIMit %f" % max_curr) #1e-90.000000001(":SOURce:CURRage:PROTection:LEVel 1")
		elif self.PSUtypes[psu] == "k_6517B":
			self.addedPSUs[psu].write(":SOUR:CURR:RLIM:STAT OFF")
		elif self.PSUtypes[psu] == "k_6487":
			time.sleep(2)
			self.addedPSUs[psu].write(":SOURce:VOLTage:ILIMit 2.5e-3 \n")
			time.sleep(2)
		#raise Exception("This function does not work yet")
		#self.addedPSUs[psu].query("CURR:LIM %f" % max_curr)
		#i = max_curr

	def getVoltage(self, psu):
		if self.PSUtypes[psu] == "k_2410":
			# voltage = self.addedPSUs[psu].query(":MEASure:VOLTage:DC?")
			voltage = self.addedPSUs[psu].query(":READ?")
			if not "," in voltage: return -999.
			return float(voltage.split(",")[0])

		elif (self.PSUtypes[psu] == "k_6517B") or (self.PSUtypes[psu] == "k_6487"):
			voltage = self.addedPSUs[psu].query(":SOUR:VOLT:LEVel:IMMediate:AMPLitude?")
			return float(voltage)

    
	def getCurrent(self, psu):
		overCurrent = False
		messageRange = "N"
		
		print(psu)
		if self.PSUtypes[psu] == "k_2410":
			# current = self.addedPSUs[psu].query(":MEASure:CURRent:DC?")
			current = self.addedPSUs[psu].query(":READ?")
			if not "," in current: return -999.
			return float(current.split(",")[1])
			
		elif self.PSUtypes[psu] == "k_6517B":
			measurementSuccesfull = False
			while (measurementSuccesfull == False):
				currentTemp = self.addedPSUs[psu].query(":READ?")
				#currentTemp = self.addedPSUs[psu].query(":SENSe1:DATA:FRESh?")#":READ?"
				#current = self.addedPSUs[psu].writeAndRead(":SENSe1:FUNC?")#(":SENSe[1]]:FUNCtion 'VOLT'")
				currentReading = currentTemp.split(",", 1)
				#if ((currentTemp != "") and (len(currentTemp) >= 4)):
				print(currentTemp)
				if (((currentTemp != "") and (len(currentReading[0]) >= 11)) and (currentReading[0][-4:] == "NADC") and ((currentReading[0][0] == '+') or (currentReading[0][0] == '-'))):
					measurementSuccesfull = True
					time.sleep(0.2)#0.2
				else:
					print("No feedback")
					time.sleep(0.2)#0.2
					
			print("Current is:")
			print(currentTemp)
			currentValue = currentTemp.split(",", 1)

			print(currentValue[0][:-4])
			messageRange = currentValue[0][-4]
			
			current = float(currentValue[0][:-4])
			
		elif self.PSUtypes[psu] == "k_6487":
			measurementValid = False
			while (not measurementValid):
				currentTemp = self.addedPSUs[psu].writeAndRead(":READ? \n")#:MEASure:CURRENT:DC? :READ? :MEAS?

				currentValue = currentTemp.split(",", 1)
				print(currentValue)
				if (currentValue[0] == ''):
					print("tredoing Measruement")
				else:
					measurementValid = True
					print("seems valid")
					
				print(measurementValid)
			current = float(currentValue[0][:-1])
			
		if (abs(float(current)) >= 55e-6):
			overCurrent = True
		else:
			overCurrent = False	

		return current, overCurrent, messageRange
		
	def setAutoRange(self, psu):
		if self.PSUtypes[psu] == "k_6517B":
			print(f"Setting auto-range for {self.PSUtypes[psu]}")
			#time.sleep(6)
			self.addedPSUs[psu].write(":SENSe:CURRent:DC:RANGe 200e-12")
			print("Range set to 200pA")
			time.sleep(2)
			
			print("Setting lower Limit of Auto range")
			self.addedPSUs[psu].write(":SENSe1:CURRent:DC:RANGe:AUTO:LLIMit 2e-9")
			time.sleep(2)
			self.addedPSUs[psu].write(":SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 2e-3")
			time.sleep(2)
			self.addedPSUs[psu].write(":SENSe:CURRent:DC:RANGe:AUTO ON ")
			print("Autorange set\n")

		elif self.PSUtypes[psu] == "k_2410":
					# com.write()

			print(f"Setting auto-range for {self.PSUtypes[psu]}")
			#time.sleep(6)
			# self.addedPSUs[psu].write(":SENSe:CURRent:DC:RANGe 200e-12")
			# print("Range set to 200pA")
			# time.sleep(2)
			
			# print("Setting lower Limit of Auto range")
			# self.addedPSUs[psu].write(":SENSe1:CURRent:DC:RANGe:AUTO:LLIMit 2e-9")
			# time.sleep(2)
			# self.addedPSUs[psu].write(":SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 2e-3")
			# time.sleep(2)
			self.addedPSUs[psu].write(":SENS:CURR:RANG:AUTO ON ")
			print("Autorange set\n")
		else:
			print("Failed to enable auto-range. Not implemented")

    		
	def resetPsu(self, psu):
		if self.PSUtypes[psu] == "k_2410":
			self.addedPSUs[psu].write("*rst; status:preset; *cls")
		elif self.PSUtypes[psu] == "k_6517B":
			time.sleep(3)
			self.addedPSUs[psu].write(":SYST:PRES")

			time.sleep(30)
			self.addedPSUs[psu].write(":SYSTem:REMote")
			time.sleep(3)
			self.addedPSUs[psu].write(":SENSe1:FUNC 'CURR';:SENSe:CURRent:DC:RANGe 20e-12;:SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 1e-4;")#:SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 1e-4 12
			time.sleep(5)		
			self.addedPSUs[psu].write(":SENSe1:Current:DAMPing ON")
			#:SENSe:CURRent:DC:RANGe:AUTO ON :SENSe1:CURRent:DC:RANGe:AUTO:LLIMit 2e-9

			#self.addedPSUs[psu].write(":SYSTem:ZCOR ON")
			#self.addedPSUs[psu].writeAndRead(":SENSe1:FUNC 'CURR';:SENSe:CURRent:DC:RANGe:AUTO ON;:SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 1e-4")

			#calib
			time.sleep(2)#METER Connect option of CONFIG V-Sourc
			self.addedPSUs[psu].write(":SOURce:VOLTage:MCONnect ON")
			time.sleep(2)
			self.addedPSUs[psu].write(":SOURce:CURRent:RLIMit:STATe OFF")
			time.sleep(2)
			self.addedPSUs[psu].write(":SENSe1:VOLTage:DC:GUARd ON")
			time.sleep(2)
			self.addedPSUs[psu].write(":SYSTem:HLControl OFF")
			time.sleep(2)
			#self.addedPSUs[psu].write(":OUTP1 OFF")
			#psu.enableOutput(True)#
		elif self.PSUtypes[psu] == "k_6487":
			time.sleep(2)
			print(":SYST:PRES \n")
			self.addedPSUs[psu].write(":SYST:PRES\n")
			
			time.sleep(8)
			print(":SYSTem:REMote \n")
			self.addedPSUs[psu].write(":SYSTem:REMote \n")
			time.sleep(6)
			print(":SENSe1:FUNC 'CURR' \n;:SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 1e-4 \n")
			self.addedPSUs[psu].write(":SENSe1:FUNC 'CURR' \n;:SENSe1:CURRent:DC:RANGe:AUTO:ULIMit 1e-4 \n") #:SENSe:CURRent:DC:RANGe 2e-9 \n;
			time.sleep(6)
			print(":CONFigure:CURRent:DC \n")
			self.addedPSUs[psu].write(":CONFigure:CURRent:DC \n")
			time.sleep(6)
			print(":ARM:COUNt 1 \n")
			self.addedPSUs[psu].write(":ARM:COUNt 1 \n")
			time.sleep(6)#METER Connect option of CONFIG V-Sourc
			print("reset done")

		return
	def ZCHon(self, psu):
		if (self.PSUtypes[psu] == "k_6487"):
			time.sleep(2)
			self.addedPSUs[psu].write(":SYSTem:ZCHeck ON \n")
		elif self.PSUtypes[psu] == "k_6517B":
			time.sleep(2)
			self.addedPSUs[psu].write(":SYSTem:ZCHeck ON")
			
	def rampDownVoltage(self, psuSelected, startVoltage, endVoltage=0, step=1.0, delay=6.0):
		"""
		Ramps down the voltage of the selected PSU in steps.

		:param psuSelected: Name of the PSU to ramp down.
		:param startVoltage: Starting voltage for ramp down.
		:param endVoltage: Target voltage to reach (default is 0).
		:param step: Voltage decrement step (default is 1V).
		:param delay: Delay between each step in seconds (default is 0.5 seconds).
		"""
		if psuSelected not in self.PSUtypes:
			raise KeyError(f"PSU '{psuSelected}' not found.")

		step = abs(step)  # guard against an infinite loop if a negative step is ever passed
		currentVoltage = startVoltage

		# Ramp down in steps
		while currentVoltage > endVoltage:
			self.setVoltage(psuSelected, currentVoltage)
			print(f"Ramping down {psuSelected}: Voltage set to {currentVoltage}V")
			time.sleep(delay)
			currentVoltage -= step

		# Ensure final voltage is set to the end voltage
		self.setVoltage(psuSelected, endVoltage)
		print(f"Final voltage set to {endVoltage}V for {psuSelected}")
		return
	
	def rampUpVoltage(self, psuSelected, startVoltage, endVoltage,wait=1, step=1.0, delay=5):
		"""
		Ramps up the voltage of the selected PSU in steps.

		:param psuSelected: Name of the PSU to ramp up.
		:param startVoltage: Starting voltage for ramp up.
		:param endVoltage: Target voltage to reach.
		:param step: Voltage increment step (default is 1V).
		:param delay: Delay between each step in seconds (default is 0.5 seconds).
		"""
		if psuSelected not in self.PSUtypes:
			raise KeyError(f"PSU '{psuSelected}' not found.")

		step = abs(step)  # guard against an infinite loop if a negative step is ever passed
		currentVoltage = startVoltage

		# Ramp up in steps
		while currentVoltage < endVoltage:
			self.setVoltage(psuSelected, currentVoltage)
			if currentVoltage == startVoltage:
				time.sleep(delay)#900
			print(f"Ramping up {psuSelected}: Voltage set to {currentVoltage}V")
			time.sleep(delay)
			currentVoltage += step

		# Ensure final voltage is set to the end voltage
		self.setVoltage(psuSelected, endVoltage)
		print(f"Final voltage set to {endVoltage}V for {psuSelected}")
		return

	# -------------------------------------------------------------------------
	# Dead code below - not called from any script in this project. Kept
	# commented out for reference only, each one is broken/incomplete as-is:
	# -------------------------------------------------------------------------

	# def overcomeVoltageBurden6517B(self,voltage):
	# 	if (self.measurementRange["NW"] <= 200e-12):
	# 		d = 0.0#47
	# 		k = 0.0#10878045
	# 	elif ((self.measurementRange["NW"] > 200e-12) and (self.measurementRange["NW"] <= 200e-9)):
	# 		d = 0.0#47
	# 		k = 0.0#25#10950523
	# 	elif (self.measurementRange["NW"] > 200e-9):# and (self.measurementRange["NW"] <= 2e-6)
	# 		d = 0
	# 		k = 0
	# 	else:
	# 		d = 0
	# 		k = 0
	# 	# never returns anything, d/k always 0 - incomplete burden-voltage correction

	# def getcurrent(self,psu):
	# 	overCurrent = False
	# 	messageRange = "N"
	# 	print(psu)
	#
	# 	if self.PSUtypes[psu] == "k_2410":
	# 		currentTemp = self.addedPSUs[psu].query(":READ?")
	# 		if not "," in current: return -999.  # BUG: references undefined 'current', should be 'currentTemp'
	# 		return float(current.split(",")[1])
	#
	# 	elif self.PSUtypes[psu] == "k_6517B":
	# 		currentTemp = self.addedPSUs[psu].query(":READ?")
	# 		currentReading = currentTemp.split(",", 1)
	# 		print(currentTemp)
	# 		if (((currentTemp != "") and (len(currentReading[0]) >= 11)) and (currentReading[0][-4:] == "NADC") and ((currentReading[0][0] == '+') or (currentReading[0][0] == '-'))):
	# 				measurementSuccesfull = True
	# 				time.sleep(0.2)
	# 		else:
	# 				print("No feedback")
	# 				time.sleep(0.2)
	# 		print("Current is:")
	# 		print(currentTemp)
	# 		currentValue = currentTemp.split(",", 1)
	# 		print(currentValue[0][:-4])
	# 		messageRange = currentValue[0][-4]
	# 		current = float(currentValue[0][:-4])
	#
	# 	elif self.PSUtypes[psu] == "k_6487":
	# 		measurementValid = False
	# 		while (not measurementValid):
	# 			currentTemp = self.addedPSUs[psu].writeAndRead(":READ? \n")  # writeAndRead does not exist on pyvisa resources
	# 			currentValue = currentTemp.split(",", 1)
	# 			print(currentValue)
	# 			if (currentValue[0] == ''):
	# 				print("tredoing Measruement")
	# 			else:
	# 				measurementValid = True
	# 				print("seems valid")
	# 			print(measurementValid)
	# 		current = float(currentValue[0][:-1])
	#
	# 	if (abs(float(current)) >= 55e-6):
	# 		overCurrent = True
	# 	else:
	# 		overCurrent = False
	# 	return current, overCurrent, messageRange
	# 	# superseded by getCurrent() (uppercase C) - this lowercase duplicate is unused and broken

	# def changeMeasureRange(self, psu, messageRange):
	# 	if self.PSUtypes[psu] == "k_6517B":
	# 		print("measurementRange= %", self.measurementRange["NW"])
	# 		if ((messageRange == "O") or (messageRange == "L")):
	# 			newRange = self.measurementRange["NW"] * 10
	# 		elif ((messageRange == "U") or (messageRange == "Z")):
	# 			newRange = self.measurementRange["NW"] / 10
	# 		else:
	# 			print("Error Reading", messageRange)
	# 			newRange = self.measurementRange["NW"]
	# 		if (newRange < 20e-12):
	# 			newRange = 20e-12
	# 		print("new Range= ", newRange)
	# 		self.measurementRange["NW"] = newRange
	# 		self.measurementRange["NW_C"] = newRange
	# 		self.addedPSUs["NW"].write(":SENSe:CURRent:DC:RANGe " + str(newRange))
	# 		self.addedPSUs["NW_C"].write(":SENSe:CURRent:DC:RANGe " + str(newRange))
	# 		# BUG: "NW_C" is never registered via addPSU in this project - would KeyError

	# def getCurrentBuffer(self, psu, nMeasurements):
	# 	self.addedPSUs[psu].write(":SENS:FUNC CURR")
	# 	self.addedPSUs[psu].write(":SENS:CURR:RANG: AUTO ON")
	# 	self.addedPSUs[psu].write(":TRIG:LOAD SimpleLoop, %i, 0.1", nMeasurements)  # BUG: not how pyvisa write() formatting works
	# 	self.addedPSUs[psu].write("INIT")
	# 	self.addedPSUs[psu].write("*WAI")
	# 	query = self.addedPSUs[psu].query(":TRAC:DATA? 1, 10, defbuffer1, READ, REL")
	# 	print(query)
	# 	return float(query)

	# def checkRLim(self, psu):
	# 	if self.PSUtypes[psu] == "k_6517B":
	# 		time.sleep(2)
	# 		RLIMis = self.addedPSUs[psu].writeAndRead(":SOURce:CURRent:RLIMit:STATe?")  # writeAndRead does not exist on pyvisa resources
	# 	return RLIMis
