#!/bin/bash

# AAIMI GPIO 0.3
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
import requests
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
# For outputs (All digital pins except D11 and D12) switch-on is first entry, switch-off is second
# For inputs (D11 and D12) and analog inputs, first entry is to read the sensor, second entry is not used
pin_commands = {"D2": ["q", "r"], "D3": ["s", "t"], "D4": ["u", "v"], "D5": ["w", "x"], "D6": ["y", "z"], "D7": ["i", "j"], "D8": ["k", "l"], "D9": ["m", "n"],\
                "D10": ["o", "p"], "D11": ["K", "L"], "D12": ["M", "N"], "D13": ["O", "P"], "A0": ["a", "A"], "A1": ["b", "B"], "A2": ["c", "C"], "A3": ["d", "D"], "A4": ["e", "E"], "A5": ["f", "F"]}

# Flag to write changes to file only at end of loop
# This saves rapid file-writes when using PWM speed adjustment slider in GUI
write_due = "no"

# Status of loop.
# If "no", program does not monitor pins, just waits for socket commands
# When start signal from GUI received, this will change to "yes" and program will load and monitor pins
running = "no"

# Pins set as PWM dual-directional motor outputs
#  The two wires for each motor, and the default, and current speed
pwm_pairs = {}
ard_pwm_pairs = {}

# Count to determine which reserved variable AAIMI will use to define GPIO PWM objects for DC motor pins
pwm_count = 0

# Stepper motor pins ordered for clockwise and anti-clockwise rotation
stepper_motor_pins = {}
stepper_motor_pins_reverse = {}

# Create stepping sequences for stepper motors
stepper_orders = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]

# Hold the next required positional change requested by user for a stepper motor 
next_stepper_move = [] # [motorName, target_position]

# Stepper motors currently in oscillating mode
# Stores current moving/pausing state and next oscillating direction to move after pause
oscillating = {}  # oscillating = {motorName: {"state": "pausing", "next: "right"}}

# Flag to tell loop there is an active oscillating motor to control
oscillating_on = "off"

# General single-pin PWM devices like leds that connect back to GND
pwm_general_pins = {}
# Count to determine which reserved variable AAIMI will use to define single GPIO PWM object
led_count = 0

# Input and output pins timout and timer settings
# If both of these are empty the main loop will not monitor any pins
# Input pins
event_times = {}
# Output pins with timer/timeout set
event_times_out = {}
# A list of pins currently within their active timer range
active_hours = []

# Time variables, second_clock[0] is loop count, syncs to real-word settings every minute
# These are used to monitor timer scedules and timeouts
second_clock = [0, 60]
minute_store = "00"
hour_store = "00"

### Email settings #############

# Use a dedicated system Gmail account to send emails when a specific pin goes High
# Use email?
email_enabled = "no"

# By default the user enters the system email password in the web GUI to avoid storing it in code?
# After system reboot email will not operate until user has re-enterd the password
pass_entered = "no"

if email_enabled == "yes":
    import aaimi_email_out
    # Dedicated Gmail address for system to use.
    # You'll need to modify settings for the Gmail account to allow third-party applications
    aaimi_email_out.system_email = "yourSystemEmail@gmail.com"
    
    # To avoid the need to re-enter the system email password after each restart you can
    ### set your password below, then change the pass_entered variable to 'yes'. (Less secure)
    aaimi_email_out.system_pass = ""
    
    # Your email account (any type) to receive pin notification emails
    aaimi_email_out.user_email = "yourEmail@yourMail.com"
    
#######

##### HTTP Settings #############

# Send HTTPS requests to a website with two parameters when a specific input pin goes High
# Use only with HTTPS-enabled websites or protected LAN-based servers.
http_enabled = "no"
if http_enabled == "yes":
    url_to_send_to = "https://yourWebsite.php"

    # Is a username and password required for website?
    pass_required = "yes"
    user_name = "yourName"

    # By default the user enters the website password in the web GUI to avoid storing it in code?
    # You can change the website_pass_entered variable to 'yes' and enter you website password below. (Less secure)
    website_pass_entered = "no"
    website_pass = ""
    
    # Create a mock user-agent, some servers won't allow HTTP requests without one
    user_agent = {'User-agent': 'Mozilla/5.0'}

#######
    
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
##            reading = str(arduino.readline()).replace("\n", "")
##            return float(reading)
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


# Write new or updated pin details to JSON file for JS to display in browser
def write_pin_list():
    container = []
    container.append(pins)
    with open(pinlist, 'w') as pindata:
        json.dump(container, pindata)

        
