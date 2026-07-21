import pathlib
import os
import time
from datetime import datetime, timedelta 
import numpy as np
import libximc.highlevel as ximc
import sys
import json

"""
This code controls the motors of the TCT.
"""


class Stage:
    
    axes = ["x","y","z"]
    orientation = {"Axis 3":"z","Axis 1":"x","Axis 2":"y"}
    devices={}
    step_coeff = 1
    saved_positions = {"zero":[0,0,0]}

    @staticmethod
    def identify_devices():
        """
        Identifies and connects to the motors controlling the axes.
        The function scans for available XIMC devices on the system,
        creates Axis objects for each detected device, and stores them
        in `Stage.devices` according to their orientation.

        Args:
            None

        Returns:
            Stage.devices (): A dictionary containing the connected axis devices.
        """

        # Stage.devices search
        dev_objs = ximc.enumerate_devices(
            ximc.EnumerateFlags.ENUMERATE_NETWORK |
            ximc.EnumerateFlags.ENUMERATE_PROBE
        )

        for dev in dev_objs:
            print("device found: ",dev['uri'],dev['ControllerName'])
            Stage.devices[Stage.orientation[dev['ControllerName']]]= ximc.Axis(dev["uri"])
        return Stage.devices


    @staticmethod
    def get_axis_position(axis):
        """
        Prints the position of an axis.

        Args:
            ax (str): The axis whom position will be printed

        Returns:
            None
        """

        int_position = Stage.devices[axis].get_position_calb()

        print(axis, " position: ", int_position.Position)


    @staticmethod
    def print_position():
        """
        Prints the position of all the axes.

        Args:
            None

        Returns:
            None
        """

        for ax in Stage.axes:
            Stage.get_axis_position(ax)


    @staticmethod
    def print_finish(duration):
        """
        Prints the estimated duration and finish time of the scanning

        Args:
            duration (int): The duration of the scanning

        Returns:
            None
        """

        finish = datetime.now() + timedelta(milliseconds = duration)
        print("Duration: ", duration/1000, " s")
        print("Current time: ", datetime.now())
        print("Estimated finish: ", finish)


    @staticmethod
    def print_stats(x=True,y=True,z=True,speed=True,acceleration=True,deceleration=True,uspeed=False,antiplayspeed=False,uantiplayspeed=False,moveflags=False):
        """
        Prints motion parameters of the selected motor axes.
        Each axis (x, y, z) can be enabled or disabled, and specific motion
        parameters can be selected for display.

        Args:
            x (bool): Print parameters for the X axis.
            y (bool): Print parameters for the Y axis.
            z (bool): Print parameters for the Z axis.
            speed (bool): Display the motor speed.
            acceleration (bool): Display the acceleration value.
            deceleration (bool): Display the deceleration value.
            uspeed (bool): Display the microstep speed.
            antiplayspeed (bool): Display the anti-play speed.
            uantiplayspeed (bool): Display the microstep anti-play speed.
            moveflags (bool): Display the move flags configuration.

        Returns:
            None
        """

        k = [x,y,z]
        i = 0
        for ax in Stage.axes:
            if (k[i]):
                move_settings = Stage.devices[ax].get_move_settings()

                print(ax, " axis:")
                if (speed):
                    print("Speed: ", move_settings.Speed)
                if (acceleration):
                    print("Acceleration: ", move_settings.Accel)
                if (deceleration):
                    print("Deceleration: ", move_settings.Decel)
                if (uspeed):
                    print("uSpeed: ", move_settings.uSpeed)
                if (antiplayspeed):
                    print("AntiplaySpeed: ", move_settings.AntiplaySpeed)
                if (uantiplayspeed):
                    print("uAntiplaySpeed: ", move_settings.uAntiplaySpeed)
                if (moveflags):
                    print("MoveFlags: ", move_settings.MoveFlags)

                i = i + 1


    @staticmethod
    def change_stats(axis, quantity, new_value): 
        """
        Change a motion parameter of the selected motor axis.
    
        The function retrieves the current motion settings of the specified
        axis, modifies the selected parameter, and applies the updated settings.
    
        Available parameters:
            Speed – main movement speed (steps/sec)
            uSpeed – microstep fraction of speed
            Accel – acceleration
            Decel – deceleration
            AntiplaySpeed – speed used for backlash (anti-play) correction
            uAntiplaySpeed – microstep fraction for anti-play speed
            MoveFlags – bit flags controlling movement options
    
        Args:
            axis (str): The axis whose parameter will be modified (e.g., 'x', 'y', 'z').
            quantity (str): The name of the parameter to change.
            new_value (int | float): The new value for the selected parameter.
    
        Returns:
            None
        """

        move_settings = Stage.devices[axis].get_move_settings()
        setattr(move_settings, quantity, new_value) #setattr(object, attribute_name, value) := object.attribute_name = value
        Stage.devices[axis].set_move_settings(move_settings)

        Stage.print_stats()

    
    @staticmethod
    def move_axis(axis,new_position,timestop=100):
        """
        Moves an axis to a new potition and waits for a specified time.

        Args:
            axis (str): The axis which will be moved.
            new_position (int): The new position of the axis.
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None                
        """

        Stage.devices[axis].command_move_calb(int(new_position))
        Stage.devices[axis].command_wait_for_stop(timestop)


    @staticmethod
    def move_axis_r(axis,relative_shift,timestop=100):
        """mmm
        Moves an axis to a new potition relative to the current position and waits for a specified time.

        Args:
            axis (str): The axis which will be moved.
            relative_shift (int): The new position of the axis.
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None                
        """

        Stage.devices[axis].command_movr_calb(int(relative_shift))
        Stage.devices[axis].command_wait_for_stop(timestop)

        Stage.get_axis_position(axis)


    @staticmethod
    def move(new_positions,timestop=100):
        """
        Moves all the axes to a new potition and waits for a specified time.

        Args:
            new_positions (list of int): An array with the new positions of the axes.
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None                
        """

        for i in range(3):
            Stage.move_axis(Stage.axes[i],new_positions[i],timestop)


    @staticmethod
    def move_to_center(timestop=100):
        """
        Moves all the axes to the center and waits for a specified time.

        Args:
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None                
        """
        
        Stage.move([0,0,0],timestop)
        print("Done")


    @staticmethod
    def scan_1D(axis,x0,x1,N,timestop=100):
        """
        It does an 1-dimensional scan.

        Args:
            axis (str): The axis which will be moved.
            x0 (int): Starting point of the scanning.
            x1 (int): Finishing point of the scanning.
            N (int): Number of points.
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None
        """

        duration = timestop*N
        positions = np.linspace(x0, x1, num=N)
        Stage.print_finish(duration)
        
        for j in positions:
            Stage.move_axis(axis,j,timestop)

        print("Done")


    @staticmethod
    def scan_2D(axis1,axis2,x0,y0,x1,y1,Nx,Ny,timestop=100):
        """
        It does a 2-dimensional scan.

        Args:
            axis1 (str): The first axis which will be moved.
            axis2 (str): The second axis which will be moved.
            x0 (int): Starting point of the first axis.
            y0 (int): Starting point of the second axis.
            x1 (int): Finishing point of the first axis.
            y1 (int): Finishing point of the second axis.
            Nx (int): Number of points of the first axis.
            Ny (int): Number of points of the second axis.
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None
        """

        duration = timestop*Nx*Ny
        array1 = np.linspace(x0, x1, num=Nx)
        array2 = np.linspace(y0, y1, num=Ny)
        pos1, pos2 = np.meshgrid(array1,array2)
        Stage.print_finish(duration)

        for j in pos1[0]:
            Stage.move_axis(axis1,j,timestop)
            for i in pos2:
                Stage.move_axis(axis2,i,timestop)

        print("Done")


    @staticmethod
    def calibration(coeff=1.248):
        """
        Sets the conversion coefficient between motor steps and user units.
        The same coefficient is applied to all axes in `Stage.axes`.
        For um the coefficient is 1.248.

        Args:
            coeff (float): Conversion coefficient (user units per step).

        Returns:
            None
        """
        
        step_coeff = coeff
        for ax in Stage.axes:
            engine_settings = Stage.devices[ax].get_engine_settings()
            Stage.devices[ax].set_calb(step_coeff, engine_settings.MicrostepMode)


    @staticmethod
    def get_axis_status(parameter = None, axis = None, printing = False):
        """
        Returns the status of all the axes or a specified one. (I haven't tested it yet)

        Available parameters:
            MoveSts: 
            MvCmdSts: 
            PWRSts: 
            EncSts: 
            WindSts: 
            CurPosition: 
            uCurPosition: 
            EncPosition: 
            CurSpeed: 
            uCurSpeed: 
            Ipwr: 
            Upwr: 
            Iusb: 
            Uusb: 
            CurT: 
            Flags: 
            GPIOFlags: 
            CmdBufFreeSpace: 

        Args:
            parameter (str): The parameter that will be returned. If none all the parameters will be returned.
            axis (str): The axis whose status will be returned. If none the status of all the axes will be returned.
            printing (bool): Print the status of the selected axes.
            

        Returns:
            value (bool): The current status of the axis.
        """

        if axis is not None:
            if parameter is not None:
                status = Stage.devices[axis].get_status()
                value = getattr(status, parameter)

            else:
                value = Stage.devices[axis].get_status()
            if (printing):
                print(value)
            return value
        else:
            value = []
            i = 0
            if parameter is not None:
                for ax in Stage.axes:
                    status = Stage.devices[ax].get_status()
                    status_all = getattr(status, parameter)
                    value.append(status_all)
                    if (printing):
                        print(f"{ax} axis :")
                        print(value[i])
                    i = i + 1
            else:
                for ax in Stage.axes:
                    value.append(Stage.devices[ax].get_status())
                    if (printing):
                        print(f"{ax} axis :")
                        print(value[i])
                    i = i + 1
            return value

    
    @staticmethod
    def save_position(name,position=[]):
        """
        It saves a position in a dictionary

        Args:
            position (list of int): The position you want to save. If it's not specified, it saves the current position.
            name (str): The key for the position

        Returns:
            None
        """
        if len(position) == 0:
            for axis in St.axes:
                pos = Stage.devices[axis].get_position_calb()
                position.append(pos.Position)
        elif 0 < len(position) < 3:
            print("invalid position")
        Stage.saved_positions[name] = position


    @staticmethod
    def delete_saved_position(name):
        """
        Deletes a saved position from the dictionary

        Args:
            name (str): The key for the position

        Returns:
            None
        """
        Stage.saved_positions.pop(name)


    @staticmethod
    def print_saved_positions():
        """
        It prints the dictionary with the saved positions

        Args:
            None

        Returns:
            None
        """
        for i in Stage.saved_positions:
            print(i, " : ", Stage.saved_positions[i])

    
    @staticmethod
    def go_to_saved_position(name,timestop=100):
        """
        It goes to one of the saved positions

        Args:
            name (str): The key for the position
            timestop (int): Time to wait after the movement, in milliseconds.

        Returns:
            None
        """
        Stage.move(Stage.saved_positions[name],timestop)


    @staticmethod
    def non_stop():
        """
        This command allows you to run some basic functions without opening and closing the devices all the time.

        Args:
            None
        
        Returns:
            None
        """

        while True:
            command = input("\nSelect one of the following commands:\n" \
                            "get_axis_position\n" \
                            "print_position\n" \
                            "move_axis\n" \
                            "move_axis_r\n" \
                            "move\n" \
                            "move_to_center\n" \
                            "save_position\n" \
                            "print_saved_positions\n" \
                            "delete_saved_position\n"\
                            "go_to_saved_position\n"\
                            "or exit\n"\
                            "\n")

            if command == "get_axis_position":
                axis = input("Select an axis\n")
                print("\n")
                St.get_axis_position(axis)
            elif command == "print_position":
                St.print_position()
            elif command == "move_axis":
                axis, new_position = input("Select axis and new position\n").split()
                print("\n")
                St.move_axis(axis,new_position)
            elif command == "move_axis_r":
                axis, new_position = input("Select axis and new position\n").split()
                print("\n")
                St.move_axis_r(axis,new_position)
            elif command == "move":
                new_position = input("Select the array of position\n")
                print("\n")
                St.move(new_position)
            elif command == "move_to_center":
                St.move_to_center()
            elif command == "save_position":
                save_current = input("Do you want to save the current position\n")
                if save_current=="Yes":
                    name = input("Give a name for the position\n")
                    position = []
                elif save_current=="No":
                    name, position = input("Give a name for the position and the position\n").split()
                if St.save_position(name):
                    sure = input("It seems there is another saved position with that name. Are you sure you want to overwright it?")
                    if sure == "Yes":
                        St.save_position(name,position)
                    elif sure == "No":
                        name = input("Give a new name for the position\n")
                        St.save_position(name,position)
                else:
                    St.save_position(name,position)
                print("\n")
            elif command == "print_saved_positions":
                St.print_saved_positions()
            elif command == "delete_saved_position":
                name = input("Select the name of the position you want to delete\n")
                sure = input(f"Are you sure you want to delete the position {name}?\n")
                if sure == "Yes":
                    St.delete_saved_position(name)
                print("\n")
            elif command == "go_to_saved_position":
                name = input("Select the name of the position you want to go\n")
                print("\n")
                St.go_to_saved_position(name)
            elif command == "exit":
                print("\n")
                break
        

