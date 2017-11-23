#!/bin/bash

#AAIMI SERIAL CONTROLLER
#A module for the AAIMI Project / aaimi.anthscomputercave.com
#Works with light_monitor_arduino_03 Arduino sketch
#Written by Anthony Hartup

import serial, time

arduino = serial.Serial('/dev/ttyUSB0', 9600)

#Check sensor
def check(sensor):
    arduino.write(sensor)
    while True:
        try:
            time.sleep(0.01)
            light = str(arduino.readline()).replace("\n", "")
            return float(light)
        except:
            pass
            #KeyboardInterrupt 

def check_digital_sensor(sensor):
    arduino.write(sensor)
    while True:
        try:
            time.sleep(0.01)        
            rawsense = arduino.readline()
            return int(rawsense)
        except:
            pass
            #KeyboardInterrupt     

def switch(r):
    arduino.write(r)





        
