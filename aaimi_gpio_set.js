// Pin configuration page for AAIMI GPIO
// Flags to monitor which divs are shown/hidden
var screenState = "set";
var previousScreenState = "set";
// The currenly displayed pin configuration map, 'session' is default, user can create others
var current_pin_map = "session";
// Array to hold full details for all active digital and ananlog pins between file reads
var allPins = {};
// The currently selected pin name
var current_pin = "NoPin";
var current_pin_status = "Pending";
var current_pin_setting = "Pending";
var current_div = "";
var previousPin = "";
// PHP file to send socket requests to Python program, aaimi_gpio.py
var commandPHP = "aaimi_gpio.php"; 
// Hold temporary details during pin mods
var current_pin_name = "";
var current_pintype = "";
// Ordered list of all Raspberry Pi pins used for drawing the 40 pin buttons
var piPinsList = ["3V3_1", "5V_1", "gpio_2", "5V_2", "gpio_3", "GND_1", "gpio_4", "gpio_14", "GND_2", "gpio_15", "gpio_17", 
			"gpio_18", "gpio_27", "GND_3", "gpio_22", "gpio_23", "3V3_2", "gpio_24", "gpio_10", "GND_4",
			 "gpio_9", "gpio_25", "gpio_11",  "gpio_8", "GND_5", "gpio_7", "DNC_1", "DNC_2", "gpio_5", "GND_6",
			 "gpio_6", "gpio_12", "gpio_13", "GND_7", "gpio_19", "gpio_16", "gpio_26", "gpio_20", "GND_8", "gpio_21"];
// Ordered ist of all Arduino Pins used for drawing the pin buttons
var arduinoPinList = ["D0", "A5", "D1", "A4", "D2", "A3", "D3", "A2", "D4", "A1", "D5", "A0", "D6", "BLANK2", "D7", "VIN",
			"D8", "GND1", "D9", "GND2", "D10", "5V", "D11", "3V3", "D12", "RESET", "D13", "IOREF", "GND3", "BLANK", "AREF"];
// A list of all maps in the pin details file
var savedMaps = [];
var pinmaps = 0;
// HTML to populate pin buttons and divs
var pageSetText = "";

$(document).ready(function(){
	// Get a list of all digital and analog pins and their settings
	console.log("Getting pins");
	getAllPins()
});

///// Control buttons and their sub-divs ///////

// On/Off nav button
// Show options for starting/stopping program loop, and shutting down the Raspberry Pi
function openCloseOptions() {
	if (screenState != "OpenClose") {
		$('div#openCloseOptions').attr('style', 'display:block');
		$('div#resetDiv').attr('style', 'display:none');
		$('div#mapOptions').attr('style', 'display:none');
		$('div#savediv').attr('style', 'display:none');
		previousScreenState = screenState;
		screenState = "OpenClose"	
	}
	else {
		$('div#openCloseOptions').attr('style', 'display:none');	
		screenState = "set";
	}
};
// Switch the program loop on or off, or shut down the Raspberry Pi
function switchOnProgram(switchAction, command) {
	$.post("aaimi_gpio.php", {'commandsection':switchAction, 'command':command}, function(data) {
	alert(data);
	});
};

// Show optons for saving or resetting pin configurations
function mapOptions() {
	if (screenState != "maps") {
		$('div#mapOptions').attr('style', 'display:block');
		$('div#openCloseOptions').attr('style', 'display:none');
		$('div#resetDiv').attr('style', 'display:none');
		$('div#savediv').attr('style', 'display:none');
		previousScreenState = screenState;
		screenState = "maps"	
	}
	else {
		$('div#mapOptions').attr('style', 'display:none');	
		screenState = "set";
	}
};
// Reset the pins and switch to a new saved pin configuration
function changeCurrentMap(mapnum) {
	current_pin_map = savedMaps[mapnum];
	$.post("aaimi_gpio.php", {'commandsection':'choose_map', 'command':current_pin_map}, function(data) {
	alert(data);
	});
	getAllPins()
};

// Display option to reset main pin map
// Show the save form and list of saved pin maps
function showSaveDiv() {
	if (screenState != "save") {
		$('div#savediv').attr('style', 'display:block');
		$('div#resetDiv').attr('style', 'display:none');
		if (pinmaps > 1) {
			var savetxt = "<h2>Saved Maps</h2>";
			for (m = 0; m < savedMaps.length; m++) {
			savetxt = savetxt + "<button style='background-color:green;font-size:1em;margin-bottom:20px;' onclick='changeCurrentMap(" + m + ")'>" + savedMaps[m] + "</button><br>";				
			}
		}
		else{
			var savetxt = "<h2 style='color:blue'>You have no saved pin maps</h2>";
		}
		savetxt = savetxt + "<button style='font-size:1.3em;margin-bottom:20px;background-color:darkBlue;color:white;' onclick='saveCurrentMap()'>Save current map</button>";
		
		$('div#savediv').html(savetxt);
		previousScreenState = screenState;
		screenState = "save";
	}
	else {
		$('div#savediv').attr('style', 'display:none');
		screenState = "set";
	}
};
// Save pin configuration to file via PHP and Python
$('#saveform').submit(function(event) {
	event.preventDefault();
    var $uform = $( this ),
    	save_name = $uform.find( "input[name='savename']" ).val();
	console.log("Form");
	console.log(save_name);
	// Send details to Python program to add to main pin file 
	$.post(commandPHP, {'commandsection':'save', 'command':save_name}, function(data) {
		alert(data);
	});	
});
// Display the save form
function saveCurrentMap() {
	$('div#saveformdiv').attr('style', 'display:block');
};

