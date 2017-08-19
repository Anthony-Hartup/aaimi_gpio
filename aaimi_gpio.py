#!/bin/bash

# AAIMI GPIO
# Configure and use Raspberry Pi GPIO pins from a web interface 


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

import json, socket, sys, os, threading, time
import RPi.GPIO as GPIO

# Socket to listen for input from browser-based GUI
socketport = 50001

# Program can save and load multiple pin configurations. session is default
current_pin_map = "session"

# JSON to hold all pin maps
pins = {}
pinlist = "pi_details.txt"
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
    global pins
    if scope == "new":
        pins = {}
        pins["maps"] = {}
        pins["maps"]["session"] = {}
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
        pins["maps"][mapname][keystring]["action"]["arg1"] = 0
        pins["maps"][mapname][keystring]["action"]["arg2"] = 0
        pins["maps"][mapname][keystring]["action"]["timer"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["timeout"] = 0
        pins["maps"][mapname][keystring]["action"]["timeout_type"] = "Pending"
        pins["maps"][mapname][keystring]["action"]["times"] = ["00:00", "00:00"]      
        pincount += 1
    write_pin_list()
    
# Load the list of GPIO configurations from file and define the inputs and outputs from the default pin map
# This is triggered from GUI
def load_pin_list():
    global pins, current_pin_map, pwm_pairs, event_times, pwm_count, pwm_general_pins, led_count, led1, led2
    global pwm1, pwm2, pwm3, pwm4
    with open(pinlist) as source_file:
        all_pin_maps = json.load(source_file)
        pins = all_pin_maps[0]
        
    for p in pins["maps"][current_pin_map]:
        # Only get details from pins that have been defined
        if pins["maps"][current_pin_map][p]["setting"] != "Unset":
            target_pin = int(p.replace("gpio_", ""))
            msg = p + " has been set to " + pins["maps"][current_pin_map][p]["setting"]
            # If pin is any type of output (Output, PWMOutput or PWMOutputLED)
            if "Output" in pins["maps"][current_pin_map][p]["setting"]:
                # Define pin as output and switch High or Low depending on default setting
                GPIO.setup(target_pin, GPIO.OUT)
                if pins["maps"][current_pin_map][p]["default"] == "Low" and pins["maps"][current_pin_map][p]["setting"] != "PWMOutput":
                    GPIO.output(target_pin, False)
                    pins["maps"][current_pin_map][p]["status"] = "Low"
                elif pins["maps"][current_pin_map][p]["default"] == "High" and pins["maps"][current_pin_map][p]["setting"] != "PWMOutput":
                    GPIO.output(target_pin, True)
                    pins["maps"][current_pin_map][p]["status"] = "High"
                if pins["maps"][current_pin_map][p]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][p]["action"]["timer"] == "setTimes":
                    # Add to events folder for loop to monitor if timer or timeout set
                    event_times_out[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]

                # If pin is a bi-directional motor
                # 
                if pins["maps"][current_pin_map][p]["setting"] == "PWMOutput":
                    pwm_count += 1
                    this_motor = pins["maps"][current_pin_map][p]["nickname"]
                    pwm_pairs[this_motor] = {}
                    # The two gpio pin names for the motor, ie ['gpio_22', 'gpio_27']
                    pwm_pairs[this_motor]["pin_pair"] = [target_pin, int(pins["maps"][current_pin_map][p]["action"]["arg1"])]
                    # Set second motor pin as output
                    GPIO.setup(int(pwm_pairs[this_motor]["pin_pair"][1]), GPIO.OUT)
                    print("GPIO " + str(pwm_pairs[this_motor]["pin_pair"][1]) + "has been set")
                    # The identifier (int) for both pins to use for GPIO commands, ie [22, 27]
                    pwm_pairs[this_motor]["id"] = pwm_count
                    # Default state for motor when program starts: on or off
                    pwm_pairs[this_motor]["default"] = pins["maps"][current_pin_map][p]["default"]
                    # Current speed and default starting speed
                    pwm_pairs[this_motor]["pwm"] = [0, int(pins["maps"][current_pin_map][p]["action"]["arg2"])]
                    pwm_pairs[this_motor]["direction"] = "Forwards"
                    pins["maps"][current_pin_map][p]["action"]["arg3"] = "Forwards"        
                    pins["maps"][current_pin_map][p]["action"]["arg4"] = 0                  
                    # Set objects for pins
                    if pwm_count == 1:
                        # Use first reserved motor pin variables
                        pwm1 = GPIO.PWM(target_pin, 50)
                        pwm_count = 2                              
                        pwm2 = GPIO.PWM(int(pins["maps"][current_pin_map][p]["action"]["arg1"]), 50)
                    elif pwm_count == 3:
                        # Use second reserved reserved motor pin variables
                        pwm3 = GPIO.PWM(target_pin, 50)
                        pwm_count = 4                             
                        pwm4 = GPIO.PWM(int(pins["maps"][current_pin_map][p]["action"]["arg1"]), 50)
                    else:
                        print("You can only have two motors")
                        
                # If pin is a LED or other single pin PWM device
                elif pins["maps"][current_pin_map][p]["setting"] == "PWMOutputLed":
                    # Add name and current and default speed for PWM signal
                    pwm_general_pins[target_pin] = {}
                    pwm_general_pins[target_pin]["speeds"] = [0, int(pins["maps"][current_pin_map][p]["action"]["arg2"])]
                    print(pwm_general_pins)
                    led_count += 1
                    # Create an ID form led_count to determine which reserved PWM object to use
                    pwm_general_pins[target_pin]["id"] = led_count
                    if led_count == 1:
                         led1 = GPIO.PWM(target_pin, 50)
                    elif led_count == 2:
                        led2 = GPIO.PWM(target_pin, 50)
                    else:
                        print("You can only use two dimmable LEDs in this version")
                    print(pwm_general_pins)

            # If pin is any type of input (Input, InputPullUp, InputPullDown)       
            elif "Input" in pins["maps"][current_pin_map][p]["setting"]:
                # Add input to events folder for loop to monitor
                event_times[target_pin] = [time.time(), pins["maps"][current_pin_map][p]["action"]["timeout"], pins["maps"][current_pin_map][p]["action"]["timeout_type"]]
                if "PullDown" in pins["maps"][current_pin_map][p]["setting"]:
                    GPIO.setup(target_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                elif "PullUp" in pins["maps"][current_pin_map][p]["setting"]:
                    GPIO.setup(target_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                else:
                    GPIO.setup(target_pin, GPIO.IN)
            print(msg)


# Save the default pinmap to a new map you can use later
def save_map(newmapname, reset_session_map="no"):
    global pins
    pins["maps"][newmapname] = pins["maps"][current_pin_map]
    if reset_session_map == "yes":
        # Change the current pin map back to factory settings
        create_new_pinfile(scope="existing", mapname=current_pin_map)
        GPIO.cleanup()
    else:
        write_pin_list()
        current_pin_map = newmapname
    

# Configure settings for a single pin based on incoming details from browser
# Change scope to test to run without setting GPIO pins
def configure_pin(orders, scope="full"):
    global pins, pwm_count, pwm_pairs, current_pin_map, event_times, led_count, pwm_general_pins
    global pwm1, pwm2, pwm3, pwm4 , led1, led2 # Reserved undeclared variables for two 2-pin PWM DC motors and 2 single-pin LEDs
    #   This allows the PWM objects created in this fucntion to be global

    # The example below would configure GPIO 17 as an input and set it to switch GPIO 4 on when HIGH and switch it off after
    #   input has returned to and stayed LOW for thirty seconds    
    # Input orders: 'config session gpio_17 Input myInputPin Low switchOut 4 filler 00:00 00:00 timeout 30'
    # Output orders: 'config session gpio_4 PWMOutputLed MyLed Low outManual 0 filler 00:00 00:00 noTimeOut 0'
    
    # Split space-separated details (orders) sent from browser
    comms = orders.split(" ")
    current_pin_map = comms[1]

    # Create new map if it doesn't exist
    if current_pin_map not in pins["maps"]:
        create_new_pinfile(scope="existing", mapname=current_pin_map)
        
    # Get target_pin number from name string to use for GPIO operations, eg: "gpio_8" becomes 8
    pin_name = comms[2]
    target_pin = int(pin_name.replace("gpio_", ""))

    # Load basic details to the specified pin map
    pins["maps"][current_pin_map][pin_name]["setting"] = comms[3] # Output/PWMOutput Input/InputPullup/InputPullDown
    pins["maps"][current_pin_map][pin_name]["nickname"] = comms[4] # Name to display on GPIO buttons
    pins["maps"][current_pin_map][pin_name]["default"] = comms[5] # Default state, Low/High
    pins["maps"][current_pin_map][pin_name]["status"] = comms[5] # Current state (live)
    
    # The type of action for the pin
    pins["maps"][current_pin_map][pin_name]["action"]["type"] = comms[6]
    # Action details
    pins["maps"][current_pin_map][pin_name]["action"]["arg1"] = int(comms[7])
    pins["maps"][current_pin_map][pin_name]["action"]["arg2"] = int(comms[8])

    # Timer and timout settings
    # I comms[9] == 'timer', execute actions only between comms[10] and comms[11]
    pins["maps"][current_pin_map][pin_name]["action"]["timer"] = comms[9]
    pins["maps"][current_pin_map][pin_name]["action"]["times"] = [comms[10], comms[11]]
    # It comms[12] != 'Indefinite', switch pin low after comms[13] seconds
    pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] = comms[12]
    pins["maps"][current_pin_map][pin_name]["action"]["timeout"] = comms[13]
    
    # load inputs into event_times folder so AAIMI knows to monitor their state during each loop
    # Include timing details for their actions, eg timeout if input is triggering an out put
    if "Input" in comms[3]:
        event_times[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]
    # Add output pin to event_times_out folder if the work on a timer or timeout
    if "Output" in comms[3]:
        # Only add output to event_times_out if pin has timer or timeout enabled
        if pins["maps"][current_pin_map][pin_name]["action"]["timeout_type"] == "timeout" or pins["maps"][current_pin_map][pin_name]["action"]["timer"] == "setTimes":
            event_times_out[int(target_pin)] = [time.time(), int(comms[13]), comms[12]]    
    print(pins["maps"][current_pin_map][pin_name])
    
    # Set GPIO pins if scope not 'tests'
    if scope != "test":
        if "Output" in comms[3]:
            GPIO.setup(int(target_pin), GPIO.OUT)
            # Switch pin to default state if not set as PWM pin
            if comms[5] == "On" and comms[3] != "PWMOutput":
                GPIO.output(int(target_pin), True)
            elif comms[5] == "Off" and comms[3] != "PWMOutput":
                GPIO.output(int(target_pin), False)
        elif "Input" in comms[3]:
            if "PullDown" in comms[3]:
                GPIO.setup(int(target_pin), GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            elif "PullUp" in comms[3]:
                GPIO.setup(int(target_pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(int(target_pin), GPIO.IN)
                
    
    if comms[3] == "PWMOutput":
        # Will be bi-directional DC motor
        
        # Create entries for direction and current speed
        pins["maps"][current_pin_map][pin_name]["action"]["arg3"] = "Forwards"        
        pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0
        
        # Use pwm_count to decide which reserved pwm variables to use for motor pins
        pwm_count += 1
        pwm_pairs[comms[4]] = {}

        # Set second motor pin as output and store details
        GPIO.setup(int(comms[7]), GPIO.OUT)        
        pairpin = "gpio_" + str(comms[7])
        pins["maps"][current_pin_map][pairpin]["action"]["type"] = "OutputPartner"
        pins["maps"][current_pin_map][pairpin]["action"]["arg1"] = target_pin
        
        # The two gpio pin names for the motor, ie ['gpio_22', 'gpio_27']
        pwm_pairs[comms[4]]["pin_pair"] = [target_pin, comms[7]]
        # The identifier to determine which reserved PWM objects to use
        pwm_pairs[comms[4]]["id"] = pwm_count
        # Default state for motor when program starts: on or off
        pwm_pairs[comms[4]]["default"] = comms[5]
        # Current speed and default starting speed
        pwm_pairs[comms[4]]["pwm"] = [0, int(comms[8])]
        pwm_pairs[comms[4]]["direction"] = "Forwards"
        
        # Set objects for pins         
        if pwm_count == 1:
            # User first pair of reserved motor pin variables
            pwm1 = GPIO.PWM(target_pin, 50)
            pwm_count = 2                              
            pwm2 = GPIO.PWM(int(comms[7]), 50)
        elif pwm_count == 3:
            # Use second pair of reserved motor pin variables
            pwm3 = GPIO.PWM(target_pin, 50)
            pwm_count = 4                             
            pwm4 = GPIO.PWM(int(comms[7]), 50)


    elif comms[3] == "PWMOutputLed":
        # Will be single pin PWM device, LED, etc.
        # Add name and current and default speed for PWM signal
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
    write_pin_list()                                       
                                        

######### Bi-directional PWM motors

# Start a PWM Motor or change direction of a running motor
def start_motor(motor_name, direction):
    global pwm_pairs, pins, write_due, pwm1, pwm2, pwm3, pwm4
    # Set wait time for motor to stop spinning if changing rotation direction
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
        if pwm_pairs[motor_name]["id"] == 1:
            pwm2.stop()
            time.sleep(time_to_wait)
            pwm1.start(speed)
        elif pwm_pairs[motor_name]["id"] == 3:
            pwm4.stop()
            time.sleep(time_to_wait)
            pwm13.start(speed) 
        pins["maps"][current_pin_map][pin_name]["status"] = "High"
        pins["maps"][current_pin_map][pair_name]["status"] = "Low"
        
    # Use second pin of pair if rotation is backwards      
    elif direction == "Backwards":
        pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
        pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])  
        if pwm_pairs[motor_name]["id"] == 1:
            pwm1.stop()
            time.sleep(time_to_wait)
            pwm2.start(speed)
        elif pwm_pairs[motor_name]["id"] == 3:
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


def stop_motor(motor_name):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4
    pin_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][0])
    pair_name = "gpio_" + str(pwm_pairs[motor_name]["pin_pair"][1])
    if pwm_pairs[motor_name]["id"] == 1:
        pwm2.stop()
        pwm1.stop()
    elif pwm_pairs[motor_name]["id"] == 3:
        pwm4.stop()
        pwm3.stop()  
    pwm_pairs[motor_name]["pwm"][0] = 0
    pins["maps"][current_pin_map][pin_name]["action"]["arg4"] = 0
    pins["maps"][current_pin_map][pin_name]["status"] = "Low"
    pins["maps"][current_pin_map][pair_name]["status"] = "Low"
    write_pin_list()


