#!/bin/bash

# AAIMI GPIO
# Configure and use Raspberry Pi GPIO pins and Arduino pins from a web interface 


###############

# Copyright (C) 2017  Anthony Hartup

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

###############

import json
import socket
import os
import threading
import time
import RPi.GPIO as GPIO

# Socket to listen for input from browser-based GUI
socketport = 50001

# Program can save and load multiple pin configurations. session is default
current_pin_map = "session"

# Pin configuration details for Pi and Arduino
pins = {}
# JSON to hold pin maps
pinlist = "pin_details.txt"

# Commands to send to Arduino to read inputs and switch outputs
# Switch-on is first entry, switch-off is second
pin_commands = {"D2": ["q", "r"], "D3": ["s", "t"], "D4": ["u", "v"], "D5": ["w", "x"], "D6": ["y", "z"], "D7": ["i", "j"], "D8": ["k", "l"], "D9": ["m", "n"],\
                "D10": ["o", "p"], "D11": ["K", "L"], "D12": ["M", "N"], "D13": ["O", "P"], "A0": ["a", "A"], "A1": ["b", "B"], "A2": ["c", "C"], "A3": ["d", "D"], "A4": ["e", "E"], "A5": ["f", "F"]}

# Flag to write changes to file at end of loop
# This saves rapid file-writes when using PWM speed adjustment slider in GUI
write_due = "no"

# Status of loop.
# If "no", program does not monitor pins, just waits for socket commands
# When start signal from GUI received, this will change to "yes" and program will moitor pins
running = "no"

# Pins set as PWM dual-directional motor outputs
#  The two wires for each motor, and the default, and current speed
pwm_pairs = {}
ard_pwm_pairs = {}
# Count to determine which reserved variable AAIMI will use to define GPIO PWM objects for DC motor pins
pwm_count = 0

# General single-pin PWM devices like leds that connect back to GND
pwm_general_pins = {}
# Count to determine which reserved variable AAIMI will use to define single GPIO PWM object
led_count = 0

# Input and output pins and their timout and timer settings
# If both of these are empty the main loop will not monitor any pins
# Input pins
event_times = {}
# Output pins with timer/timeout set
event_times_out = {}
# A list of switching times for timer outputs
active_hours = []

# Time variables, second_clock[0] is loop count, syncs to real-word settings every minute
# These are used to monitor timer scedules and timeouts
second_clock = [0, 60]
minute_store = "00"
hour_store = "00"


##################################################
# Start serial connection with Arduino

### Uncomment the following section to use an Arduino connected to the Pi via USB

##import serial
##arduino = serial.Serial('/dev/ttyUSB0', 9600)
##
##def check(sensor):  # Check Arduino analog pin
##    arduino.write(sensor)
##    while True:
##        try:
##            time.sleep(0.01)
##            light = str(arduino.readline()).replace("\n", "")
##            return float(light)
##        except:
##            pass
##
##def check_digital_sensor(sensor):   # Check Arduino digital pin
##    arduino.write(sensor)
##    while True:
##        try:
##            time.sleep(0.01)        
##            rawsense = arduino.readline()
##            return int(rawsense)
##        except:
##            pass   
##
##def switch(r):  # Switch Arduino output pin
##    arduino.write(r)

#######################################################


# Write new or updated pin details to file for JS to display in browser
def write_pin_list():
    container = []
    container.append(pins)
    with open(pinlist, 'w') as pindata:
        json.dump(container, pindata)

        