// Display option to reset main pin map
function resetOptions() {
	if (screenState != "reset") {
		$('div#resetDiv').attr('style', 'display:block');
		$('div#openCloseOptions').attr('style', 'display:none');
		$('div#savediv').attr('style', 'display:none');
		previousScreenState = screenState;
		screenState = "reset"	
	}
	else {
		$('div#resetOptions').attr('style', 'display:none');	
		screenState = previousScreenState;
	}
};
// Send call to main program to delete current pin configuration and reset GPIO pins
function sendResetRequest() {
	resetPrompt = prompt("Are you sure you wish to delete this pin configuration? y/n");
	if (resetPrompt == "y") {
		$.post(commandPHP, {'commandsection':'reset', 'command':'reset'}, function(data) {
			if (data == "Done") {
				alert("GPIO pins have been reset");
			}
			else {
				alert(data);
			}
		});	
	}
};

//////////// PIN FORMS  /////////////////

// Initial pin configuration form to get a pin name and type (input/output, etc)
$('.pinform').submit(function(event) {
	event.preventDefault();
		// If Raspberry Pi, allow input or output for any pin
		if (current_pin.indexOf("gpio") != -1) {
			var $uform = $( this ),
				pin_namet = $uform.find( "input[name='nickname']" ).val(),
    			pin_typet = $uform.find( "select[name='pintype']" ).val();
		}
		// Arduino will automatically apply allowed pin type settings for pin
		// D11 and D12 can only be inputs, all other digitals can only be outputs
		// Ananlog pins can only be analog input
		else {
			var $uform = $( this ),
				pin_namet = $uform.find( "input[name='nickname']" ).val();
			if (current_pin == "D11" || current_pin == "D12") {
				pin_typet = "Input";
			}
			else if (current_pin.indexOf("A") != -1) {
				pin_typet = "Analog";
			}
			else if (current_pin.indexOf("D") != -1) {
				pin_typet = "Output";
			}
			console.log(current_pin);
			console.log(pin_typet);
		}
	// keep pin name and settings for following form
    current_pin_name = pin_namet;
    current_pintype = pin_typet;
	// Choose which form and form fields to display based-on pin type
	if (current_pintype.indexOf("Input") != -1 || current_pintype == "Analog") {
		var inputOutputTextHeading = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2>";
		$('form.outpinform').attr('style', 'display:none');
		$('form.pinform').attr('style', 'display:none');
		$('form.inpinform').attr('style', 'display:block');
		$('section#inputSection').attr('style', 'display:block');
		$('div#tempFormHeading').attr('style', 'display:block');
		$('div#tempFormHeading').html(inputOutputTextHeading);
		if (current_pintype == "Analog") {
		// Display an input for a trigger point for the analog pin
			$('.trig').attr('style', 'display:block');
		}
		else {
			$('.trig').attr('style', 'display:none');
		}
	}
	else if (current_pintype.indexOf("Output") != -1) {
		console.log("Starting Output");
		var inputOutputTextHeading = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2>";
		$('form.outpinform').attr('style', 'display:block');
		$('form.pinform').attr('style', 'display:none');
		$('form.inpinform').attr('style', 'display:none');
		$('section#outputSection').attr('style', 'display:block');

		$('div#tempFormHeading').attr('style', 'display:block');
		$('div#tempFormHeading').html(inputOutputTextHeading);
		if (current_pintype == "PWMOutputLed") {
			$('section#pwmSection').attr('style', 'display:block');
			$('p#pwmMotSpeedId').attr('style', 'display:none');
		}
		else if (current_pintype == "PWMOutput") {
			$('section#pwmSection').attr('style', 'display:block');
			$('p#pwmMotorSpeedId').attr('style', 'display:block')
		}
	}
	else {
		console.log(current_pintype);
	}
});