# Set the PWM duty cycle for a motor that is already running
def set_motor_speed(motor_name, direction, speed):
    global pwm_pairs, pins, pwm1, pwm2, pwm3, pwm4
    pin_name = pwm_pairs[motor_name]["pin_pair"][0]
    if direction == pwm_pairs[motor_name]["direction"]:
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
        # If changing direction stop and restart motor
        start_motor(motor_name, direction)
    # Schedule file-write on next loop
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
    

# Save the current pin configuration
def save_pin_map(mapname):
    pins["maps"][mapname] = pins["maps"][current_pin_map]

# Reset all GPIO pins and set the pin configuration map to default.
def reset_program():
    GPIO.cleanup()
    create_new_pinfile()
    load_pin_list()

# Check timers and timeouts if new hour or minute
def check_timers():
    global minute_store, hour_store, second_clock, event_times_out
    now = time.strftime("%H:%M:%S")
    now_times = now.split(":")
    time_to_check = now[:5]
    if minute_store != now_times[1]:
        minute_store = now_times[1]
    if hour_store != now_times[0]:
        hour_store = now_times[0]
        
    # Check inputs running on timers
    for timers in event_times:
        if event_times[timers][2] == "setTimes":
            timer_name = "gpio_" + str(timers)
            if time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][0]:
                active_hours.append(timer_name)
            elif time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][1]:
                active_hours.pop(timer_name)
            print(active_hours)
            
    # Check ouputs running on timers
    for timers in event_times_out:
        timer_name = "gpio_" + str(timers)
        if pins["maps"][current_pin_map][timer_name]["action"]["type"] == "outTimer":
            if time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][0]:
                active_hours.append(timer_name)
                GPIO.output(int(timers), True)
                event_times_out[timers][0] = int(time.time())
                pins["maps"][current_pin_map][timer_name]["status"] = "High"
            elif time_to_check == pins["maps"][current_pin_map][timer_name]["action"]["times"][1]:
                active_hours.pop(active_hours.index(timer_name))
                GPIO.output(int(timers), False)
                pins["maps"][current_pin_map][timer_name]["status"] = "Low"
    # Sync loop count to correct second so loop ends on start of new minute next time
    second_clock[0] = int(now_times[2])
            