# Create a new JSON pin file for factory reset
# If scope is "new", will create list from scratch and remove all saved pin maps.
# Otherwise it will just rewrite the currently open map
def create_new_pinfile(scope="new", mapname="session"):
    global pins, current_pin_map
    if scope == "new":
        print("NEW")
        # Delete existing pin file
        pins = {}
        pins["current_map"] = "session"
        pins["maps"] = {}
        pins["maps"]["session"] = {}
    else:
        # Create new entry for specified mapname
        pins["maps"][mapname] = {}
    # Create entries for all Raspi pins from gpio_2 to gpio_27
    pincount = 2
    print("Starting Pi")
    while pincount <= 27:
        keystring = "gpio_" + str(pincount)       
        pins["maps"][mapname][keystring] = {}
        pins["maps"][mapname][keystring]["status"] = "NA"
        pins["maps"][mapname][keystring]["setting"] = "Unset"  # Input, output, analog
        pins["maps"][mapname][keystring]["default"] = "Pending"  # Default state for pin
        pins["maps"][mapname][keystring]["nickname"] = "nickname"
        pins["maps"][mapname][keystring]["action"] = {}
        pins["maps"][mapname][keystring]["action"]["type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["arg1"] = 0 #Partner pin, second motor/stepper wire, LED PWM speed
        pins["maps"][mapname][keystring]["action"]["arg2"] = 0  # Default PWM speed, third stepper wire
        pins["maps"][mapname][keystring]["action"]["arg3"] = 0   # motor direction, fourth stepper wire
        pins["maps"][mapname][keystring]["action"]["arg4"] = 0 # current PWM speed       
        pins["maps"][mapname][keystring]["action"]["timer"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["timeout"] = 0
        pins["maps"][mapname][keystring]["action"]["timeout_type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["times"] = ["00:00", "00:00"]      
        pincount += 1

    # Create entries for all Arduino digital and analog pins
    pincount = 0
    print("Starting Ard")
    while pincount <= 19:
        if pincount <= 13:
            # create digital pins first, D0 to D13
            keystring = "D" + str(pincount)
        else:
            # Create analog pins, A0 to A5
            keystring = "A" + str(pincount - 14)
        pins["maps"][mapname][keystring] = {}
        pins["maps"][mapname][keystring]["status"] = "NA"
        pins["maps"][mapname][keystring]["setting"] = "Unset"  # Input, output, analog
        pins["maps"][mapname][keystring]["default"] = "Pending" # Default state for pin
        pins["maps"][mapname][keystring]["nickname"] = "nickname" # Name for pin
        pins["maps"][mapname][keystring]["action"] = {}
        pins["maps"][mapname][keystring]["action"]["type"] = "Pending" # switchOut, countRecord, outManual, sendEmail, sendWebRequest
        pins["maps"][mapname][keystring]["action"]["arg1"] = 0  # Partner pin
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


# Send a POST request to a website with two values if a pin set as HTTP goes High
def send_web_request(web_pin):
    global website_pass_entered, pass_required
    if website_pass_entered == "yes" or pass_required == "no":
        contents = {}
        
        # GUI user can select a default key/value pair to send (pin name is default value) or choose custom value
        # Build first key/value for request
        if pins["maps"][current_pin_map][web_pin]["action"]["httpvalue1"] == "gpioPinName":
            # Default value, use GPIO pin name
            contents[pins["maps"][current_pin_map][web_pin]["action"]["httpKey1"]] = web_pin 
        else:
            # Use pin's custom message
            contents[pins["maps"][current_pin_map][web_pin]["action"]["httpKey1"]] = pins["maps"][current_pin_map][web_pin]["action"]["httpvalue1"]

        # Build second key/value for request. There are two default choices for this value: pin state or analog value.
        # Otherwise use the pin's custom value
        if pins["maps"][current_pin_map][web_pin]["action"]["httpvalue2"] == "gpioPinState":
            # Use Low/High state of pin
            contents[pins["maps"][current_pin_map][web_pin]["action"]["httpKey2"]] = pins["maps"][current_pin_map][web_pin]["status"]
        elif pins["maps"][current_pin_map][web_pin]["action"]["httpvalue2"] == "analogValue":
            # Use analog reading
            contents[pins["maps"][current_pin_map][web_pin]["action"]["httpKey2"]] = str(pins["maps"][current_pin_map][web_pin]["action"]["arg2"])
        else:
            # Use pin's custom message
            contents[pins["maps"][current_pin_map][web_pin]["action"]["httpKey2"]] = pins["maps"][current_pin_map][web_pin]["action"]["httpvalue2"]
            
        # Add time to message
        contents["time"] = time.strftime("%d:%H:%M")    
        # Send the request with or without user credentials
        if pass_required == "yes":
            print("Sending")
            website_request = requests.post(url_to_send_to, params=contents, headers=user_agent, auth=(user_name, website_pass))
        else:
            website_request = requests.get(url_to_send_to, params=contents, headers=user_agent)
        website_reply = website_request.text
        print(str(website_reply))
            

#  Numbers are added to the pin numbers for Arduino pins to create numeric identifiers that differentiate from Pi pins
#  Convert those numbers to pin names
def num_to_name(num):
    """
    (int) -> str
    Get IO pin name from its numeric identifier
    >> num_to_name(8)
    gpio_8
    >> num_to_name(107)
    D7
    >>num_to_name(115)
    A1
    """
    # Pi pin numeric identifiers are the actual GPIO number
    if num <= 27:
        pname = "gpio_" + str(num)
    # 100 is added to Arduino digital pin numeric identifiers
    elif num >= 100 and num <= 113:
        pname = "D" + str(int(num) - 100)
    # 114 is added to Arduino analog pin numeric identifiers
    elif num >= 114:
        pname = "A" + str(int(num) - 114)
    return pname

    
# Load the list of GPIO configurations from file and define the inputs and outputs from the chosen pin map
# This is triggered from after start_loop command from GUI, and also after command to change pin maps
def load_pin_list():
    global pins, current_pin_map, pwm_pairs, event_times, pwm_count, pwm_general_pins, led_count, stepper_motor_pins 
    global pwm1, pwm2, pwm3, pwm4, led1, led2 # Reserved variables for PWM motor and LED GPIO objects
    
    # Read JSON pin file and determine the current map
    print("opening")
    with open(pinlist) as source_file:
        all_pin_maps = json.load(source_file)
        pins = all_pin_maps[0]
        current_pin_map = pins["current_map"]
    print("Loaded")
    
    # Load variables and details for all active pins and configure GPIO settings
    for p in pins["maps"][current_pin_map]:
        print(p)
        
        # Only get details from pins that have been defined
        if pins["maps"][current_pin_map][p]["setting"] != "Unset":
            
            # Configure stepper motor pins (Raspberry Pi pins only)
            if "Stepper" in pins["maps"][current_pin_map][p]["setting"]:
                target_pin = int(str(p.replace("gpio_", "")))
                stepper_name = str(pins["maps"][current_pin_map][p]["nickname"])

                # Create forward and reverse pin arrays to operate stepper then configure pins
                stepper_motor_pins[stepper_name] = [int(target_pin), int(pins["maps"][current_pin_map][p]["action"]["arg1"]),\
                                                    int(pins["maps"][current_pin_map][p]["action"]["arg2"]), int(pins["maps"][current_pin_map][p]["action"]["arg3"])]
                stepper_motor_pins_reverse[stepper_name] = [int(pins["maps"][current_pin_map][p]["action"]["arg3"]),\
                                                            int(pins["maps"][current_pin_map][p]["action"]["arg2"]), int(pins["maps"][current_pin_map][p]["action"]["arg1"]), int(target_pin)]
                
                for pin in stepper_motor_pins[stepper_name]:
                    print("Setup pins")
                    GPIO.setup(int(pin), GPIO.OUT)
                    GPIO.output(int(pin), False)

                # Add to time monitoring if stepper is working on timer or timeout
                if pins["maps"][current_pin_map][p]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][p]["action"]["timer"] == "setTimes":
                    # Add to events folder for loop to monitor if timer or timeout set  [lastevent, timeoutseconds, timer/timeout]
                    event_times_out[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]                    
                    
            # All other types of pins (Raspberry Pi and Arduino)
            else:
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
                    # Define pin as output and switch High or Low depending on its default setting and board type
                    if "gpio_" in p:
                        # Raspberry Pi pin
                        GPIO.setup(target_pin, GPIO.OUT)
                        # Set pin to its default state if not PWM output
                        if pins["maps"][current_pin_map][p]["default"] == "Low" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                            GPIO.output(target_pin, False)
                            pins["maps"][current_pin_map][p]["status"] = "Low"
                        elif pins["maps"][current_pin_map][p]["default"] == "High" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                            GPIO.output(target_pin, True)
                            pins["maps"][current_pin_map][p]["status"] = "High"
                            
                    else:
                        # Arduino pin, set to its default state
                        if pins["maps"][current_pin_map][p]["default"] == "Low" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                            switch(pin_commands[p][1])
                        elif pins["maps"][current_pin_map][p]["default"] == "High" and "PWMOutput" not in pins["maps"][current_pin_map][p]["setting"]:
                            switch(pin_commands[p][0])
                    print("Switched")

                    # Add to events folder for loop to monitor if timer or timeout set  [lastevent, timeoutseconds, timer/timeout]       
                    if pins["maps"][current_pin_map][p]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][p]["action"]["timer"] == "setTimes":
                        event_times_out[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]
                    
                    # If pin is a bi-directional motor
                    if pins["maps"][current_pin_map][p]["setting"] == "PWMOutput":
                        if "gpio" in p:
                            
                            # Increment motor count to determine which reserved motor objects to use
                            pwm_count += 1

                        # Get motor name and ad entry to motor array    
                        this_motor = pins["maps"][current_pin_map][p]["nickname"]
                        pwm_pairs[this_motor] = {}
                        
                        # The two gpio pin numeric identifiers for the motor, ie ['gpio_22', 'gpio_27'] become [22, 27]
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
                    
##                    # Check-frequency, number of loops between each pin read [count, readfrequency]
##                    pins["maps"][current_pin_map][p]["action"]["arg4"] = [0, 10]
                    
                    # Add input to events folder for loop to monitor
                    event_times[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]


# Configure settings for a single pin based on incoming space-separated string from browser
# Change scope to test to run without setting GPIO pins
def configure_pin(orders, scope="full"):
    global pins, pwm_count, pwm_pairs, current_pin_map, event_times, led_count, pwm_general_pins
    global pwm1, pwm2, pwm3, pwm4, led1, led2 # Reserved undeclared variables for two 2-pin PWM DC motors and 2 single-pin LEDs
    global stepper_motor_pins_reverse, stepper_motor_pins

    # The example orders below would configure GPIO 17 as an input and set it to switch GPIO 4 on when HIGH and switch it off after
    #   input has returned to and stayed LOW for thirty seconds
    # EXAMPLES:
    # Input orders: 'config session gpio_17 Input myInputPin Low switchOut 4 0 Always 00:00 00:00 timeout 30'
    # Output orders: 'config session gpio_4 PWMOutputLed MyLed Low outManual 0 0 Always 00:00 00:00 Indefinite 0'
    
    # Split space-separated details (orders) sent from browser
    comms = orders.split(" ")
    # Choose the name of the pin map to add the pin to
    current_pin_map = comms[1]
    # Flag to indicate function is proceeding without errors
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
    pins["maps"][current_pin_map][pin_name]["setting"] = comms[3] # Output/PWMOutput Input/InputPullup/InputPullDown Analog Stepper
    pins["maps"][current_pin_map][pin_name]["nickname"] = comms[4] # Name to display on GPIO buttons
    pins["maps"][current_pin_map][pin_name]["default"] = comms[5] # Default state, Low/High
    pins["maps"][current_pin_map][pin_name]["status"] = comms[5] # Current state (live)
    
    # The type of action for the pin
    pins["maps"][current_pin_map][pin_name]["action"]["type"] = comms[6] # switchOut (input), outManual (output) sendEmail sendWebRequest

    # Stepper Motor
    if "Stepper" in comms[3]:
        stepper_motor_pins[comms[4]] = []
        # Get the other three stepper pins for motor
        pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = comms[7] # Second motor pin (B) 23
        pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = comms[8]  # third motor pin (C) 24
        pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = comms[14]   # Fourth motor pin (D) 8
        
        # Create forward and reverse pin arrays to operate stepper
        stepper_motor_pins[comms[4]] = [int(target_pin), int(comms[7]), int(comms[8]), int(comms[14])]
        stepper_motor_pins_reverse[comms[4]] = [int(comms[14]), int(comms[8]), int(comms[7]), int(target_pin)]

        # Configure all stepper pins
        for pin in stepper_motor_pins[comms[4]]:
            print("Setup pins")
            GPIO.setup(pin,GPIO.OUT)
            GPIO.output(pin, False)

        # Stepper motor speed details
        pins["maps"][current_pin_map][pin_name]["action"]["default_speed"] = float(comms[15]) # default starting speed .006
        pins["maps"][current_pin_map][pin_name]["action"]["speed"] = float(comms[15]) # current speed .006

        # Stepper motor position
        # # Program uses 0-360 degree positioning with zero at twelve oclock.
        ## GUI uses -180-180 degree positioning, meaning - 90 degrees from GUI will become 270 degrees for program calculation
        if int(comms[16]) >= 0:
            pins["maps"][current_pin_map][pin_name]["action"]["default_pos"] = int(comms[16]) # default starting position
        else:
            pins["maps"][current_pin_map][pin_name]["action"]["default_pos"] = 180 + (180 + comms[16])
        pins["maps"][current_pin_map][pin_name]["action"]["pos"] = int(pins["maps"][current_pin_map][pin_name]["action"]["default_pos"])   # current position

        # Multiplier to convert full steps to degrees to achieve 360 deg rotation with motor's gearing and step-ration
        pins["maps"][current_pin_map][pin_name]["action"]["adjuster"] = float(comms[18])  

        # Choose whether motor is manually driven or automatically oscillates between set positions
        pins["maps"][current_pin_map][pin_name]["action"]["rotation_type"] = str(comms[17])  # manualPosition or "oscillating"
        
        # Set left and right stopping points for oscillation
        # Left stopping point
        if comms[19] >= 0: 
            pins["maps"][current_pin_map][pin_name]["action"]["left_pos"] = int(comms[19])
        else:
            pins["maps"][current_pin_map][pin_name]["action"]["left_pos"] = 180 + (180 + comms[19])
        # Right stopping point
        if comms[20] >= 0:
            pins["maps"][current_pin_map][pin_name]["action"]["right_pos"] = int(comms[20])
        else:
            pins["maps"][current_pin_map][pin_name]["action"]["right_pos"] = 180 + (180 + comms[20])  
        
        # Timer and timout settings
        # Motor operating between set times
        # If comms[9] == 'timer', execute actions only between comms[10] and comms[11]
        pins["maps"][current_pin_map][pin_name]["action"]["timer"] = comms[9]
        pins["maps"][current_pin_map][pin_name]["action"]["times"] = [comms[10], comms[11]]

        # Motor switch off on timeout
        # It comms[12] != 'Indefinite', switch pin low after comms[13] seconds
        pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] = comms[12]
        pins["maps"][current_pin_map][pin_name]["action"]["timeout"] = comms[13]

        # Add to monitoring array if either timer or timeout set
        if pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][pin_name]["action"]["timer"] == "setTimes":
            event_times_out[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]  

        
    else:
        # All other pin types
        if "switchout" in comms[6]:
            # Input set to switch a previously configured output when triggered. Get output pin number
            pins["maps"][current_pin_map][num_to_name(comms[7])]["partner"] = target_pin
        
        elif comms[6] == "sendEmail":
            # Program will send an email to user any time the input is triggered
            pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = str(comms[7]) # Subject line for email
            
        elif comms[6] == "sendWebRequest":
            # Program will send HTTP request to a website if input pin triggers
            pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = str(comms[7])
            # First key and value to send with request
            pins["maps"][current_pin_map][pin_name]["action"]["httpKey1"] = str(comms[14])
            pins["maps"][current_pin_map][pin_name]["action"]["httpvalue1"] = str(comms[15])

            # Second key and value to send with request
            pins["maps"][current_pin_map][pin_name]["action"]["httpKey2"] = str(comms[16])
            pins["maps"][current_pin_map][pin_name]["action"]["httpvalue2"] = str(comms[17])

        else:
            pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = int(comms[7])
        if pins["maps"][current_pin_map][pin_name]["setting"] == "Analog":
            pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = float(comms[8]) # current reading for analog pins
        else:
            pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = int(comms[8]) # default PWM speed for digital

        # Timer and timout settings
        # If comms[9] == 'timer', execute actions only between comms[10] and comms[11]
        pins["maps"][current_pin_map][pin_name]["action"]["timer"] = comms[9]
        pins["maps"][current_pin_map][pin_name]["action"]["times"] = [comms[10], comms[11]]
        # It comms[12] != 'Indefinite', switch pin low after comms[13] seconds
        print(comms[12])
        print(comms[13])        
        pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] = comms[12]
        pins["maps"][current_pin_map][pin_name]["action"]["timeout"] = comms[13]
        print("wa")
       
        # load inputs into event_times folder so AAIMI knows to monitor their state during each loop
        # Include timing details for their actions, eg timeout if input is triggering an output
        if "Input" in comms[3] or "Analog" in comms[3]:
            event_times[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]
            if "A" in pin_name:
                pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = float(comms[-1]) # Analog trigger point
                # Interval to read analog pin, default is 10 seconds
                pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = [0, 10]
       
        # Add output pin to event_times_out folder if they work on a timer or timeout
        if "Output" in comms[3]:
            # Only add output to event_times_out if pin has timer or timeout enabled
            if pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][pin_name]["action"]["timer"] == "setTimes":
                event_times_out[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]  # [currentTime, timeout, timeout_type]
                
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
                    
        # Configure bi-directional PWM DC motor
        if comms[3] == "PWMOutput" and "gpio" in pin_name:
            
            # Create entries for direction and current speed
            pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = "Forwards"        
            pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0 # Current speed
            
            # Use pwm_count to decide which reserved pwm variables to use for motor pin objects
            pwm_count += 1
            pwm_pairs[comms[4]] = {}

            # Set second motor pin as output and store details
            GPIO.setup(int(comms[7]), GPIO.OUT)        
            pairpin = "gpio_" + str(comms[7])
            pins["maps"][current_pin_map][pairpin]["action"]["type"] = "OutputPartner"
            pins["maps"][current_pin_map][pairpin]["action"]["arg1"] = target_pin
            
            # The two gpio pin numbers for the motor, ie [22, 27]
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

        # Configure single pin PWM device, LED, etc.
        elif comms[3] == "PWMOutputLed" and "gpio" in pin_name:
            
            # Add current and default speed for PWM signal
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


                                        
######### Run 360 deg Stepper Motors #####################