// Parse input form results base on whether pin is Pi or Arduino
$('.inpinform').submit(function(event) {
	event.preventDefault();
	var usercomm = "changeGPIOtype";
	if (current_pin.indexOf("gpio") != -1) {
	    var $uform = $( this ),
	    	pinhilo = $uform.find( "select[name='highOrLowChange']" ).val(), // default: high or low
			pinAction = $uform.find( "select[name='pinActions']" ).val(),  // How to react to event
			inOutPin = $uform.find( "input[name='inOutPin']" ).val(),  // output to switch on input event
			inOutTiming = $uform.find( "select[name='inOutTiming']" ).val(),  // Indicates action works on timer
			inOutTimeS = $uform.find( "input[name='inOutTimeS']" ).val(),   // Starting time
			inOutTimeE = $uform.find( "input[name='inOutTimeE']" ).val(),   // Ending time
			keepOn = $uform.find( "select[name='keepOn']" ).val(),   // Indicates action switches back after set time
			keepOnTime = $uform.find( "input[name='keepOnTime']" ).val();   // Timeout
	}
	else {
		// Will be Arduino pin
	    var $uform = $( this ),
	    	pinhilo = $uform.find( "select[name='highOrLowChange']" ).val(),
			pinAction = $uform.find( "select[name='pinActions']" ).val(),
			inOutPin = $uform.find( "input[name='inOutPin']" ).val(),
			triggerPoint = $uform.find( "input[name='trigger']" ).val(),   // Analog trigger point
			inOutTiming = $uform.find( "select[name='inOutTiming']" ).val(),
			inOutTimeS = $uform.find( "input[name='inOutTimeS']" ).val(),
			inOutTimeE = $uform.find( "input[name='inOutTimeE']" ).val(),
			keepOn = $uform.find( "select[name='keepOn']" ).val(),
			keepOnTime = $uform.find( "input[name='keepOnTime']" ).val();
	}
	// Construct a space-separated string of details to send to Python program via PHP socket
	var pimessage = current_pin_map + " " + current_pin + " " + current_pintype + " " + current_pin_name + " " + pinhilo;
	// Create HTML test to display overview of pin after form submission
	var inputOutputText = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2><p>Defualt: " + pinhilo + "</p>";
	// Add analog trigger point if pin is Arduino
	if (current_pin.indexOf("gpio") == -1) {
		if (triggerPoint != "") {
			inputOutputText = inputOutputText + "<p>Analog Trigger Point: " + triggerPoint + "</p>"; 
		}
	}
	// Set input pin to trigger output event
	if (pinAction == "switchOut" || pinAction == "switchOutoff" || pinAction == "adjustPWM") { 
		pimessage = pimessage + " " + pinAction + " " + inOutPin + " 0";
		if (pinAction == "switchOut") {
			inputOutputText = inputOutputText + "<p>Action: Swith GPIO" + inOutPin + " on</p>"; 
		}
		else {
			inputOutputText = inputOutputText + "<p>Action: Swith GPIO" + inOutPin + " off</p>";
		}
		pimessage = pimessage + " " + inOutTiming + " " + inOutTimeS + " " + inOutTimeE + " " + keepOn + " " + keepOnTime;
		// Timer options
		if (inOutTiming == "setTimes") {
			inputOutputText = inputOutputText + "<p>Only between " + inOutTimeS + " and " + inOutTimeE + "</p>";
		}
		if (keepOn != "Indefinite") {
			if (keepOn == "timeout") {
				inputOutputText = inputOutputText + "<p>Switch output back " + keepOnTime + " seconds after input returns to normal</p>";
			}
			else if (keepOn == "timeoutEvent") {
				inputOutputText = inputOutputText + "<p>Switch output back " + keepOnTime + " seconds after initial input event</p>";
			}
		}
		else {
			inputOutputText = inputOutputText + "<p>Leave output switched until you manually switch it back</p>";
		}
	}
	// Set input pin to increment count for each input event
	else if (pinAction == "countRecord") { 
		pimessage = pimessage + " " + pinAction + " 0 0";
		pimessage = pimessage + " " + inOutTiming + " " + inOutTimeS + " " + inOutTimeE + " " + keepOn + " " + keepOnTime;
	}
	// Add analog trigger point if Arduino
	if (current_pin.indexOf("gpio") == -1) {
		pimessage = pimessage + " " + triggerPoint
	}
	// Replace form with pin overview
	$('form.inpinform').attr('style', 'display:none');
	$('div#tempFormHeading').html(inputOutputText);
	// Send command to Python to add to main pin details
	$.post(commandPHP, {'commandsection':'config', 'command':pimessage}, function(data) {
		if (data != "Done") {
			alert(data);
		}
	});	
	alert(pimessage);		
});

// Parse output form results
$('.outpinform').submit(function(event) {
	event.preventDefault();
	var usercomm = "changeGPIOtype";
    var $uform = $( this ),
    	pinhilo = $uform.find( "select[name='outHighOrLowdefault']" ).val(), // default: high or low
		pinAction = $uform.find( "select[name='outPinActions']" ).val(),  // How to control the output
		arg1 =  $uform.find( "input[name='motorPair']" ).val(),  // Second pin for motor
		arg2 =  $uform.find( "input[name='motorSpeed']" ).val(),   // Default motor speed
		keepOn = $uform.find( "select[name='keepOnOut']" ).val(),  // Indicates output works on timeout
		timeout = $uform.find( "input[name='keepOnTimeOut']" ).val(), // Timeout in seconds
		inOutTiming = $uform.find( "select[name='inOutTiming']" ).val(),  // Indicates output works on timer
		inOutTimeS = $uform.find( "input[name='inOutTimeS']" ).val(),  // Start time
		inOutTimeE = $uform.find( "input[name='inOutTimeE']" ).val();  // End time
	// Create message for Python
	var pimessage = current_pin_map + " " + current_pin + " " + current_pintype + " " + current_pin_name + " " + pinhilo + " " + pinAction;
	// If pin is for motor, add pair pin and default motor speed
	if (current_pintype == "PWMOutput") {
		pimessage = pimessage + " " + arg1 + " " + arg2;
	}
	// If pin is for PWM LED, add filler then LED brightness (arg2)
	else if (current_pintype == "PWMOutputLed") {
		pimessage = pimessage + " 0 " + arg2;
	}
	// If standard output, just add fillers
	else {
		pimessage = pimessage + " 0 0";
	}
	pimessage = pimessage + " " + inOutTiming + " " + inOutTimeS + " " + inOutTimeE + " " + keepOn + " " + timeout;
	// Create HTML to display new settings to user
	var inputOutputText = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2><p>Defualt: " + pinhilo + "</p>";
	if (pinAction == "outManual" || pinAction == "outOnInput") { 		
		inputOutputText = inputOutputText + "<p>" + pinAction + "</p>";
	}
	// Timer options
	else if (pinAction == "outTimer") {
		if (pinhilo == "High") {
			inputOutputText = inputOutputText + "<p>" + pinAction + "</p><p>Switch LOW between " + inOutTimeS + " and " + inOutTimeE + "</p>";
		}
		else {
			inputOutputText = inputOutputText + "<p>" + pinAction + "</p><p>Switch HIGH between " + inOutTimeS + " and " + inOutTimeE + "</p>";
		}
	}
	// Replace form with pin overview HTML
	$('form.outpinform').attr('style', 'display:none');
	$('div#tempFormHeading').html(inputOutputText);
	// Send command to Python to add to main pin details
	$.post(commandPHP, {'commandsection':'config', 'command':pimessage}, function(data) {
		alert(data);
	});		
	alert(pimessage);
});

