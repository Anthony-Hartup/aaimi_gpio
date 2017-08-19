# aaimi_gpio
# A Browser-based GPIO configuration and control interface for the Raspberry Pi
# Part of The AAIMI Project
# https://theaaimiproject.com
# By Anthony Hartup

# You can find full setup and usage instructions at:
# https://anthscomputercave.com/projects/aaimi/aaimi_gpio/aaimi_gpio.html?pagename=aaimi_gpio_setup

# This program runs in the background on a Raspberry Pi. You can switch the main loop on from the web-interface
# and configure GPIO pins as various types of inputs and outputs. You can assign tasks to react to input events.

# From the Run page you can switch outputs, PWM outputs and motors, and monitor the state of inputs.

# This is a brand new program and there are a few options missing or incomplete, and a few known bugs. I'm working on those things now.

# INCLUDED FILES

# aaimi_gpio.py
## - Runs at boot, listens to web socket for commands from GUI. Configures GPIO pins and maintains lists of pin configurations.

# index.html
## - Main pin configuration page. Contains forms to set pins.

# aaimi_gpio_set.js
## - Creates buttons for all pins and handles form input from index.html. Sends requests to aaimi_gpio.py via PHP socket.

# aaimi_gpio_run.html
## - Control page. Displays all defined pins and allows user to switch outputs and monitor inputs

# aaimi_gpio_run.js
## - manages layout for aaimi_gpio_run.html, sends control commands to aaimi_gpio.py via PHP socket

# aaimi_gpio.php
## - Routes requests from Javascript via socket to aaimi_gpio.py

# aaimi_gpio.css
## - Controls overall layout and appearance of HTML pages

# pi_details.txt
## - Holds a JSON list of GPIO configurations. Default configuration is called 'session'.
## - Users can save the current 'session' map to another map name to use later then reset the default map