# Accept commands from browser and route to relevant functions
def react(order):
    global pins, current_pin_map, event_times_out, running, pwm_pairs, event_times, pwm_count, pwm_general_pins, led_count
    print(order)
    # order is space-separated strings
    commands = order.split(" ")

    # PWM speed: motor, direction, speed
    # Example: 'speedPWM myMotor Forwards 50'
    if commands[0] == "speedMotor":
        set_motor_speed(commands[1], commands[2], int(commands[3]))

    if commands[0] == "speedPWM":
        set_led_brightness(int(commands[1]), int(commands[2]))

    # Switch a PWM motor on
    # Example: 'switchMotor myMotor Forwards'
    elif commands[0] == "switchMotor":
        
        pinName = "gpio_" + commands[2]
        if commands[2] == "1":
            start_motor(commands[1], commands[3])            
        else:
            stop_motor(commands[1]) 

    # Switch a PWM LED on or off
    # Example: 'switchPWM 4 1'
    elif commands[0] == "switchPWM":
        pinName = "gpio_" + str(commands[1])
        start_stop_pwm_led(int(commands[1]), int(commands[2])) 
        if int(commands[2]) == 1:          
            pins["maps"][current_pin_map][pinName]["status"] = "High"
        else:
            pins["maps"][current_pin_map][pinName]["status"] = "Low"
        write_pin_list()

    # Switch an output on or off
    # Example: 'switch 4 1'        
    elif commands[0] == "switch":
        pinName = "gpio_" + commands[2]
        if commands[1] == "1":
            GPIO.output(int(commands[2]), True)
            pins["maps"][current_pin_map][pinName]["status"] = "High"
            if int(commands[2]) in event_times_out:
                event_times_out[int(commands[2])][0] = int(time.time())
        else:
            GPIO.output(int(commands[2]), False)
            pins["maps"][current_pin_map][pinName]["status"] = "Low"
        write_pin_list()

    # Change settings for given pin    
    elif commands[0] == "config":
        configure_pin(order)
        
    # Start and stop loop actions
    # Example: 'startLoop 1'     
    elif commands[0] == "startLoop":
        if commands[1] == "on":
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
        GPIO.cleanup()
        os.system("shutdown now")
        

    # Reset all GPIO pins and set the pin configuration map to default.    
    elif commands[0] == "reset":
        reset_program()

    # Save the current pin configuration as a new map    
    elif commands[0] == "save":
        save_map(commands[1])

