import argparse
import time
from power_supply import PSU  # Assuming your PSU class is in a separate file named psu.py

def main():
    parser = argparse.ArgumentParser(description='Set power supply voltage.')
    parser.add_argument('--voltage', type=float, help='Target voltage to set')
    parser.add_argument('--delay', type=int, default= 1, help='Seconds betwen steps')
    parser.add_argument('--port', type=str, default='101', help='Serial port of power supply')
    args = parser.parse_args()

    psu = PSU()
    PSName = "k_2410" 
    target = "NW" #FIX this needs to be removed 
    psu.addPSU(target, f'{args.port}', str(PSName))
    
    #psu.setMaxVoltage(target, 120)

    # Get the initial voltage
    psu.enable(target)
    initial_voltage = psu.getVoltage(target)

    if initial_voltage < args.voltage:
        psu.rampUpVoltage(psuSelected=target, startVoltage=initial_voltage,delay=args.delay, endVoltage=args.voltage, step=1)
    elif initial_voltage > args.voltage:
        psu.rampDownVoltage(psuSelected=target, startVoltage=initial_voltage,delay=args.delay, endVoltage=args.voltage, step=1)
    else:
        print(f"Voltage is already at {args.voltage}V. No change needed.")

if __name__ == '__main__':
    main()