# Move the mast one full step sequence
def mast_motor(mmotor, mdirection, motorpause):
    global stepper_orders, stepper_motor_pins_reverse, stepper_motor_pins
    current_order = 0
    
    # Define order of GPIO signals to use (Currently set for motor shaft facing up)
    if mdirection == "anti_clockwise":
        motor_gpio_pins_dir = stepper_motor_pins[mmotor] 
    elif mdirection == "clockwise":
        motor_gpio_pins_dir = stepper_motor_pins_reverse[mmotor] 
        
    # Work through all combinations in stepper_orders array    
    while current_order < len(stepper_orders):
        
        # Switch each pin to suit the current combination
        for pin in range(0, 4):
            stepper_pin = motor_gpio_pins_dir[pin]
            if stepper_orders[current_order][pin]!=0:
                GPIO.output(stepper_pin, True)
            else:
                GPIO.output(stepper_pin, False)
                
        current_order += 1        
        time.sleep(motorpause)
    
# Calculate the distance and direction and move the motor to a specific location in degrees
def calc_move():
    global next_stepper_move
    print(next_stepper_move)
    motor = next_stepper_move[0]
    target_pos = int(next_stepper_move[1])
    next_stepper_move = []
    stepPinName = "gpio_" + str(stepper_motor_pins[motor][0])
    current_pos = pins["maps"][current_pin_map][stepPinName]["action"]["pos"]
    print(target_pos)

    # Choose whether motor needs to turn clockwise or anti-clockwise to reach target position
    if target_pos < 360 and target_pos != current_pos:
        
        if target_pos < 181:
            if current_pos < 181:
                if current_pos < target_pos:
                    distance = target_pos - current_pos
                    direction = "clockwise"
                elif current_pos > target_pos:
                    distance = current_pos - target_pos
                    direction = "anti_clockwise"
            elif current_pos > 180:
                distance = (360 - current_pos) + target_pos
                direction = "clockwise"
                
        elif target_pos > 180:            
            if current_pos < 181:
                distance = (360 - target_pos) + current_pos
                direction = "anti_clockwise"
            elif current_pos > 180:
                if current_pos < target_pos:
                    distance = target_pos - current_pos
                    direction = "clockwise"
                elif current_pos > target_pos:
                    distance = current_pos - target_pos
                    direction = "anti_clockwise"

        # Get motor to target position one step at a time            
        moves = 0
        motor_pause = pins["maps"][current_pin_map][stepPinName]["action"]["speed"]
        pins["maps"][current_pin_map][stepPinName]["status"] = "High"
        while moves < int(distance * pins["maps"][current_pin_map][stepPinName]["action"]["adjuster"]):
            mast_motor(motor, direction, motor_pause)
            moves += 1
            
        pins["maps"][current_pin_map][stepPinName]["status"] = "Low"
        pins["maps"][current_pin_map][stepPinName]["action"]["pos"] = target_pos

    # Switch all stepper pins low when at target pos
    for p in stepper_motor_pins[motor]:
        GPIO.output(p, False)
        
    write_pin_list() 