if __name__=="__main__":
    St = Stage
    St.identify_devices() 
    
    for ax in St.axes:
        St.devices[ax].open_device()
    St.calibration(1.248)
    #It is important to set the coefficient in order to set the unit you want.
    #If you don't do that the movements and the results that will be printed will be with coefficient 1.
    #The default in my code is 1.248
    #The move commands can take floats for the positions, but I suggest we only use integers.

    path = r"C:\Users\ehep\tctsw\tctfw\Stage_control\saved_positions.json"

    with open(path, "r") as sp:
        St.saved_positions = json.load(sp)

    
    St.non_stop()
    #St.move([0,0,0])
    #St.print_position()
    #St.save_position("test")
    #St.print_saved_positions()
    #St.go_to_saved_position("zero")
    #St.print_position()
    #St.print_position()
    #St.move_axis("x",2000, 1000)
    #St.move_axis_r("y", 100, 100)
    #St.move_axis_r("x", 100, 100)
    # St.scan_1D('x' , 1000 , 2000 , 3 , 5000)


    with open(path, "w") as sp:
        json.dump(St.saved_positions, sp, indent=4)

    for ax in St.axes:
            St.devices[ax].close_device()
    
    
    #In every process you must open the axes and you finish you must close them.
    #If you try to open the same axis two times without closing it first, there will be an error.