# Create a new JSON pin file for factory reset
# If scope is "new", will create list from scratch and remove all saved pin maps.
# Otherwise it will just rewrite the mapname map
def create_new_pinfile(scope="new", mapname="session"):
    global pins, current_pin_map
    if scope == "new":
        # Delete existing pin file
        pins = {}
        pins["current_map"] = "session"
        pins["maps"] = {}
        pins["maps"]["session"] = {}
    # Create entries for all Raspi pins
    pincount = 2
    while pincount <= 27:
        keystring = "gpio_" + str(pincount)
        pins["maps"][mapname][keystring] = {}
        pins["maps"][mapname][keystring]["status"] = "NA"
        pins["maps"][mapname][keystring]["setting"] = "Unset"
        pins["maps"][mapname][keystring]["default"] = "Pending"
        pins["maps"][mapname][keystring]["nickname"] = "nickname"         
        pins["maps"][mapname][keystring]["action"] = {}
        pins["maps"][mapname][keystring]["action"]["type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["arg1"] = 0 #Partner pin, second motor wire, LED PWM speed
        pins["maps"][mapname][keystring]["action"]["arg2"] = 0  # Default PWM speed
        pins["maps"][mapname][keystring]["action"]["arg3"] = 0   # motor direction
        pins["maps"][mapname][keystring]["action"]["arg4"] = 0 # current PWM speed       
        pins["maps"][mapname][keystring]["action"]["timer"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["timeout"] = 0
        pins["maps"][mapname][keystring]["action"]["timeout_type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["times"] = ["00:00", "00:00"]      
        pincount += 1

    # Create entries for all Arduino digital and analog pins
    pincount = 0
    while pincount <= 19:
        if pincount <= 13:
            # create digital pins first
            keystring = "D" + str(pincount)
        else:
            # Create analog pins
            keystring = "A" + str(pincount - 14)
        print(keystring)
        pins["maps"][mapname][keystring] = {}
        pins["maps"][mapname][keystring]["status"] = "NA"
        pins["maps"][mapname][keystring]["setting"] = "Unset"  # Input, output, analog
        pins["maps"][mapname][keystring]["default"] = "Pending" # Default state for pin
        pins["maps"][mapname][keystring]["nickname"] = "nickname" # Name for pin
        pins["maps"][mapname][keystring]["action"] = {}
        pins["maps"][mapname][keystring]["action"]["type"] = "Pending" # switchout, count, manual, etc
        pins["maps"][mapname][keystring]["action"]["arg1"] = 0  # Partner pin, second motor wire
        pins["maps"][mapname][keystring]["action"]["arg2"] = 0  # Analog reading
        pins["maps"][mapname][keystring]["action"]["arg3"] = 0   # Analog trigger-point
        pins["maps"][mapname][keystring]["action"]["arg4"] = [0, 10] # Frequency to read sensors
        pins["maps"][mapname][keystring]["action"]["timer"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["timeout"] = 0
        pins["maps"][mapname][keystring]["action"]["timeout_type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["times"] = ["00:00", "00:00"]       
        pincount += 1
    current_pin_map = mapname
    write_pin_list()
## Uncomment the following line and run once to create a new pin file if your file becomes unusable
# create_new_pinfile()

#create_new_pinfile()

# Get IO pin name from its numeric identifier
def num_to_name(num):
    if num <= 27:
        pname = "gpio_" + str(num)
    elif num >= 100 and num <= 113:
        pname = "D" + str(int(num) - 100)
    elif num >= 114:
        pname = "A" + str(int(num) - 114)
    return pname
    
# Load the list of GPIO configurations from file and define the inputs and outputs from the chosen pin map
# This is triggered from after start_loop command from GUI, and also after command to change maps
def load_pin_list():
    global pins, current_pin_map, pwm_pairs, event_times, pwm_count, pwm_general_pins, led_count
    global pwm1, pwm2, pwm3, pwm4, led1, led2   # Reserved variables for PWM motor and LED GPIO objects
    # Read JSON pin file and determine the current map
    with open(pinlist) as source_file:
        all_pin_maps = json.load(source_file)
        pins = all_pin_maps[0]
        current_pin_map = pins["current_map"]
    # Load variables and details for all active pins and configure GPIO settings
    #pins["maps"][current_pin_map]["D3"]["partner"] = 22
    for p in pins["maps"][current_pin_map]:
        # Only get details from pins that have been defined
        print(p)
        if pins["maps"][current_pin_map][p]["setting"] != "Unset":
            # Create numeric identifier for pin for int operations
            if "gpio_" in p:
                # Raspi, use GPIO number. This is used for GPIO operations
                target_pin = int(p.replace("gpio_", ""))
            elif "D" in p:
                # Add 100 to target_pin to signify Arduino digital pin
                target_pin = int(p.replace("D", "")) + 100
            elif "A" in p:
                # Add 114 to differentiate Arduino analog pin
                target_pin = int(p.replace("A", "")) + 114
            msg = p + " has been set to " + pins["maps"][current_pin_map][p]["setting"]
            
            # If pin is any type of output (Output, PWMOutput or PWMOutputLED)
            if "Output" in pins["maps"][current_pin_map][p]["setting"]:
                # Define pin as output and switch High or Low depending on its default setting
                if "gpio_" in p:
                    # Raspberry Pi pin
                    GPIO.setup(target_pin, GPIO.OUT)
                    # Set pin to its default state
                    if pins["maps"][current_pin_map][p]["default"] == "Low" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                        GPIO.output(target_pin, False)
                        pins["maps"][current_pin_map][p]["status"] = "Low"
                    elif pins["maps"][current_pin_map][p]["default"] == "High" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                        GPIO.output(target_pin, True)
                        pins["maps"][current_pin_map][p]["status"] = "High"
                else:
                    # Arduino pin, set to its default state
                    if pins["maps"][current_pin_map][p]["default"] == "Low" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                        print("Switching Low")
                        switch(pin_commands[p][1])
                        print("DONE")
                    elif pins["maps"][current_pin_map][p]["default"] == "High" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                        switch(pin_commands[p][0])
                print("Switched")
                        
                if pins["maps"][current_pin_map][p]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][p]["action"]["timer"] == "setTimes":
                    # Add to events folder for loop to monitor if timer or timeout set  [lastevent, timeoutseconds, timer/timeout]
                    event_times_out[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]
                print("Output finished")
                
                # If pin is a bi-directional motor
                if pins["maps"][current_pin_map][p]["setting"] == "PWMOutput":
                    if "gpio" in p:
                        pwm_count += 1
                    this_motor = pins["maps"][current_pin_map][p]["nickname"]
                    pwm_pairs[this_motor] = {}
                    # The two gpio pin numbers for the motor, ie ['gpio_22', 'gpio_27'] become [22, 27]
                    pwm_pairs[this_motor]["pin_pair"] = [target_pin, int(pins["maps"][current_pin_map][p]["action"]["arg1"])]
                    if "gpio_" in p:
                        # Set second motor pin as output
                        GPIO.setup(int(pwm_pairs[this_motor]["pin_pair"][1]), GPIO.OUT)
                        print("GPIO " + str(pwm_pairs[this_motor]["pin_pair"][1]) + "has been set")
                        # The identifier (int) for the motor pin objects, 1 is pwm1 and pwm2, 3 is pwm3 and pwm4
                        pwm_pairs[this_motor]["id"] = pwm_count
                    else:
                        print(p + " has been set")
                        # The identifier (int) for both pins to use for GPIO commands, ie [22, 27]
                        if "D" in p or "A" in p:
                            pwm_pairs[this_motor]["id"] = target_pin                         
                    # Default state for motor when program starts: on or off
                    pwm_pairs[this_motor]["default"] = pins["maps"][current_pin_map][p]["default"]
                    # Current speed and default starting speed
                    pwm_pairs[this_motor]["pwm"] = [0, int(pins["maps"][current_pin_map][p]["action"]["arg2"])]  # ???     
                    pins["maps"][current_pin_map][p]["action"]["arg4"] = 0 # Current speed
                    # Direction
                    pwm_pairs[this_motor]["direction"] = "Forwards"
                    pins["maps"][current_pin_map][p]["action"]["arg3"] = "Forwards"                       
                    # Configure PWM objects for motor pins
                    if target_pin < 100:  # PWM currently only supported on Raspi
                        if pwm_count == 1:
                            # First motor, use first pair of reserved motor pin variables
                            pwm1 = GPIO.PWM(target_pin, 50)
                            pwm_count = 2                              
                            pwm2 = GPIO.PWM(int(pins["maps"][current_pin_map][p]["action"]["arg1"]), 50)
                        elif pwm_count == 3:
                            # Second motor, use second pair of reserved motor pin variables
                            pwm3 = GPIO.PWM(target_pin, 50)
                            pwm_count = 4                             
                            pwm4 = GPIO.PWM(int(pins["maps"][current_pin_map][p]["action"]["arg1"]), 50)
                        else:
                            print("You can only have two motors")
                        
                # If pin is a LED or other single pin PWM device
                elif pins["maps"][current_pin_map][p]["setting"] == "PWMOutputLed":
                    # Add name, current and default speed for PWM signal
                    pwm_general_pins[target_pin] = {}
                    pwm_general_pins[target_pin]["speeds"] = [0, int(pins["maps"][current_pin_map][p]["action"]["arg2"])]
                    print(pwm_general_pins)
                    if target_pin < 100: # Arduino PWM not currently supported
                        # Raspi
                        led_count += 1
                        # Create an ID from led_count to determine which reserved PWM object to use
                        pwm_general_pins[target_pin]["id"] = led_count
                        if led_count == 1:
                             led1 = GPIO.PWM(target_pin, 50)
                        elif led_count == 2:
                            led2 = GPIO.PWM(target_pin, 50)
                        else:
                            print("You can only use two dimmable LEDs in this version")
                    else:
                        print("Arduino PWM not currently supported.")
                    print(pwm_general_pins)

            # If pin is any type of input (Input, InputPullUp, InputPullDown)       
            elif "Input" in pins["maps"][current_pin_map][p]["setting"]:
                # Add input to events folder for loop to monitor
                event_times[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]
                if target_pin < 100:
                    # If Raspberry Pi pin, configure GPIO
                    if "PullDown" in pins["maps"][current_pin_map][p]["setting"]:
                        GPIO.setup(target_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    elif "PullUp" in pins["maps"][current_pin_map][p]["setting"]:
                        GPIO.setup(target_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    else:
                        GPIO.setup(target_pin, GPIO.IN)
                        
            # If pin is Arduino Analog pin, add input to events folder for loop to monitor
            elif "Analog" in pins["maps"][current_pin_map][p]["setting"]:
                print("EV times")
                # Check-frequency, number of loops between each pin read [count, readfrequency]
                pins["maps"][current_pin_map][p]["action"]["arg4"] = [0, 10]
                # Add input to events folder for loop to monitor
                event_times[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]
                
            print(msg)



# Save the default pinmap to a new map you can use later
def save_map(newmapname, reset_session_map="no"):
    global pins, current_pin_map
    print("SM")
    # Copy existing map to save name
    pins["maps"][newmapname] = pins["maps"][current_pin_map]
    print("Copied")
    if reset_session_map == "yes":
        # Save the map to new name and reset the session pin map back to factory settings
        running = "no"
        create_new_pinfile(scope="existing", mapname=current_pin_map)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        event_times = {}
        event_times_out = {}
        running = "yes"
    else:
        # Just save the map to another name without resetting current map
        print("Writing")
        write_pin_list()
        print(newmapname)
        current_pin_map = newmapname
    


# Configure settings for a single pin based on incoming details from browser
# Change scope to test to run without setting GPIO pins
def configure_pin(orders, scope="full"):
    global pins, pwm_count, pwm_pairs, current_pin_map, event_times, led_count, pwm_general_pins
    global pwm1, pwm2, pwm3, pwm4, led1, led2 # Reserved undeclared variables for two 2-pin PWM DC motors and 2 single-pin LEDs
    #   This allows the PWM objects created in this fucntion to be global

    # The example orders below would configure GPIO 17 as an input and set it to switch GPIO 4 on when HIGH and switch it off after
    #   input has returned to and stayed LOW for thirty seconds    
    # Input orders: 'config session gpio_17 Input myInputPin Low switchOut 4 0 Always 00:00 00:00 timeout 30'
    # Output orders: 'config session gpio_4 PWMOutputLed MyLed Low outManual 0 0 Always 00:00 00:00 Indefinite 0'
    
    # Split space-separated details (orders) sent from browser
    comms = orders.split(" ")
    current_pin_map = comms[1]
    # Flag to indicate function result and send message to browser
    pin_ok = "yes"

    # Create new map if it doesn't exist
    if current_pin_map not in pins["maps"]:
        create_new_pinfile(scope="existing", mapname=current_pin_map)
        
    # Get target_pin number from name string to use for GPIO operations, eg: "gpio_8" becomes 8, "D1" becomes 101
    pin_name = comms[2]
    if "gpio_" in pin_name:
        # Raspi, use GPIO number. This is used for GPIO operations
        target_pin = int(pin_name.replace("gpio_", ""))
    elif "D" in pin_name:
        # Add 100 to differentiate Arduino digital pin
        target_pin = int(pin_name.replace("D", "")) + 100
        if "PWM" in comms[3]: # PWM not supported on Arduino
            # Add 100 to target_pin to signify Arduino digital pin
            print("PWM not supported on Arduino")
            pin_ok = "PWM not supported on Arduino"
    elif "A" in pin_name:
        # Add 114 to differentiate Arduino analog pin
        target_pin = int(pin_name.replace("A", "")) + 114
        if "PWM" in comms[3]: # PWM not supported on Arduino
            # Add 100 to target_pin to signify Arduino digital pin
            print("PWM not supported on Arduino")
            pin_ok = "PWM not supported on Arduino"
    print(target_pin)
    if pin_ok != "yes":
        return pin_okay
    # Backup the selected pin in case of error
    backup_pin = pins["maps"][current_pin_map][pin_name]

    # Load basic details to the specified pin map
    pins["maps"][current_pin_map][pin_name]["setting"] = comms[3] # Output/PWMOutput Input/InputPullup/InputPullDown Analog
    pins["maps"][current_pin_map][pin_name]["nickname"] = comms[4] # Name to display on GPIO buttons
    pins["maps"][current_pin_map][pin_name]["default"] = comms[5] # Default state, Low/High
    pins["maps"][current_pin_map][pin_name]["status"] = comms[5] # Current state (live)
    
    # The type of action for the pin
    pins["maps"][current_pin_map][pin_name]["action"]["type"] = comms[6] # switchOut (input), outManual (output)
    if "switchout" in comms[6]:
        pins["maps"][current_pin_map][num_to_name(comms[7])]["partner"] = target_pin
    # Action details
    pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = int(comms[7]) # partner pin for switchOut
    if pins["maps"][current_pin_map][pin_name]["setting"] == "Analog":
        pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = float(comms[8]) # current reading for analog pins
    else:
        pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = int(comms[8]) # default PWM speed for digital

    # Timer and timout settings
    # If comms[9] == 'timer', execute actions only between comms[10] and comms[11]
    pins["maps"][current_pin_map][pin_name]["action"]["timer"] = comms[9]
    pins["maps"][current_pin_map][pin_name]["action"]["times"] = [comms[10], comms[11]]
    # It comms[12] != 'Indefinite', switch pin low after comms[13] seconds
    pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] = comms[12]
    pins["maps"][current_pin_map][pin_name]["action"]["timeout"] = comms[13]
    
    # load inputs into event_times folder so AAIMI knows to monitor their state during each loop
    # Include timing details for their actions, eg timeout if input is triggering an output
    if "Input" in comms[3] or "Analog" in comms[3]:
        event_times[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]
        if "A" in pin_name:
            pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = float(comms[14]) # Analog trigger point
            # Interval to read analog pin, default is 10 seconds
            pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = [0, 10]
            
    # Add output pin to event_times_out folder if they work on a timer or timeout
    if "Output" in comms[3]:
        # Only add output to event_times_out if pin has timer or timeout enabled
        if pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][pin_name]["action"]["timer"] == "setTimes":
            event_times_out[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]    
    print(pins["maps"][current_pin_map][pin_name])
    
    # Define standard Raspi GPIO pin (not PWM) and set outputs to default state
    if scope != "test" and "gpio" in pin_name:
        if "Output" in comms[3]:
            GPIO.setup(int(target_pin), GPIO.OUT)
            # Switch pin to default state if not set as PWM pin
            if comms[5] == "High" and comms[3] != "PWMOutput":
                GPIO.output(int(target_pin), True)
            elif comms[5] == "Low" and comms[3] != "PWMOutput":
                GPIO.output(int(target_pin), False)

        # Define inputs with pull-up or pull-down resistors if specified
        elif "Input" in comms[3]:
            if "PullDown" in comms[3]:
                GPIO.setup(int(target_pin), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            elif "PullUp" in comms[3]:
                GPIO.setup(int(target_pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(int(target_pin), GPIO.IN)
                
    
    if comms[3] == "PWMOutput" and "gpio" in pin_name:
        # Will be bi-directional DC motor
        
        # Create entries for direction and current speed
        pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = "Forwards"        
        pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0 # Current speed
        
        # Use pwm_count to decide which reserved pwm variables to use for motor pins
        pwm_count += 1
        pwm_pairs[comms[4]] = {}

        # Set second motor pin as output and store details
        GPIO.setup(int(comms[7]), GPIO.OUT)        
        pairpin = "gpio_" + str(comms[7])
        pins["maps"][current_pin_map][pairpin]["action"]["type"] = "OutputPartner"
        pins["maps"][current_pin_map][pairpin]["action"]["arg1"] = target_pin
        
        # The two gpio pin numbers for the motor, ie ['gpio_22', 'gpio_27']
        pwm_pairs[comms[4]]["pin_pair"] = [target_pin, comms[7]]
        # The identifier to determine which reserved PWM objects to use
        pwm_pairs[comms[4]]["id"] = pwm_count
        # Default state for motor when program starts: on or off
        pwm_pairs[comms[4]]["default"] = comms[5]
        # Current speed and default starting speed
        pwm_pairs[comms[4]]["pwm"] = [0, int(comms[8])]
        pwm_pairs[comms[4]]["direction"] = "Forwards"
        
        # Set objects for PWM pins         
        if pwm_count == 1:
            # Motor one, use first pair of reserved motor pin objects
            pwm1 = GPIO.PWM(target_pin, 50)
            pwm_count = 2                              
            pwm2 = GPIO.PWM(int(comms[7]), 50)
        elif pwm_count == 3:
            # Motor two, use second pair of reserved motor pin variables
            pwm3 = GPIO.PWM(target_pin, 50)
            pwm_count = 4                             
            pwm4 = GPIO.PWM(int(comms[7]), 50)


    elif comms[3] == "PWMOutputLed" and "gpio" in pin_name:
        # Will be single pin PWM device, LED, etc.
        # Add name, current and default speed for PWM signal
        pwm_general_pins[target_pin] = {}
        pwm_general_pins[target_pin]["speeds"] = [0, int(pins["maps"][current_pin_map][pin_name]["action"]["arg2"])]
        # Use led_count to identify which reserved pwm variable to use
        led_count += 1
        pwm_general_pins[target_pin]["id"] = led_count
        if led_count == 1:
            # Use first reserved variable for object
             led1 = GPIO.PWM(target_pin, 50)
        elif led_count == 2:
            # Use second reserved variable for object
            led2 = GPIO.PWM(target_pin, 50)
        else:
            print("You can only use two dimmable LEDs in this version")
        print(pwm_general_pins)

    # Write changes to JSON file
    write_pin_list()                                       
                                        


######### Bi-directional PWM motors (Raspberry Pi only)

# Start a PWM Motor or change direction of an already running motor
def start_motor(motor_name, direction):
    global pwm_pairs, pins, write_due, pwm1, pwm2, pwm3, pwm4
    # Set wait time to allow motor to stop spinning if changing rotation direction
    if direction != pwm_pairs[motor_name]["direction"]:
        time_to_wait = 2
        pwm_pairs[motor_name]["direction"] = direction
    else:
        time_to_wait = .0001   
    speed = pwm_pairs[motor_name]["pwm"][1]
    # Use first pin of pair if rotation is forward    
    if direction == "Forwards":
        pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
        pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])
        if pwm_pairs[motor_name]["id"] == 1:  # First motor
            pwm2.stop()
            time.sleep(time_to_wait)
            pwm1.start(speed)
        elif pwm_pairs[motor_name]["id"] == 3:  # Second motor
            pwm4.stop()
            time.sleep(time_to_wait)
            pwm13.start(speed) 
        pins["maps"][current_pin_map][pin_name]["status"] = "High"
        pins["maps"][current_pin_map][pair_name]["status"] = "Low"
        
    # Use second pin of pair if rotation is backwards      
    elif direction == "Backwards":
        pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
        pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])  
        if pwm_pairs[motor_name]["id"] == 1:  # First motor
            pwm1.stop()
            time.sleep(time_to_wait)
            pwm2.start(speed)
        elif pwm_pairs[motor_name]["id"] == 3:   # Second motor
            pwm3.stop()
            time.sleep(time_to_wait)
            pwm4.start(speed)
        pins["maps"][current_pin_map][pin_name]["status"] = "Low"
        pins["maps"][current_pin_map][pair_name]["status"] = "High"              
    pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = direction
    pwm_pairs[motor_name]["pwm"][0] = speed
    pwm_pairs[motor_name]["direction"] = direction
    pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = speed
    write_pin_list() 


# Switch a motor off
def stop_motor(motor_name):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4
    pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
    pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])
    if pwm_pairs[motor_name]["id"] == 1:  # First motor
        pwm2.stop()
        pwm1.stop()
    elif pwm_pairs[motor_name]["id"] == 3:   # Second motor
        pwm4.stop()
        pwm3.stop()  
    pwm_pairs[motor_name]["pwm"][0] = 0
    # Set current motor speed, and status for both pins
    pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0
    pins["maps"][current_pin_map][pin_name]["status"] = "Low"
    pins["maps"][current_pin_map][pair_name]["status"] = "Low"
    write_pin_list()


# Change the PWM duty cycle for a motor that is already running
def set_motor_speed(motor_name, direction, speed):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4
    pin_name = pwm_pairs[motor_name]["pin_pair"][0]
    if direction == pwm_pairs[motor_name]["direction"]:
        # If not changing direction, just adjust speed
        pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
        if direction == "Forwards":
            if pwm_pairs[motor_name]["id"] == 1:
                pwm1.ChangeDutyCycle(speed)
            elif pwm_pairs[motor_name]["id"] == 3:
                pwm3.ChangeDutyCycle(speed)
        elif direction == "Backwards":
            if pwm_pairs[motor_name]["id"] == 1:
                pwm2.ChangeDutyCycle(speed)
            elif pwm_pairs[motor_name]["id"] == 3:
                pwm4.ChangeDutyCycle(speed)
        pwm_pairs[motor_name]["pwm"][0] = speed
        pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = speed
    else:
        # If changing direction stop and restart motor in new direction at default speed
        start_motor(motor_name, direction)
        
    # Schedule file-write on next loop to reflect changes
    write_due = "yes"

        
####### General PWM outputs for Leds

# Start a PWM Led on or off at its default brightness
def start_stop_pwm_led(pwm_id_num, pwm_action):
    global pwm_general_pins, led2, led1, pins, current_pin_map
    pin_name = "gpio_" + str(pwm_id_num)
    
    # Switch off
    if pwm_action == 0:
        if pwm_general_pins[pwm_id_num]["id"] == 1:
            led1.stop()
        elif pwm_general_pins[pwm_id_num]["id"] == 2:
            led2.stop()
        pins["maps"][current_pin_map][pin_name]["status"] = "Low"
        pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = 0
        pwm_general_pins[pwm_id_num]["speeds"][0] = 0
        
    # Switch on
    elif pwm_action == 1:
        # Start PWM at default speed
        if pwm_general_pins[pwm_id_num]["id"] == 1:
            led1.start(pwm_general_pins[pwm_id_num]["speeds"][1])
        elif pwm_general_pins[pwm_id_num]["id"] == 2:
            led2.start(pwm_general_pins[pwm_id_num]["speeds"][1])
        pins["maps"][current_pin_map][pin_name]["status"] = "High"
        pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = pins["maps"][current_pin_map][pin_name]["action"]["arg2"]
        pwm_general_pins[pwm_id_num]["speeds"][0] = pwm_general_pins[pwm_id_num]["speeds"][1]


# Set the PWM duty cycle for a LED or other single pin device
def set_led_brightness(pwm_id_num, speed):
    global pwm_general_pins, led1, led2, pins, current_pin_map, write_due
    pin_name = "gpio_" + str(pwm_id_num)
    if pwm_general_pins[pwm_id_num]["id"] == 1:
        led1.ChangeDutyCycle(speed)
    elif pwm_general_pins[pwm_id_num]["id"] == 2:
        led2.ChangeDutyCycle(speed)
    pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = speed
    write_due = "yes"

############

# Reset all GPIO pins and set the pin configuration map to default.
def reset_program(full="existing"):
    global event_times, event_times_out
    # Stop main loop functions so other threads won't interrupt
    running = "no"
    # Reset GPIO and clear event arrays
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    event_times = {}
    event_times_out = {}
    create_new_pinfile(scope=full)
    load_pin_list()
    # Start main loop functions again
    running = "yes"

# Changed to a previously-saved map 
def change_map(newmap):
    global event_times, event_times_out, current_pin_map, pins
    if newmap in pins["maps"]:
        current_pin_map = newmap
        pins["current_map"] = newmap
        write_pin_list()
        running = "no"
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        print(current_pin_map)
        event_times = {}
        event_times_out = {}
        load_pin_list()
        running = "yes"
        
    else:
        print("No such map")

# Check timers if new hour or minute
def check_timers():
    global pins, current_pin_map, minute_store, hour_store, second_clock, event_times_out, active_hours, write_due

    # Register new time
    now = time.strftime("%H:%M:%S")
    now_times = now.split(":")
    time_to_check = now[:5]
    if minute_store != now_times[1]:
        minute_store = now_times[1]
    if hour_store != now_times[0]:
        hour_store = now_times[0]
        
    # Check inputs running on timers
    for timers in event_times:
        # Determine if pin is Raspi or Arduino and get name
        timer_name = str(num_to_name(int(timers)))
        # Is pin configured to work during set times?
        if pins["maps"][current_pin_map][timer_name]["action"]["timer"] == "setTimes":
            # Set input actions for pin as active so an event will trigger reaction
            if time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][0]:
                if timer_name not in active_hours:
                    active_hours.append(timer_name)
                    write_due == "yes"
            # Set input actions for pin as dormat so an event will not trigger reaction    
            elif time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][1]:
                if timer_name in active_hours:
                    active_hours.pop(timer_name)
                    write_due == "yes"
                if pins["maps"][current_pin_map][timer_name]["action"]["type"] == "swtchOut":
                    # Switch off partner output
                    if pins["maps"][current_pin_map][timer_name]["action"]["arg1"] <= 27:
                        GPIO.output(int(pins["maps"][current_pin_map][timer_name]["action"]["arg1"]), False)
                        pairpin = "gpio_" + str(pins["maps"][current_pin_map][timer_name]["action"]["arg1"])
                    else:
                        pairpin = "D" + str((int(pins["maps"][current_pin_map][timer_name]["action"]["arg1"]) - 100))
                        ard_command = pin_commands[pairpin][1]
                        switch(ard_command)
                    pins["maps"][current_pin_map][pairpin]["status"] = "Low"
            print(active_hours)
            
    # Check ouputs running on timers
    for timers in event_times_out:
        # Determine if pin is Raspi or Arduino
        timer_name = str(num_to_name(int(timers)))
        if pins["maps"][current_pin_map][timer_name]["action"]["type"] == "outTimer":
            if time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][0]:
                # Pin is within its operating time
                active_hours.append(timer_name)
                
                write_due == "yes"

                # Switch the pin High 
                if "gpio_" in timer_name: # Raspi
                    GPIO.output(int(timers), True)
                else:  # Arduino
                    ard_command = pin_commands[timer_name][0]
                    switch(ard_command)                    
                event_times_out[timers][0] = int(time.time())
                pins["maps"][current_pin_map][timer_name]["status"] = "High"
                
            elif time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][1]:
                # Pin is now outside its operating time
                if timer_name in active_hours:
                    active_hours.pop(active_hours.index(timer_name))
                write_due == "yes"

                # Switch pin Low
                if "gpio_" in timer_name:   # Raspi             
                    GPIO.output(int(timers), False)
                else:  # Arduino
                    ard_command = pin_commands[timer_name][1]
                    switch(ard_command)                     
                pins["maps"][current_pin_map][timer_name]["status"] = "Low"
                
    # Sync loop count to correct second so loop ends on start of new minute next time
    second_clock[0] = int(now_times[2])

    
            