# Set the stepper motor to automatically oscillate between set points
def step_oscillate():
    global oscillating, oscillating_on, next_stepper_move
    while oscillating_on == "on":
        for smotor in oscillating:
            
            # If motor is paused at one side, start back in opposite direction
            if oscillating[smotor]["state"] == "pausing" or oscillating[smotor]["state"] == "waiting":
                oscillating[smotor]["state"] = "moving"
                
                if oscillating[smotor]["next"] == "left":
                    side = int(pins["maps"][current_pin_map][oscillating[smotor]["pin"]]["action"]["left_pos"])
                    oscillating[smotor]["next"] = "right"
                else:
                    side = int(pins["maps"][current_pin_map][oscillating[smotor]["pin"]]["action"]["right_pos"])
                    oscillating[smotor]["next"] = "left"

                # Load instructions for calc_move() function
                next_stepper_move = []
                next_stepper_move.append(smotor)
                next_stepper_move.append(side)
                calc_move()

                # Stop at end point and wait two seconds before resuming
                oscillating[smotor]["state"] = "pausing"
                time.sleep(2)
                
    # Switch back to default position when turned off
    next_stepper_move.append(smotor)
    next_stepper_move.append(int(pins["maps"][current_pin_map][oscillating[smotor]["pin"]]["action"]["default_pos"]))
    calc_move()    
    print("SO")
                