/////////////  FUNCTIONS  ///////////////////

// Show a div and optionally hide another
function showDiv(divToShow, divToHide) {
	var divText = "div#" + divToShow;
	$(divText).attr('style', 'display:block');
	if (divToHide != "none") {
	divText = "div#" + divToHide;
	$(divText).attr('style', 'display:none');
	}
}

// Change div class to reflect High or Low pin
function showHideClass(showClass, hideClass) {
	$(showClass).attr('style', 'display:block');
	if (hideClass != "none") {
	$(hideClass).attr('style', 'display:none');
	}
};

// Show and hide form fields depending on selected options
function showHideFields(field, label, show, button) {
	// Append the field id to tag
	var labelField = "p#" + field;
	var inputField = "input#" + field;
	var fieldButton = "button#" + button;
	if (show == "show") {
	$(labelField).attr('style', 'display:block');
	$(inputField).attr('style', 'display:block');	
	$(fieldButton).attr('style', 'display:none');	
	}
};

function changeHighLow(selectId) {
var selectfield = document.getElementById(selectId);
var selectedValue = selectfield.options[selectfield.selectedIndex].value;
if (selectedValue == "High" || selectedValue == "Low") {
	var highLowText = "Choose what happens when this pin goes " + selectedValue + ".";
	$('p#hilo').html(highLowText);
}
};

// Add and remove form options and fields based on a select box choice
function changeFormFields(targetId) {
var selectBox = document.getElementById(targetId);
var selectedValue = selectBox.options[selectBox.selectedIndex].value;
if (selectedValue.indexOf("Input") != -1) {
	$('section#inputSection').attr('style', 'display:block');
}
else if (selectedValue == "switchOut" || selectedValue == "switchOutoff") {
	$('section#inputActionSection').attr('style', 'display:block');
	$('section#submitInput').attr('style', 'display:block');
}
else if (selectedValue == "Analog") {
	console.log("AN");
	$('.trig').attr('style', 'display:block');
	$('p#defaultDialogue').html('React when pin goes Higher or Lower your trigger point?');
}
else if (selectedValue == "setTimes") {
	$('input#inOutTimeInpStart').attr('style', 'display:block');
	$('input#inOutTimeInpEnd').attr('style', 'display:block');	
}
else if (selectedValue == "timeout" || selectedValue == "timeoutEvent") {
	$('input#timeoutId').attr('style', 'display:block');
}
else if (selectedValue == "outOnInput") {
	console.log("OnINPUT");
	$('section#submitOutput').attr('style', 'display:block');
	$('p#inPutMessage').attr('style', 'display:block');
}
else if (selectedValue == "outTimer") {
	$('section#outputTimerSection').attr('style', 'display:block');
	$('section#submitOutput').attr('style', 'display:block');
}
else if (selectedValue == "outTimed") {
	$('section#outputTimedSection').attr('style', 'display:block');
	$('section#submitOutput').attr('style', 'display:block');
	$('input#timeoutIdOut').attr('style', 'display:block');
}
else if (selectedValue == "outManual") {
	$('section#submitOutput').attr('style', 'display:block');
}
else if (selectedValue == "countRecord") {
	$('section#submitInput').attr('style', 'display:block');
	$('p#inPutMessage').attr('style', 'display:block');
}
// Arduino
else if (selectedValue == "ajustPWM") {
	$('.inOutPWMSpeed').attr('style', 'display:block');
}
if (targetId == "pinActionSelect" || targetId == "ardPinActionSelect") {
	$('section#submitOutput').attr('style', 'display:block');
}
};

// Load the initial pin configuration form
function changePin() {
$('div#pin_set_holder').attr('style', 'display:none');
$('div#ArdPinFormDiv').attr('style', 'display:none');
$('div#pinFormDiv').attr('style', 'display:block');
$('h2#formHeading').html(current_pin);
};

// Load the initial Arduino pin configuration form
function changeArdPin() {
$('div#ard_pin_set_holder').attr('style', 'display:none');
$('div#pinFormDiv').attr('style', 'display:none');
$('div#ardPinFormDiv').attr('style', 'display:block');
if (current_pin == "D11" || current_pin == "D12") {
	$('option.ard_in').prop('disabled', true);	
	$('option.ard_out').prop('disabled', true);
	$('option.ard_an').prop('disabled', false);	
	$('option.ard_an').attr('style', 'display:block');	
}
$('h2#formHeading').html(current_pin);
};