# Accept commands from browser and route to relevant functions
def react(order):
    global pins, current_pin_map, event_times_out, running, pwm_pairs, event_times, pwm_count, pwm_general_pins, led_count
    print(order)
    # order is space-separated strings
    commands = order.split(" ")

    # PWM motor speed: motor, direction, speed
    # Example order: 'speedMotor myMotor Forwards 50'
    if commands[0] == "speedMotor":
        set_motor_speed(commands[1], commands[2], int(commands[3]))

    # PWM LED speed: LED, speed
    # Example order: 'speedPWM myLED 50'
    if commands[0] == "speedPWM":
        set_led_brightness(int(commands[1]), int(commands[2]))

    # Switch a PWM motor on at its default speed   ???????????
    # Example: 'switchMotor myMotor 1 Forwards'
    elif commands[0] == "switchMotor":
        
        pinName = "gpio_" + commands[2]
        if commands[2] == "1":
            start_motor(commands[1], commands[3])            
        else:
            stop_motor(commands[1]) 

    # Switch a PWM LED on or off
    # Example: 'switchPWM 4 1' will switch GPIO4 on
    elif commands[0] == "switchPWM":
        pinName = "gpio_" + str(commands[1])
        start_stop_pwm_led(int(commands[1]), int(commands[2])) 
        if int(commands[2]) == 1:          
            pins["maps"][current_pin_map][pinName]["status"] = "High"
        else:
            pins["maps"][current_pin_map][pinName]["status"] = "Low"
        write_pin_list()

    # Switch an output on or off
    # Example: 'switch 1 4'        
    elif commands[0] == "switch":
        print("StartingLed")
        print(commands)
        if int(commands[2]) <= 27:
            # Will be Pi GPIO
            pinName = "gpio_" + commands[2]
            print(commands[1])
            if commands[1] == "1":
                # Switch pin High
                print("switching high")
                GPIO.output(int(commands[2]), True)
                pins["maps"][current_pin_map][pinName]["status"] = "High"
                if int(commands[2]) in event_times_out:
                    event_times_out[int(commands[2])][0] = int(time.time())
                # Log time if output is operated by an input pin on timeout
                if "partner" in pins["maps"][current_pin_map][pinName]:
                    if pins["maps"][current_pin_map][pinName]["partner"] in event_times:
                        event_times[pins["maps"][current_pin_map][pinName]["partner"]][0] = time.time()
            else:
                print("Low")
                # Switch pin Low
                GPIO.output(int(commands[2]), False)
                pins["maps"][current_pin_map][pinName]["status"] = "Low"
        else:
            # Will be Arduino digital pin
            pinName = "D" + str(int(commands[2]) - 100)
            if pinName in pin_commands:
                if commands[1] == "1":
                    # Send On character to Arduino to switch pin High
                    ard_command = pin_commands[pinName][0]
                    switch(ard_command)
                    if int(commands[2]) in event_times_out:
                        event_times_out[int(commands[2])][0] = int(time.time())
                    pins["maps"][current_pin_map][pinName]["status"] = "High"
                    if "partner" in pins["maps"][current_pin_map][pinName]:
                        if pins["maps"][current_pin_map][pinName]["partner"] in event_times:
                            event_times[pins["maps"][current_pin_map][pinName]["partner"]][0] = time.time()                    
                    
                else:
                    # Send Off character to Arduino to switch pin Low
                    ard_command = pin_commands[pinName][1]
                    switch(ard_command)
                    pins["maps"][current_pin_map][pinName]["status"] = "Low"                
        write_pin_list()

    # Change settings for given pin    
    elif commands[0] == "config":
        configure_pin(order)
        
    # Start and stop loop actions
    # Example: 'startLoop on'     
    elif commands[0] == "startLoop":
        if commands[1] == "on" and running != "yes":
            # Start main loop actions running and load pin file
            GPIO.setmode(GPIO.BCM)
            load_pin_list()
            running = "yes"
            print("Pins are ready to use")
            
        elif commands[1] == "off":
            # Stop loop actions and reset all pins and lists
            # The program will stop monitoring pins and just monitor socket for command to start again
            running = "no"
            GPIO.cleanup()
            pins = {}
            pwm_pairs = {}
            event_times = {}
            event_times_out = {}
            pwm_count = 0
            pwm_general_pins = {}
            led_count = 0

    # Clean up GPIO pins and shut down the Raspberry Pi
    # Example: 'killAll'
    elif commands[0] == "killAll":
        running = "no"
        GPIO.cleanup()
        os.system("shutdown now")
        
    # Reset all GPIO pins and set the pin configuration map to default.    
    elif commands[0] == "reset":
        reset_program()

    # Save the current pin configuration as a new map    
    elif commands[0] == "save":
        save_map(commands[1])

    # Change to a previously-saved pin map
    elif commands[0] == "choose_map":
        change_map(commands[1])