#####################

######### Bi-directional PWM motors (Raspberry Pi only)   ###############

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
    pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
    pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])    
    # Use first pin of pair if rotation is forward    
    if direction == "Forwards":
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

    # Update arrays and pin file        
    pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = direction
    pwm_pairs[motor_name]["pwm"][0] = speed
    pwm_pairs[motor_name]["direction"] = direction
    pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = speed
    write_pin_list() 


# Switch a motor off
def stop_motor(motor_name):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4

    # Get GPIO names for both motor pins
    pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
    pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])

    # Switch both pins Low for specified motor
    if pwm_pairs[motor_name]["id"] == 1:  # First motor
        pwm2.stop()
        pwm1.stop()
    elif pwm_pairs[motor_name]["id"] == 3:   # Second motor
        pwm4.stop()
        pwm3.stop()  
    
    # Set current motor speed, and status for both pins and update pin file
    pwm_pairs[motor_name]["pwm"][0] = 0
    pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0
    pins["maps"][current_pin_map][pin_name]["status"] = "Low"
    pins["maps"][current_pin_map][pair_name]["status"] = "Low"
    write_pin_list()


# Change the PWM duty cycle for a motor that is already running
def set_motor_speed(motor_name, direction, speed):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4
    pin_name = pwm_pairs[motor_name]["pin_pair"][0]

    # If not changing direction, just adjust speed
    if direction == pwm_pairs[motor_name]["direction"]:
        pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])

        # Determine which pin is currently driving the motor based-on direction
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

        # Update arrays
        pwm_pairs[motor_name]["pwm"][0] = speed
        pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = speed

    # If changing direction, restart motor in new direction at default speed    
    else:
        start_motor(motor_name, direction)
        
    # Schedule file-write on next loop to reflect changes
    write_due = "yes"