//// Show the details div for the chosen Raspberry Pi pin
function showPinDetails(pinnum) {
	$('div.pindetails').attr('style', 'display:none');
	$('div.arddetails').attr('style', 'display:none');
	current_pin = piPinsList[pinnum];
	console.log(current_pin);
	var detailsDiv = "div#" + current_pin + "_details";
	$(detailsDiv).attr('style', 'display:block');
};

// Show the details div for a chosen Arduino pin
function showArdDetails(identifier) {
	console.log(identifier);
	show = "yes";
	// Get pin type from numeric identifier
	// 100 = D0, 113 = D13
	if (identifier >= 100 && identifier <=113) {
		thisDiv = "D" + (identifier - 100);
	}
	// GND pins, 51-53
	else if (identifier >= 51 && identifier <= 53) {
		rem = (identifier % 10);
		thisDiv = "GND" + rem;
	}
	// Analog pins, 114-119
	else if (identifier >= 114) {
		rem = (identifier % 114);
		thisDiv = "A" + rem;
		console.log(thisDiv);
	}
	else if (identifier == 33) {
		thisDiv = "3V3";
	}
	else if (identifier == 50) {
		thisDiv = "5V";
	}
	else {
		show = "no"
	}
	if (show == "yes") {
	current_pin = thisDiv;
	// Hide any open details divs and show the chosen div
	$('div.pindetails').attr('style', 'display:none');
	findButton = "button#" + thisDiv + "button";
	$('div.arddetails').attr('style', 'display:none');
	var detailsDiv = "div#" + thisDiv + "_details";
	$(detailsDiv).attr('style', 'display:block');
	}
};


/////////////////////// DRAW PINS