# Listen for incomming requests from web GUI, email and remote systems
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
            print("SWSL failed")

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
            changed = "no"
            if len(event_times) > 0:
                # Check state of any declared inputs. If set as timeout, switch off if time has elapsed
                for et in event_times:
                    etname = "gpio_" + str(et)
                    if GPIO.input(int(et)) == True:
                        # Log time of event and update pin status if changed
                        event_times[et][0] = time.time()
                        if pins["maps"][current_pin_map][etname]["status"] == "Low":
                            pins["maps"][current_pin_map][etname]["status"] = "High"
                            # Switch an output on if pin is configured as switchout.
                            if pins["maps"][current_pin_map][etname]["action"]["type"] == "switchOut":
                                # If action is on a timer, check if within start and finish times
                                if pins["maps"][current_pin_map][etname]["action"]["timer"] == "setTimes":
                                    if etname in active_hours:
                                        # Switch partner output on
                                        pairpin = "gpio_" + str(pins["maps"][current_pin_map][etname]["action"]["arg1"])
                                        GPIO.output(int(pins["maps"][current_pin_map][etname]["action"]["arg1"]), True)
                                        pins["maps"][current_pin_map][pairpin]["status"] = "High"
                                else:
                                    pairpin = "gpio_" + str(pins["maps"][current_pin_map][etname]["action"]["arg1"])
                                    GPIO.output(int(pins["maps"][current_pin_map][etname]["action"]["arg1"]), True)
                                    pins["maps"][current_pin_map][pairpin]["status"] = "High"
                            # Increment the event count if pin is set as 'countRecord'.
                            elif pins["maps"][current_pin_map][etname]["action"]["type"] == "countRecord":
                                pins["maps"][current_pin_map][etname]["action"]["arg1"] += 1
                                print("Count: " + str(pins["maps"][current_pin_map][etname]["action"]["arg1"]))
                            # Note change to trigger file-write at end of loop
                            changed = "yes"
                                
                    else:
                        # update pin status to Low if changed
                        if pins["maps"][current_pin_map][etname]["status"] == "High":
                            pins["maps"][current_pin_map][etname]["status"] = "Low"
                            changed = "yes"
                        # If pin has partner output and timeout is set, check time elapsed since pin was last high
                        if pins["maps"][current_pin_map][etname]["action"]["type"] == "switchOut":
                            pairpin = "gpio_" + str(pins["maps"][current_pin_map][etname]["action"]["arg1"])
                            gone = int(time.time()) - int(event_times[et][0])
                            if pins["maps"][current_pin_map][etname]["action"]["type"] != "Indefinite":
                                # Switch off partner output if timeout elapsed
                                if pins["maps"][current_pin_map][pairpin]["status"] == "High" and event_times[et][2] == "timeout" and gone > int(event_times[et][1]):
                                    print("OFF")
                                    GPIO.output(int(pins["maps"][current_pin_map][etname]["action"]["arg1"]), False)
                                    pins["maps"][current_pin_map][pairpin]["status"] = "Low"
                                    changed = "yes"                            

            if len(event_times_out) > 0:
                # Check any outputs set as timeout and switch off if time has elapsed
                for et in event_times_out:
                    if GPIO.input(int(et)) and event_times_out[et][2] == "timeout":
                        gone = int(time.time()) - int(event_times_out[et][0])
                        if gone > int(event_times_out[et][1]):
                            print(gone, int(time.time()), int(event_times_out[et][0]))
                            etname = "gpio_" + str(et)
                            GPIO.output(int(et), False)
                            pins["maps"][current_pin_map][etname]["status"] = "Low"
                            changed = "yes"
                                
            if changed == "yes" or write_due == "yes":
                # Write full pinlist to file for browser access
                write_pin_list()
                write_due = "no"
            time.sleep(1)
            second_clock[0] += 1
            # If minute is ending, check timers and sync second_clock with real seconds
            if second_clock[0] >= second_clock[1]:
                second_clock[0] = 0
                check_timers()
            
    except (KeyboardInterrupt, SystemExit):
        GPIO.cleanup()
        print("EXIT")
        os._exit(1)