##############

    
####### General PWM outputs for Leds #######################

# Start a PWM Led on or off at its default brightness
def start_stop_pwm_led(pwm_id_num, pwm_action):
    global pwm_general_pins, led2, led1, pins, current_pin_map, write_due
    pin_name = "gpio_" + str(pwm_id_num)
    
    # Switch off
    if pwm_action == 0:
        # Select pin to switch off based-on numeric ID
        if pwm_general_pins[pwm_id_num]["id"] == 1:
            led1.stop()
        elif pwm_general_pins[pwm_id_num]["id"] == 2:
            led2.stop()

        # Update arrays
        pins["maps"][current_pin_map][pin_name]["status"] = "Low"
        pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = 0
        pwm_general_pins[pwm_id_num]["speeds"][0] = 0
        
    # Start PWM at default speed
    elif pwm_action == 1:        
        # Select pin to switch off based-on numeric ID
        if pwm_general_pins[pwm_id_num]["id"] == 1:
            led1.start(pwm_general_pins[pwm_id_num]["speeds"][1])
        elif pwm_general_pins[pwm_id_num]["id"] == 2:
            led2.start(pwm_general_pins[pwm_id_num]["speeds"][1])

        # Update arrays    
        pins["maps"][current_pin_map][pin_name]["status"] = "High"
        pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = pins["maps"][current_pin_map][pin_name]["action"]["arg2"]
        pwm_general_pins[pwm_id_num]["speeds"][0] = pwm_general_pins[pwm_id_num]["speeds"][1]
    write_due = "yes"


# Set the PWM duty cycle for a LED or other single pin device
def set_led_brightness(pwm_id_num, speed):
    global pwm_general_pins, led1, led2, pins, current_pin_map, write_due
    pin_name = "gpio_" + str(pwm_id_num)

    # Select pin to switch off based-on numeric ID
    if pwm_general_pins[pwm_id_num]["id"] == 1:
        led1.ChangeDutyCycle(speed)
    elif pwm_general_pins[pwm_id_num]["id"] == 2:
        led2.ChangeDutyCycle(speed)
        
    pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = speed
    write_due = "yes"


############

################  Pin map management  ####################

# Reset all GPIO pins and set the current pin configuration map to default.
# Change full to 'new' to delete all saved maps as well
def reset_program(full="existing"):
    global event_times, event_times_out, pwm_count, led_count, running
    
    # Stop main loop functions so other threads won't interrupt
    running = "no"
    
    # Reset GPIO and clear event arrays
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    print("RP")

    # Empty the event arrays
    event_times = {}
    event_times_out = {}
    pwm_count = 0
    led_count = 0    

    # Create the new list
    create_new_pinfile(scope=full)

    # Reload the pin configuration
    load_pin_list()

    # Start main loop functions again
    running = "yes"
    

# Save the current pinmap to a new map you can use later
def save_map(newmapname, reset_session_map="no"):
    global pins, current_pin_map
    
    # Copy existing map to save name
    pins["maps"][newmapname] = pins["maps"][current_pin_map]
    print("Copied")

    # Choose whether to restet the current pin map to default
    if reset_session_map == "yes":
        # Save the map to new name and reset the session pin map back to factory settings

        # Stop main loop functions so other threads won't interrupt
        running = "no"

        # Reset map, pins and event arrays
        create_new_pinfile(scope="existing", mapname=current_pin_map)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        event_times = {}
        event_times_out = {}

        # Start main loop functions again
        running = "yes"
        
    else:
        # Just save the map to another name without resetting current map
        print("Writing")
        write_pin_list()
        

# Changed to a previously-saved map 
def change_map(newmap):
    global event_times, event_times_out, current_pin_map, pins
    if newmap in pins["maps"]:

        # Stop main loop functions so other threads won't interrupt
        running = "no"

        # Update pin file
        current_pin_map = newmap
        pins["current_map"] = newmap
        write_pin_list()

        # Reset pins and event arrays
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        print(current_pin_map)
        event_times = {}
        event_times_out = {}

        # Reload pin list and start main loop functions again
        load_pin_list()
        running = "yes"        
    else:
        print("No such map")

############

########## Timers and timeout  #################
        
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
            
            # If start time, set input actions for pin as active so an event will trigger reaction
            if time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][0]:
                if timer_name not in active_hours:
                    active_hours.append(timer_name)
                    write_due == "yes"
                    
            # If end time set input actions for pin as dormat so an event will not trigger reaction    
            elif time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][1]:
                if timer_name in active_hours:
                    active_hours.pop(timer_name)
                    write_due == "yes"

                # If input set to switch output, switch off output pin
                if pins["maps"][current_pin_map][timer_name]["action"]["type"] == "swtchOut":
                    
                    # Switch off partner output depending on board type
                    # Raspi
                    if pins["maps"][current_pin_map][timer_name]["action"]["arg1"] <= 27: 
                        GPIO.output(int(pins["maps"][current_pin_map][timer_name]["action"]["arg1"]), False)
                        pairpin = "gpio_" + str(pins["maps"][current_pin_map][timer_name]["action"]["arg1"])

                    # Arduino
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