// Populate Arduino div using the data from the existing allPins array
function getArduinoPins() {
	// Is the pin IO pin (not power, GND, etc)?
	var ioPin = "no";
	previousPin = "";
	pageSetText = pageSetText + "<h2 style='color:white'>Arduino</h2>";
	for (var aPin = 1; aPin < arduinoPinList.length + 1; aPin++) {
		pinIndex = aPin - 1;
		thisPin = arduinoPinList[pinIndex];
		if (allPins[thisPin]) {
			ioPin = "yes";
		}
		if (thisPin.indexOf("BLANK") != -1) {
			// Add blue empty button to simulate empty space between UNO pin sections
			styletext = "color:blue;background-color:blue;border-color:blue;";
			ardPinNumber = 500
		}
		else if (thisPin.indexOf("GND") != -1) {
			styletext = "background-color:gray";
			ardPinNumberString = thisPin.replace("GND", "");
			ardPinNumber = parseInt(ardPinNumberString) + 51;
		}
		else if (thisPin.indexOf("A") != -1 && thisPin != "AREF") {
			// If active pin, set button color to its pin type default
			if (ioPin == "yes") {
				if (allPins[thisPin]["setting"].indexOf("Input") != -1) {
					styletext = "background-color:GreenYellow;";
				}
				else if (allPins[thisPin]["setting"].indexOf("Analog") != -1) {
					styletext = "background-color:Khaki;color:maroon;border-color:maroon";
				}
				else if (allPins[thisPin]["setting"].indexOf("Output") != -1) {
					styletext = "background-color:LightGreen;";
				}
				else {
					styletext = "background-color:maroon;color:white";
				}
			}
			ardPinNumberString = thisPin.replace("A", "");
			ardPinNumber = parseInt(ardPinNumberString) + 114;
			//console.log(thisPin);
			//console.log(allPins[thisPin]["setting"]);
		}
		// If digital pin set button background color to input if D11/D12, output for all others
		else if (thisPin.indexOf("D") != -1 && thisPin.indexOf("GND") == -1) {
			if (ioPin == "yes") {
				if (allPins[thisPin]["setting"].indexOf("Input") != -1) {
					styletext = "background-color:khaki;";
				}
				else if (allPins[thisPin]["setting"].indexOf("Output") != -1) {
					styletext = "background-color:LightGreen;";
				}
				else {
					if (thisPin == "D11" || thisPin == "D12") {
						styletext = "background-color:gold;";
					}
					else {
						styletext = "background-color:goldenrod;";
					}
				}
			}
			ardPinNumberString = thisPin.replace("D", "");
			ardPinNumber = parseInt(ardPinNumberString) + 100;
			//console.log(thisPin);
			//console.log(allPins[thisPin]["setting"]);
			
		}
		// Non IO pins
		else if (thisPin == "3V3") {
			styletext = "background-color:darkorange;";
			ardPinNumber = 33;
		}
		else if (thisPin == "5V") {
			styletext = "background-color:red;";
			ardPinNumber = 50;
		}
		else {
			styletext = "background-color:lightblue;";
			ardPinNumber = 90;
		}

		if (aPin % 2 != 0) {
			// Start new pair of buttons. Buttons are paired horizontally and their two details divs appear underneath the pair
			pageSetText = pageSetText + "<div class='pinpair'><div class='pi_pin' id='" + thisPin;
			// If pin is not set, use GPIO pin name. If set, use pin's nickname
			if (allPins[thisPin] && allPins[thisPin]['nickname'] != "nickname") {
				pageSetText = pageSetText + "'><button class='ard_left' onclick='showArdDetails(" + ardPinNumber + ")' style='float:left;" + styletext +  "' id='" + thisPin + "button'>" + thisPin + " " + allPins[thisPin]['nickname'] + "</button></div>";
			}
			else {
				pageSetText = pageSetText + "'><button class='ard_left' onclick='showArdDetails(" + ardPinNumber + ")' style='float:left;" + styletext +  "' id='" + thisPin + "button'>" + thisPin + "</button></div>";
			}
		}
		else {
			// Second button in pair, dont create new pair div
			if (thisPin.indexOf("BLANK") != -1) {
				pageSetText = pageSetText + "<div class='pi_pin' style='float:right;color:blue;background-color:blue;border-color:blue;' id='" + thisPin;
				pageSetText = pageSetText + "'><button class='ard_right' onclick='showArdDetails(" + ardPinNumber + ")' style='" + styletext + "' id='" + thisPin + "button'>" + thisPin + "</button></div></div>";
			}
			else {
				pageSetText = pageSetText + "<div class='pi_pin' style='float:right' id='" + thisPin;
				if (allPins[thisPin] && allPins[thisPin]['nickname'] != "nickname") {
					pageSetText = pageSetText + "'><button class='ard_right' onclick='showArdDetails(" + ardPinNumber + ")' style='" + styletext + "' id='" + thisPin + "button'>" + thisPin + " " + allPins[thisPin]['nickname'] + "</button></div></div>";	
				}
				else {
					pageSetText = pageSetText + "'><button class='ard_right' onclick='showArdDetails(" + ardPinNumber + ")' style='" + styletext + "' id='" + thisPin + "button'>" + thisPin + "</button></div></div>";	
				}				
			}
		}
		// Finish pair of buttons and add details divs below for each button in pair
		if (aPin % 2 == 0) {
			// Details div for first (left-hand button
			if (allPins[previousPin]) {
				pageSetText = pageSetText + "<div style='width:100%;display:none;margin-top:30px;' class='arddetails' id='" + previousPin + "_details'>";
				if (allPins[previousPin]['setting'] != "Unset") {
					// Display all details for pin if set
					pageSetText = pageSetText + "<br><h2 style='background-color:gold'>" + previousPin + ": " + allPins[previousPin]['nickname'] + "</h2>";
					pageSetText = pageSetText + "<p>" + allPins[previousPin]['setting'] + "</p>";
					pageSetText = pageSetText + "<p>Default: " + allPins[previousPin]['default'] + "</p>";
					pageSetText = pageSetText + "<p>Action: " + allPins[previousPin]['action']['type'] + "</p>";

					if (allPins[previousPin]['action']['type'].indexOf("switchOut") != -1) {
						pageSetText = pageSetText + "<p>Switch GPIO " + allPins[previousPin]["action"]["arg1"];
						if (allPins[previousPin]["action"]["type"] == "switchOutOff") {
							pageSetText = pageSetText + " off</p>";
						}
						else {
							pageSetText = pageSetText + " on</p>";
						}
					}

					if (allPins[previousPin]["action"]["timeout_type"] == "timeout") {
						pageSetText = pageSetText + "<p>Switch back after  " + allPins[previousPin]["action"]["timeout"] + " seconds</p>";
					}
				}
				else {
					// Just display allowed configuration for pin, input/outp/analog
					pageSetText = pageSetText + "<br><h2 style='background-color:gold'>" + previousPin + "</h2>";
					if (previousPin == "D11" || previousPin == "D12") {
						pageSetText = pageSetText + "<p>" + allPins[previousPin]['setting'] + ": Input Only</p>";
					}
					else {
						pageSetText = pageSetText + "<p>" + allPins[previousPin]['setting'] + ": Output Only</p>";
					}
				}
				pageSetText = pageSetText + "<button onclick='changeArdPin()'>Change setting</button></div><br><br>";
			}
			else {
				pageSetText = pageSetText + "<br>";
			}
			// Details divs for right-hand pin
			if (allPins[thisPin]) {
				pageSetText = pageSetText + "<div style='width:100%;display:none' class='arddetails' id='" + thisPin + "_details'>"; //
				if (allPins[thisPin]['setting'] != "Unset") {
					// Display full details if pin is set
					pageSetText = pageSetText + "<h2 style='background-color:maroon;color:white'>" + thisPin + ": " + allPins[thisPin]['nickname'] + "</h2>";
					pageSetText = pageSetText + "<p>" + allPins[thisPin]['setting'] + "</p>";
					pageSetText = pageSetText + "<p>Default: " + allPins[thisPin]['default'] + "</p>";
					if (allPins[thisPin]['setting'] == "Analog") {
						pageSetText = pageSetText + "<p>TriggerPoint: " + allPins[thisPin]['action']['arg3'] + "</p>";
					}
					pageSetText = pageSetText + "<p>Action: " + allPins[thisPin]['action']['type'] + "</p>";
					if (allPins[thisPin]['action']['type'].indexOf("switchOut") != -1) {
						pageSetText = pageSetText + "<p>Switch GPIO " + allPins[thisPin]["action"]["arg1"];
						if (allPins[thisPin]["action"]["type"] == "switchOutOff") {
							pageSetText = pageSetText + " off</p>";
						}
						else {
							pageSetText = pageSetText + " on</p>";
						}
					}
						// If timeout is set on an output or an input that operates an output
					if (allPins[thisPin]["action"]["timeout_type"] == "timeout") {
						pageSetText = pageSetText + "<p>Switch back after  " + allPins[thisPin]["action"]["timeout"] + " seconds</p>";
					}
				}
				else {
					pageSetText = pageSetText + "<h2 style='background-color:maroon;color:white'>" + thisPin + "</h2>";
					pageSetText = pageSetText + "<p>" + allPins[thisPin]['setting'] + ": Analog Input Only</p>";
				}
				pageSetText = pageSetText + "<br><button onclick='changeArdPin()'>Change setting</button></div><br>";
			}
			else {
				pageSetText = pageSetText + "<br>";
			}				
		}
		else {
			// Save details for left-hand button while creating right-hand button
			previousPin = thisPin;
		}
	}
// Load the HTML into the main arduino div
$('div#ard_pin_set_holder').html(pageSetText);
pageSetText = "";
};

