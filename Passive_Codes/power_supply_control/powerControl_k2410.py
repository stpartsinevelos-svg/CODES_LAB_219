import argparse
import time
from power_supply import PSU  # Assuming your PSU class is in a separate file named psu.py

def main():
    parser = argparse.ArgumentParser(description='Turn power supply on or off.')
    parser.add_argument('--state', choices=['on', 'off'],default='off', help='Power state: on or off')
    parser.add_argument('--port', type=str, default='103', help='Serial port of power supply')
    args = parser.parse_args()

    psu = PSU()
    PSName = "k_2410" 
    target = "NW" #FIX this needs to be removed 
    psu.addPSU(target, f'{args.port}', str(PSName))
    
    if args.state == 'on':
        psu.enable(target)
    else:
        psu.disable(target)
    
    #ps.close()

if __name__ == '__main__':
    main()