###############

######################  ROUTE USER COMMANDS ###############
            
# Accept space-separate commands from browser and route to relevant functions
def react(order):
    global pins, current_pin_map, event_times_out, running, pwm_pairs, event_times, pwm_count, pwm_general_pins
    global oscillating_on, oscillating, led_count, system_pass, next_stepper_move, pass_entered, website_pass_entered, website_pass
    print(order)
    
    # Split order in a list of commands, first command is action type, others are parameters
    commands = order.split(" ")


    # Set PWM motor speed: motor, direction, speed
    # Example order: 'speedMotor myMotor Forwards 50'
    if commands[0] == "speedMotor":
        set_motor_speed(commands[1], commands[2], int(commands[3]))


    # Set PWM LED speed: LED, speed
    # Example order: 'speedPWM myLED 50'
    elif commands[0] == "speedPWM":
        set_led_brightness(int(commands[1]), int(commands[2]))


    # Switch a PWM motor on at its default speed
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

        # Determine whether to switch on or off
        if int(commands[2]) == 1:          
            pins["maps"][current_pin_map][pinName]["status"] = "High"
        else:
            pins["maps"][current_pin_map][pinName]["status"] = "Low"
        write_pin_list()


    # Switch a standard output on or off
    # Example: 'switch 1 4' will switch gpio_4 on       
    elif commands[0] == "switch":

        # Determine board type and switch pin
        if int(commands[2]) <= 27:
            # Will be Pi GPIO
            pinName = "gpio_" + commands[2]
            print(commands[1])

            # Switch pin High
            if commands[1] == "1":
                print("switching high")
                GPIO.output(int(commands[2]), True)
                pins["maps"][current_pin_map][pinName]["status"] = "High"
                if int(commands[2]) in event_times_out:
                    event_times_out[int(commands[2])][0] = int(time.time())
                    
                # Log time if output is operated by an input pin on timeout
                if "partner" in pins["maps"][current_pin_map][pinName]:
                    if pins["maps"][current_pin_map][pinName]["partner"] in event_times:
                        event_times[pins["maps"][current_pin_map][pinName]["partner"]][0] = time.time()

            # Switch pin Low            
            else:
                print("Low")
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
                    
                    # Log time if output is operated by an input pin on timeout
                    if "partner" in pins["maps"][current_pin_map][pinName]:
                        if pins["maps"][current_pin_map][pinName]["partner"] in event_times:
                            event_times[pins["maps"][current_pin_map][pinName]["partner"]][0] = time.time()                    
                    
                else:
                    # Send Off character to Arduino to switch pin Low
                    ard_command = pin_commands[pinName][1]
                    switch(ard_command)
                    pins["maps"][current_pin_map][pinName]["status"] = "Low"                
        write_pin_list()


    # Rotate a stepper motor to a specified position
    # Example: 'stepperPos myMotor 90' will turn myMotor to 90 degrees
    elif commands[0] == "stepperPos":        
        # Convert reading to 0-360 deg scale from -180to180 deg scale, eg: -90 will become 270, 90 will become 90
        if commands[2] >= 0:
            new_pos = commands[2]
        else:
            new_pos = 180 + (180 + commands[2])
            
        # Load motor name and target position into next move list to use in new thread next loop
        next_stepper_move.append(commands[1])
        next_stepper_move.append(new_pos) 

    
    # Configure settings for new pin    
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

            # Rest pins and clear arrays and variables
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
    # Example: 'reset'
    elif commands[0] == "reset":
        reset_program()


    # Save the current pin configuration as a new map
    # Example: 'save myNewMap'
    elif commands[0] == "save":
        save_map(commands[1])


    # Change to a previously-saved pin map
    # Example: 'choose_map myNewMap'
    elif commands[0] == "choose_map":
        change_map(commands[1])


    # Example: 'emailPass myPass'
    # Set password for system email
    elif commands[0] == "emailPass":
        aaimi_email_out.system_pass = str(commands[1])
        pass_entered = "yes"



    # Set password for system email
    # Example: 'websitePass myPass'    
    elif commands[0] == "websitePass":
        website_pass = str(commands[1])
        website_pass_entered = "yes"


    # Set stepper motor to oscillate between left and right points
    # Example: 'oscillate myMotor gpio_18'
    elif commands[0] == "oscillate":
        motor_name = str(commands[1])
        if motor_name not in oscillating:
            oscillating[motor_name] = {}
            oscillating[motor_name]["state"] = "waiting"
            oscillating[motor_name]["next"] = "left"
            oscillating[motor_name]["pin"] = commands[2]
        if oscillating_on == "off":
            oscillating_on = "waiting"
        else:
            oscillating_on = "stopping"
        print(oscillating_on)
        write_pin_list()


    # Reset zero position of stepper motor
    # Example: 'stepper_zero myMotor gpio_18'
    elif commands[0] == "stepper_zero":
        pins["maps"][current_pin_map][commands[2]]["action"]["pos"] = 0
        write_pin_list()

############################ SOCKET ################
            
# Listen for incomming requests from web GUI and send to react() for routing to functions
def socket_watch():
    con_stat = ""
    dstore = ""
    while True:
        try:
            # Configure socket connection
            HOST = '127.0.0.5' 
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

#######################

check_timers()