// Get Paspberry Pi pin details from file and display in pin div
// then display Arduino details with getArduinoPins()
function getAllPins() {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
        	var myPin = JSON.parse(xmlhttp.responseText);
        	pinFunction(myPin);
    	}
	};
	xmlhttp.open("GET", "pin_details.txt", true);
	xmlhttp.send();  

	function pinFunction(pinlist) {
	    previousPin = "";
		pinmaps = Object.keys(pinlist[0].maps).length
		for (var key in pinlist[0].maps) {
			savedMaps.push(key);
		}
		current_pin_map = pinlist[0].current_map;
		maptext = "Current map: " + pinlist[0].current_map;
		$('h2#mapName').text(maptext);
		// Store contents of file to use again without another file read
		for (var key in pinlist[0].maps[current_pin_map]) {
			allPins[key] = {};
			allPins[key]["setting"] = pinlist[0].maps[current_pin_map][key]["setting"];
			allPins[key]["status"] = pinlist[0].maps[current_pin_map][key]["status"];
			allPins[key]["default"] = pinlist[0].maps[current_pin_map][key]["default"];
			allPins[key]["action"] = {};
			allPins[key]["action"]["type"] = pinlist[0].maps[current_pin_map][key]["action"]["type"];
			allPins[key]["action"]["arg1"] = pinlist[0].maps[current_pin_map][key]["action"]["arg1"];
			allPins[key]["action"]["arg2"] = pinlist[0].maps[current_pin_map][key]["action"]["arg2"];
			allPins[key]["action"]["timeout_type"] = pinlist[0].maps[current_pin_map][key]["action"]["timeout_type"];
			allPins[key]["action"]["timeout"] = pinlist[0].maps[current_pin_map][key]["action"]["timeout"];
			if (pinlist[0].maps[current_pin_map][key]["setting"] == "Analog") {
				allPins[key]["action"]["arg3"] = pinlist[0].maps[current_pin_map][key]["action"]["arg3"];
			}
			allPins[key]["nickname"] = pinlist[0].maps[current_pin_map][key]["nickname"];
		}
		// Create HTML for Raspi pins
		pageSetText = pageSetText + "<h2 style='color:white'>Raspberry Pi</h2>";
		for (var pb = 1; pb <= 40; pb++) {
			pinIndex = pb - 1;
			var buttoncol = "";
			var heading = "";
			thisPin = piPinsList[pinIndex];

				// Check that pin is GPIO rather than power or GND
				if (thisPin.indexOf("gpio") != -1) {
					var thisPinSetting = pinlist[0].maps[current_pin_map][thisPin]["setting"]
					var thisPinState = pinlist[0].maps[current_pin_map][thisPin]["status"]
					if (pb % 2 != 0) {						
						/// New pair, create holder and start left-hand pin
						pageSetText = pageSetText + "<div class='pinpair'><div class='pi_pin' id='" + thisPin;
						pageSetText = pageSetText + "'><button class='pi_left' id='" + thisPin + "button'";
					}
					else {
						/// Right-hand pin, just start right-hand pin
						pageSetText = pageSetText + "<div class='pi_pin' style='float:right' id='" + thisPin;
						pageSetText = pageSetText + "'><button class='pi_right' id='" + thisPin + "button'";
					}
						pageSetText = pageSetText + " type='button' onclick='showPinDetails(" + pinIndex + ")' style='background-color:";
					// Set color for pin button according to input/output type
					if (pinlist[0].maps[current_pin_map][thisPin]["setting"] == "Unset" && pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] != "OutputPartner") {
						buttoncol = "goldenrod";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["setting"].indexOf("Input") != -1) {
						buttoncol = "Khaki";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["setting"].indexOf("Output") != -1) {
						buttoncol = "LightGreen";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] != "OutputPartner") {
						buttoncol = "LightGreen";
					}
					// Prepend pin nickname to gpio number if set
					if (pinlist[0].maps[current_pin_map][thisPin]["nickname"] != "nickname") {
						newname = pinlist[0].maps[current_pin_map][thisPin]["nickname"] + " ";
						heading = thisPin.replace("gpio_", newname);
					}
					else {
						heading = thisPin.replace("gpio_", "GPIO ");
					}
					// Finish button pair after right-hand details button is created
					if (pb % 2 == 0) {
						pageSetText = pageSetText + buttoncol + "'>" + heading + "</button></div></div></div>";
						pageSetText = pageSetText + "<br>";
					}
					else {
						pageSetText = pageSetText + buttoncol + "'>" + heading + "</button></div>";
					}
				}
				else {
					// Will be power or GND pin
					if (thisPin.indexOf("3V3") != -1) {
						buttoncol = "darkorange";
						thisDivClass = "pi_power_3";
					}
					else if (thisPin.indexOf("5V") != -1) {
						buttoncol = "red";
						thisDivClass = "pi_power_5";
					}
					else if (thisPin.indexOf("GND") != -1) {
						buttoncol = "gray";
						thisDivClass = "pi_power_gnd";
					}
					else if (thisPin.indexOf("DNC") != -1) {
						buttoncol = "Silver";
						thisDivClass = "GND";
					}
					if (pb % 2 != 0) {	
						pageSetText = pageSetText + "<div class='pinpair'><div class='pi_pin' style='float:left' id='" + thisPin;
						pageSetText = pageSetText + "'><button class='pi_left' id='" + thisPin + "button'";
					}
					else {
						pageSetText = pageSetText + "<div class='pi_pin' style='float:right' id='" + thisPin;
						pageSetText = pageSetText + "'><button class='" + thisDivClass + "' id='" + thisPin + "button'";
					}
						pageSetText = pageSetText + " type='button' onclick='showPinDetails(" + pinIndex + ")' style='background-color:";				
					if (pb % 2 == 0) {
						pageSetText = pageSetText + buttoncol + "'>" + thisPin + "</button></div></div></div>";
						pageSetText = pageSetText + "<br>";
					}
					else {
						pageSetText = pageSetText + buttoncol + "'>" + thisPin + "</button></div>";						
					}										
				}
				// If right-hand pin, create details divs for pin pair.
				if (pb % 2 == 0) {
					pageSetText = pageSetText + "</div><div style='width:100%' class='pindetails' id='" + previousPin + "_details'><h2>" + previousPin.replace('gpio_', 'GPIO ') + "</h2>"; //</div>
					// Start details div for left-hand pin
					if ((previousPin.indexOf("gpio") != -1)) {
	 					pageSetText = pageSetText + "<p>" + previousPinSetting + "</p><p>Default state: " + previousPinState + "</p><p>Action: ";
						// If pin is input and set to switch an output, display partner pin and action
						if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"].indexOf("switchOut") != -1) {
							pageSetText = pageSetText + "Switch GPIO " + pinlist[0].maps[current_pin_map][previousPin]["action"]["arg1"];
							if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "switchOutOff") {
								pageSetText = pageSetText + " off</p>";
							}
							else {
								pageSetText = pageSetText + " on</p>";
							}
						}
						// If pin is output set to manual control
						else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "outManual") {
							pageSetText = pageSetText + "Manual on/off</p>";
						}
						// If pin is second pin in motor pair
						else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "OutputPartner") {
								pageSetText = pageSetText + "MotorPair: GPIO_" + pinlist[0].maps[current_pin_map][previousPin]["action"]["arg1"] + "</p>";
						}
						// If input set to count events
						else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "countRecord") {
							pageSetText = pageSetText + "Count input events</p>";
						}
						// If timeout is set on an output or an input that operates an output
						if (pinlist[0].maps[current_pin_map][previousPin]["action"]["timeout_type"] == "timeout") {
							pageSetText = pageSetText + "<p>Switch back after  " + pinlist[0].maps[current_pin_map][previousPin]["action"]["timeout"] + " seconds</p>";
						}
						// Create button to change pin settings
						pageSetText = pageSetText + "<button onclick='changePin()'>Change setting</button>";
					}

						pageSetText = pageSetText + "</div><div style='width:100%' class='pindetails' id='" + thisPin + "_details'><h2>" + thisPin.replace('gpio_', 'GPIO ') + "</h2>";
					// Start details div for right-hand pin
					if ((thisPin.indexOf("gpio") != -1)) {
	 					pageSetText = pageSetText + "<p>" + thisPinSetting + "</p><p>Default state: " + thisPinState + "</p><p>Action: ";
						if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"].indexOf("switchOut") != -1) {
							pageSetText = pageSetText + "Switch GPIO " + pinlist[0].maps[current_pin_map][thisPin]["action"]["arg1"];
							if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] == "switchOutOff") {
								pageSetText = pageSetText + " off</p>";
							}
							else {
								pageSetText = pageSetText + " off</p>";
							}
						}
						else if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] == "OutputPartner") {
								pageSetText = pageSetText + "MotorPair: GPIO_" + pinlist[0].maps[current_pin_map][thisPin]["action"]["arg1"] + "</p>";
						}
						else if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] == "countRecord") {
								pageSetText = pageSetText + "Count input events</p>";
						
						}
						if (pinlist[0].maps[current_pin_map][thisPin]["action"]["timeout_type"] == "timeout") {
							pageSetText = pageSetText + "<p>Switch back after  " + pinlist[0].maps[current_pin_map][thisPin]["action"]["timeout"] + " seconds</p>";
						}
						pageSetText = pageSetText + "<button onclick='changePin()'>Change setting</button>";					
					}
					// Close entire pin pair div
					pageSetText = pageSetText + "</di></div><br><br>";
				}
				else {
					// Save identifiers for after right-hand right pin is created
					previousPin = thisPin;
					previousPinSetting = thisPinSetting;
					previousPinState = thisPinState;
				}				
		}
	// Add HTML full pin details to the Raspberry Pi div
	$('div#pin_set_holder').html(pageSetText);
	// Reset pageSetText and call function to display Arduino pins
	pageSetText = "";
	getArduinoPins()
	};
};