# Listen for incomming requests from web GUI and send to react() for routing to functions
def socket_watch():
    con_stat = ""
    dstore = ""
    while True:
        try:
            # Configure socket connection
            HOST = '127.0.0.1' 
            PORT = socketport 
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            # Start listening for requests
            s.listen(1)
            conn, addr = s.accept()
            con_stat = "in"
            while 1:
                data = conn.recv(1024)
                dstore = data
                if len(data) > 0:
                    react(data)
                if not data:
                    break
            conn.close()
            con_stat = "out"
        except:
            t_state = "gone"
            if con_stat == "in":
                con_stat = "out"
                conn.close()
            time.sleep(2)
            print("Socket failed")

# Start thread to run socket in background
print("Starting main socket thread")
try:
    sock_thread = threading.Thread(target = socket_watch)
    sock_thread.start()
except:
    GPIO.cleanup()
    print('\n! Keyboard interrupt, quitting threads2.\n')
    os._exit(1)

check_timers()


# Start main loop to monitor pins
while True:
    try:
        # If running == "no", don't monitor pins
        if running == "yes":
            # Flag to update details file if there are changes
            changed = "no"
            # Partner pin for DC motor, or output pin controlled by input
            pairpin = ""
            # String to identify pin name
            event_pin_name = ""

            # Check state of any declared inputs.
            if len(event_times) > 0: 
                for et in event_times:
                    pin_status = "default" # Flag as default state until proven otherwise

                    # Determine if pin is in react state based on device type, pin type and default state                    
                    # If Raspi
                    if et <= 27:
                        event_pin_name = "gpio_" + str(et)
                        # If set to react when pin goes High
                        if GPIO.input(int(et)) == True and pins["maps"][current_pin_map][event_pin_name]["default"] == "Low":
                            pin_status = "inEventHigh"
                        # If set to react when pin goes Low    
                        if GPIO.input(int(et)) == False and pins["maps"][current_pin_map][event_pin_name]["default"] == "High":
                            pin_status = "inEventLow"
                            
                    # If Arduino digital input (Only D11 and D12 can be inputs)
                    elif et == 111 or et == 112:
                        event_pin_name = "D" + str(int(et) - 100)
                        pin_reading = check_digital_sensor(pin_commands[event_pin_name][0])
                        # If set to react when pin goes High
                        if pin_reading == 1 and pins["maps"][current_pin_map][event_pin_name]["default"] == "Low":
                            pin_status = "inEventHigh"
                        # If set to react when pin goes Low
                        elif pin_reading == 0 and pins["maps"][current_pin_map][event_pin_name]["default"] == "High":
                            pin_status = "inEventLow"
                            
                    # If Arduino analog pin, check whether reading is within its allowed range
                    elif et >= 114:
                        event_pin_name = "A" + str(int(et) - 114)
                        # If specified number of loops have passed since last read
                        if pins["maps"][current_pin_map][event_pin_name]["action"]["arg4"][0] > pins["maps"][current_pin_map][event_pin_name]["action"]["arg4"][1]:
                            # Reset read-frequency counter
                            pins["maps"][current_pin_map][event_pin_name]["action"]["arg4"][0] = 0
                            # Get pin reading from Arduino
                            pin_reading = float(check(pin_commands[event_pin_name][0]))
                            print(pin_reading)
                            if pins["maps"][current_pin_map][event_pin_name]["action"]["arg2"] != pin_reading:
                                # Set flag to update pin details file if reading has changed by more than 10mV
                                if pins["maps"][current_pin_map][event_pin_name]["action"]["arg2"] - pin_reading > .01 or pin_reading - pins["maps"][current_pin_map][event_pin_name]["action"]["arg2"] > .01:
                                    changed = "yes"                                
                                pins["maps"][current_pin_map][event_pin_name]["action"]["arg2"] = pin_reading
                            # If set to react when analog reading higher than trigger point
                            if pin_reading >= pins["maps"][current_pin_map][event_pin_name]["action"]["arg3"] and pins["maps"][current_pin_map][event_pin_name]["default"] == "Low":
                                pin_status = "inEventHigh"
                            # If set to react when analog reading lower than trigger point
                            elif pin_reading <= pins["maps"][current_pin_map][event_pin_name]["action"]["arg3"] and pins["maps"][current_pin_map][event_pin_name]["default"] == "High":
                                pin_status = "inEventLow"
                        else:
                            # Pin not due for reading, increment counter and leave pin status unchanged
                            pins["maps"][current_pin_map][event_pin_name]["action"]["arg4"][0] += 1
                            pin_status = pins["maps"][current_pin_map][event_pin_name]["status"]

                    # If not in default state    
                    if "inEvent" in pin_status:    
                        # Log time of event and update pin status if changed
                        event_times[et][0] = time.time()
                        # Get new pin status
                        status_filler = pin_status.replace("inEvent", "")
                        if pins["maps"][current_pin_map][event_pin_name]["status"] != status_filler:
                            # If this is not an existing event, perform event actions for pin
                            pins["maps"][current_pin_map][event_pin_name]["status"] = status_filler
                            
                            # Switch an output on if pin is configured as switchout.
                            if pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "switchOut":
                                pairnum = pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]
                                
                                if pins["maps"][current_pin_map][event_pin_name]["action"]["timer"] == "setTimes":
                                # If pin's action is on a timer, check if within start and finish times                                    
                                    if event_pin_name in active_hours:
                                        # Switch partner output on
                                        if int(pairnum) <= 27:  # Raspi
                                            pairpin = "gpio_" + str(pairnum)
                                            GPIO.output(int(pairnum), True)
                                        elif int(pairnum) >= 100 and int(pairnum) <= 113:  # Arduino
                                            pairpin = "D" + str(int(pairnum) - 100)
                                            ard_command = pin_commands[pairpin][0]
                                            switch(ard_command)
                                        pins["maps"][current_pin_map][pairpin]["status"] = "High"
                                        
                                else:
                                    # If action set to go at any time                                    
                                    if int(pairnum) <= 27:  # Raspi
                                        pairpin = "gpio_" + str(pairnum)
                                        GPIO.output(int(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]), True)
                                                                            
                                    elif int(pairnum) >= 100 and int(pairnum) <= 113: # Arduino digital pin
                                        pairpin = "D" + str(int(pairnum) - 100)
                                        print(pairpin)
                                        ard_command = pin_commands[pairpin][0]
                                        switch(ard_command)                                                                                
                                    pins["maps"][current_pin_map][pairpin]["status"] = "High"
                                if pins["maps"][current_pin_map][pairpin]["status"] == "High":
                                    # Log switching time if pair pin is also has timeout set. Pin will switch back according to lowest timeout
                                    if int(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]) in event_times_out:
                                        event_times_out[pairnum][0] = int(time.time())
                                    
                                    
                            # Increment the event count if pin is set as 'countRecord'.
                            elif pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "countRecord":
                                pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"] += 1
                                print("Count: " + str(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]))
                            # Note change to trigger file-write at end of loop
                            changed = "yes"

                    # If in default state, check if changed and if so, switch off any current actions for pin            
                    else:
                        # Exclude analog pin if it has not been read this loop
                        if "A" in event_pin_name and pins["maps"][current_pin_map][event_pin_name]["action"]["arg4"][0] != 0:
                            pass
                        else:
                            # update pin status to Low if changed
                            if pins["maps"][current_pin_map][event_pin_name]["status"] != pins["maps"][current_pin_map][event_pin_name]["default"]:
                                pins["maps"][current_pin_map][event_pin_name]["status"] = pins["maps"][current_pin_map][event_pin_name]["default"]
                                changed = "yes"
                                
                            # If pin has partner output and timeout is set, check time elapsed since pin was last high
                            if pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "switchOut":
                                pairnum = pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]
                                pairpin = str(num_to_name(int(pairnum)))    
                                # Check if output partner pin is HIGH
                                if pins["maps"][current_pin_map][pairpin]["status"] == "High" and pins["maps"][current_pin_map][event_pin_name]["action"]["timeout_type"] != "Indefinite":
                                    # Calculate time that input pin has been LOW
                                    gone = int(time.time()) - int(event_times[et][0])
                                    # Switch off partner output if timeout elapsed
                                    if event_times[et][2] == "timeout" and gone > int(event_times[et][1]):
                                        print("OFF")
                                        if "gpio" in pairpin: # Raspi
                                            GPIO.output(int(pairnum), False)
                                        elif "D" in pairpin:  # Arduino
                                            ard_command = pin_commands[pairpin][1]
                                            switch(ard_command)
                                        pins["maps"][current_pin_map][pairpin]["status"] = "Low"
                                        changed = "yes"                            

            if len(event_times_out) > 0:
                # Check any outputs set as timeout and switch LOW if time has elapsed since they were switched HIGH
                for et in event_times_out:
                    if et <= 27:  # Raspi
                        if GPIO.input(int(et)) and event_times_out[et][2] == "timeout":
                            gone = int(time.time()) - int(event_times_out[et][0])
                            if gone > int(event_times_out[et][1]):
                                print(gone, int(time.time()), int(event_times_out[et][0]))
                                event_pin_name = "gpio_" + str(et)
                                GPIO.output(int(et), False)
                                pins["maps"][current_pin_map][event_pin_name]["status"] = "Low"
                                changed = "yes"
                    elif et >= 100 or et <= 113:   # Arduino
                        event_pin_name = "D" + str(int(et) - 100)
                        if pins["maps"][current_pin_map][event_pin_name]["status"] == "High" and event_times_out[et][2] == "timeout":
                            print(int(time.time()) - int(event_times_out[et][0]), int(event_times_out[et][1]))
                            gone = int(time.time()) - int(event_times_out[et][0])
                            if gone > int(event_times_out[et][1]):
                                ard_command = pin_commands[event_pin_name][1]
                                switch(ard_command)
                                pins["maps"][current_pin_map][event_pin_name]["status"] = "Low"
                                changed = "yes"                                           
                                
            if changed == "yes" or write_due == "yes":
                # Write full pinlist to file for browser access
                write_pin_list()
                write_due = "no"
            time.sleep(1)
            
        else:
            # Loop is off, do nothing
            time.sleep(1)
            
        second_clock[0] += 1
        # If minute is ending, check timers and sync second_clock with real seconds
        if second_clock[0] >= second_clock[1]:
            second_clock[0] = 0
            check_timers()            
            
            
    except (KeyboardInterrupt, SystemExit):
        # Clean up pins and exit program
        GPIO.cleanup()
        print("EXIT")
        os._exit(1)