############ MAIN MONITORING LOOP ######################
# Start main loop to monitor pins
while True:
    try:
        # If running == "no", don't monitor pins
        if running == "yes":
            # Flag to update details file if there are changes
            changed = "no"

            # If there is a stepper motor ready to move to a position
            if len(next_stepper_move) != 0:
                changed = "yes"
                # Start stepper motor operation in its own thread
                try:
                    step_sock_thread = threading.Thread(target = calc_move)
                    step_sock_thread.start()
                except:
                    GPIO.cleanup()
                    print('\n! Keyboard interrupt, quitting threads2.\n')
                    os._exit(1)

            # If there is an oscillating stepper motor at one side of its cycle, move to other side
            if oscillating_on == "waiting":
                print("StartMotor")
                changed = "yes"
                oscillating_on = "on"
                # Start stepper motor operation in its own thread
                try:
                    osc_sock_thread = threading.Thread(target = step_oscillate)
                    osc_sock_thread.start()
                except:
                    GPIO.cleanup()
                    print('\n! Keyboard interrupt, quitting threads2.\n')
                    os._exit(1)

            # If an oscillating stepper motor is waiting to be switched of, set flag
            elif oscillating_on == "stopping":
                oscillating_on = "off"

            # Partner pin for DC motor, or output pin controlled by input
            pairpin = ""
            
            # String to identify primary pin name
            event_pin_name = ""

            # Check state of any declared inputs.
            if len(event_times) > 0: 
                for et in event_times:
                    pin_status = "default" # Flag as default state until proven otherwise

                    # Determine if pin is in react state based on device type, pin type and default state                    
                    # If Raspi
                    if et <= 27:
                        event_pin_name = "gpio_" + str(et)
                        # If pin is High set to react when pin goes High, declare input event
                        if GPIO.input(int(et)) == True and pins["maps"][current_pin_map][event_pin_name]["default"] == "Low":
                            pin_status = "inEventHigh"
                        # If Low and set to react when pin goes Low, declare input event    
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

                            # Log new reading if voltage has changed by more than 10mV
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

                    # If not in default state, react accordingl  
                    if "inEvent" in pin_status:    
                        # Log time of event and update pin status if changed
                        event_times[et][0] = time.time()
                        # Get new pin Low/High status
                        status_filler = pin_status.replace("inEvent", "")

                        # If this is not an existing event from last loop, perform event actions for pin
                        if pins["maps"][current_pin_map][event_pin_name]["status"] != status_filler:
                            pins["maps"][current_pin_map][event_pin_name]["status"] = status_filler
                            
                            # Switch an output on if pin is configured as switchout.
                            if pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "switchOut":
                                pairnum = pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]
                                
                                # If pin's action is on a timer, check if within start and finish times                                  
                                if pins["maps"][current_pin_map][event_pin_name]["action"]["timer"] == "setTimes":

                                    # Switch partner output on if within active hours
                                    if event_pin_name in active_hours:
                                        if int(pairnum) <= 27:  # Raspi
                                            pairpin = "gpio_" + str(pairnum)
                                            GPIO.output(int(pairnum), True)
                                        elif int(pairnum) >= 100 and int(pairnum) <= 113:  # Arduino
                                            pairpin = "D" + str(int(pairnum) - 100)
                                            ard_command = pin_commands[pairpin][0]
                                            switch(ard_command)
                                        pins["maps"][current_pin_map][pairpin]["status"] = "High"

                                # If action set to go at any time, switch partner pin                                       
                                else:                                  
                                    if int(pairnum) <= 27:  # Raspi
                                        pairpin = "gpio_" + str(pairnum)
                                        GPIO.output(int(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]), True)
                                                                            
                                    elif int(pairnum) >= 100 and int(pairnum) <= 113: # Arduino digital pin
                                        pairpin = "D" + str(int(pairnum) - 100)
                                        print(pairpin)
                                        ard_command = pin_commands[pairpin][0]
                                        switch(ard_command)                                                                                
                                    pins["maps"][current_pin_map][pairpin]["status"] = "High"

                                # Log switching time if pair pin is also has timeout set. Pin will switch back according to lowest timeout    
                                if pins["maps"][current_pin_map][pairpin]["status"] == "High":
                                    if int(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]) in event_times_out:
                                        event_times_out[pairnum][0] = int(time.time())                                    
                                    
                            # Increment the event count if pin is set as 'countRecord'.
                            elif pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "countRecord":
                                pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"] += 1
                                print("Count: " + str(pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]))

                            # If input set to trigger email, check if password has been entered
                            elif pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "sendEmail" and pass_entered == "yes":
                                subject = pins["maps"][current_pin_map][event_pin_name]["action"]["arg1"]
                                subject_pin_state = pins["maps"][current_pin_map][event_pin_name]["status"]                                
                                aaimi_email_out.send_email_report(subject, event_pin_name, subject_pin_state, arg3=str(time.strftime('%H:%M:%S')))

                            # If input set to trigger HTTP request, send request  
                            elif pins["maps"][current_pin_map][event_pin_name]["action"]["type"] == "sendWebRequest":
                                send_web_request(event_pin_name)
                                print("Sent")
                                
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


            # Check any outputs set as timeout and switch LOW if time has elapsed since they were switched HIGH
            if len(event_times_out) > 0:
                for et in event_times_out:
                    # If Raspberry Pi pin
                    if et <= 27:  
                        if GPIO.input(int(et)) and event_times_out[et][2] == "timeout":
                            gone = int(time.time()) - int(event_times_out[et][0])
                            if gone > int(event_times_out[et][1]):
                                print(gone, int(time.time()), int(event_times_out[et][0]))
                                event_pin_name = "gpio_" + str(et)
                                GPIO.output(int(et), False)
                                pins["maps"][current_pin_map][event_pin_name]["status"] = "Low"
                                changed = "yes"

                    # If Arduino digital pin            
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


            # Write full pinlist to file for browser access if any pins have changed                               
            if changed == "yes" or write_due == "yes":
                write_pin_list()
                write_due = "no"
                
            time.sleep(1)
            
        else:
            # Loop is off, do nothing
            time.sleep(1)

        # Time functions    
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

