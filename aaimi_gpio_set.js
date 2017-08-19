// Pin configuration page for AAIMI GPIO
// Flags to monitor which divs are shown/hidden
var screenState = "set";
var previousScreenState = "set";
// The currenly displayed pin configuration map, 'session' is default, user can create others
var current_pin_map = "session";
// The currently selected pin
var current_pin_status = "Pending";
var current_pin_setting = "Pending";
var current_pin = "NoPin";
var current_div = "";
// PHP file to send socket requests to Python program, aaimi_gpio.py
var commandPHP = "aaimi_gpio.php"; 
// Hold temporary details during pin mods
var current_pin_name = "";
var current_pintype = "";
// Ordered list of all Raspberry Pi pins
var allPinsList = ["3V3_1", "5V_1", "gpio_2", "5V_2", "gpio_3", "GND_1", "gpio_4", "gpio_14", "GND_2", "gpio_15", "gpio_17", 
			"gpio_18", "gpio_27", "GND_3", "gpio_22", "gpio_23", "3V3_2", "gpio_24", "gpio_10", "GND_4",
			 "gpio_9", "gpio_25", "gpio_11",  "gpio_8", "GND_5", "gpio_7", "DNC_1", "DNC_2", "gpio_5", "GND_6",
			 "gpio_6", "gpio_12", "gpio_13", "GND_7", "gpio_19", "gpio_16", "gpio_26", "gpio_20", "GND_8", "gpio_21"];
// Ordered ist of all Arduino Pins
var arduinoPinList = ["D0", "A5", "D1", "A4", "D2", "A3", "D4", "A2", "D5", "A1", "D6", "A0", "D7", "BLANK2", "D8", "VIN", "D9", "GND 1", "D10", "GND 2", "D11", "5V", "D12", "3V3", "D13", "RESET", "GND 3", "IOREF", "AREF"];
var savedMaps = [];
// HTML to populate pin buttons and divs
var pageSetText = "";
var pinmaps = 0;
var pincount = 2;
var previousPin = "";

$(document).ready(function(){
	// Get a list of all pins and their settings
	getAllPins()
	getArduinoPins()
});


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

// Show the save form and list of saved pin maps
function showSaveDiv() {
	if (screenState != "save") {
		$('div#savediv').attr('style', 'display:block');
		$('div#resetDiv').attr('style', 'display:none');
		if (pinmaps > 1) {
			var savetxt = "<h2>Saved Maps</h2>";
			for (m = 0; m < savedMaps.length; m++) {
				if (savedMaps[m] != "session") {
					savetxt = savetxt + "<button style='background-color:green;font-size:1em;margin-bottom:20px;' onclick='changeCurrentMap()'>" + savedMaps[m] + "</button><br>";
				}
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

// Switch the program loop on or off, or shut down the Raspberry Pi
function switchOnProgram(switchAction, command) {
	$.post("aaimi_gpio.php", {'commandsection':switchAction, 'command':command}, function(data) {
	alert(data);
	});
};

//////////// PIN FORMS  /////////////////

// Initial pin configuration for with pin name and type (input/output, etc)
$('.pinform').submit(function(event) {
	event.preventDefault();
    var $uform = $( this ),
    	pin_namet = $uform.find( "input[name='nickname']" ).val(),
    	pin_typet = $uform.find( "select[name='pintype']" ).val();
    current_pin_name = pin_namet;
    current_pintype = pin_typet;
	if (current_pintype.indexOf("Input") != -1) {
		var inputOutputTextHeading = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2>";
		$('form.outpinform').attr('style', 'display:none');
		$('form.pinform').attr('style', 'display:none');
		$('form.inpinform').attr('style', 'display:block');
		$('section.change_in_pin_setting').attr('style', 'display:block');
		$('div#tempFormHeading').attr('style', 'display:block');
		$('div#tempFormHeading').html(inputOutputTextHeading);
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

// Input settings
$('.inpinform').submit(function(event) {
	event.preventDefault();
	var usercomm = "changeGPIOtype";
    var $uform = $( this ),
    	pinhilo = $uform.find( "select[name='highOrLowChange']" ).val(),
		pinAction = $uform.find( "select[name='pinActions']" ).val(),
		inOutPin = $uform.find( "input[name='inOutPin']" ).val(),
		inOutTiming = $uform.find( "select[name='inOutTiming']" ).val(),
		inOutTimeS = $uform.find( "input[name='inOutTimeS']" ).val(),
		inOutTimeE = $uform.find( "input[name='inOutTimeE']" ).val(),
		keepOn = $uform.find( "select[name='keepOn']" ).val(),
		keepOnTime = $uform.find( "input[name='keepOnTime']" ).val();
	var pimessage = current_pin_map + " " + current_pin + " " + current_pintype + " " + current_pin_name + " " + pinhilo;
	var inputOutputText = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2><p>Defualt: " + pinhilo + "</p>";

	// Set input pin to trigger output event
	if (pinAction == "switchOut" || pinAction == "switchOutoff") { 
		pimessage = pimessage + " " + pinAction + " " + inOutPin + " 0";
		if (pinAction == "switchOut") {
			inputOutputText = inputOutputText + "<p>Action: Swith GPIO" + inOutPin + " on</p>"; 
		}
		else {
			inputOutputText = inputOutputText + "<p>Action: Swith GPIO" + inOutPin + " off</p>";
		}
		pimessage = pimessage + " " + inOutTiming + " " + inOutTimeS + " " + inOutTimeE + " " + keepOn + " " + keepOnTime;


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

	$('form.inpinform').attr('style', 'display:none');
	$('div#tempFormHeading').html(inputOutputText);
	$.post(commandPHP, {'commandsection':'config', 'command':pimessage}, function(data) {
		if (data != "Done") {
			alert(data);
		}
	});	
	alert(pimessage);		
});

// Outpu settings
$('.outpinform').submit(function(event) {
	event.preventDefault();
	var usercomm = "changeGPIOtype";
    var $uform = $( this ),
    	pinhilo = $uform.find( "select[name='outHighOrLowdefault']" ).val(),
		pinAction = $uform.find( "select[name='outPinActions']" ).val(),
		arg1 =  $uform.find( "input[name='motorPair']" ).val(),
		arg2 =  $uform.find( "input[name='motorSpeed']" ).val(),
		//inOutPin = $uform.find( "input[name='inOutPin']" ).val(),
		keepOnTime = $uform.find( "input[name='keepOnTimeOut']" ).val(),
		inOutTiming = $uform.find( "select[name='inOutTiming']" ).val(),
		keepOn = $uform.find( "select[name='keepOnOut']" ).val(),
		timeout = $uform.find( "input[name='keepOnTimeOut']" ).val(),
		inOutTimeS = $uform.find( "input[name='inOutTimeS']" ).val(),
		inOutTimeE = $uform.find( "input[name='inOutTimeE']" ).val();

	var pimessage = current_pin_map + " " + current_pin + " " + current_pintype + " " + current_pin_name + " " + pinhilo + " " + pinAction;
	if (current_pintype == "PWMOutput") {
		pimessage = pimessage + " " + arg1 + " " + arg2;
	}
	else if (current_pintype == "PWMOutputLed") {
		pimessage = pimessage + " 0 " + arg2;
	}
	else {
		pimessage = pimessage + " 0 0";
	}
	pimessage = pimessage + " " + inOutTiming + " " + inOutTimeS + " " + inOutTimeE + " " + keepOn + " " + timeout;
	var inputOutputText = "<h2>" + current_pin + "</h2><h2>" + current_pin_name + ": " + current_pintype + "</h2><p>Defualt: " + pinhilo + "</p>";

	if (pinAction == "outManual" || pinAction == "outOnInput") { 
		
		inputOutputText = inputOutputText + "<p>" + pinAction + "</p>";
	}
	else if (pinAction == "outTimer") {
		if (pinhilo == "High") {
			inputOutputText = inputOutputText + "<p>" + pinAction + "</p><p>Switch LOW between " + inOutTimeS + " and " + inOutTimeE + "</p>";
		}
		else {
			inputOutputText = inputOutputText + "<p>" + pinAction + "</p><p>Switch HIGH between " + inOutTimeS + " and " + inOutTimeE + "</p>";
		}
	}
	$('form.outpinform').attr('style', 'display:none');
	$('div#tempFormHeading').html(inputOutputText);
	$.post(commandPHP, {'commandsection':'config', 'command':pimessage}, function(data) {
		alert(data);
		//getPinStatus()
	});		
	alert(pimessage);
});

// Save pin configuration to file
$('#saveform').submit(function(event) {
	event.preventDefault();
    var $uform = $( this ),
    	save_name = $uform.find( "input[name='savename']" ).val();
	console.log("Form");
	console.log(save_name);
	//alert(pmessage);
	$.post(commandPHP, {'commandsection':'save', 'command':save_name}, function(data) {
		alert(data);
		//getPinStatus()
	});	
});

/////////////  FUNCTIONS  ///////////////////

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

// Change options and field based on a select box option
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
else if (selectedValue == "setTimes") {
	$('input#inOutTimeInpStart').attr('style', 'display:block');
	$('input#inOutTimeInpEnd').attr('style', 'display:block');	
}
else if (selectedValue == "timeout") {
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
if (targetId == "pinActionSelect") {
	$('section#submitOutput').attr('style', 'display:block');
}
};

// Load the initial pin configuration form
function changePin() {
$('div#pin_set_holder').attr('style', 'display:none');
$('div#pinFormDiv').attr('style', 'display:block');
$('h2#formHeading').html(current_pin);
};

// Show the details div for the chosen pin
function showButtonDiv(divnumber) {
	$('div.actiondiv').attr('style', 'display:none');
	var targetpindiv = "div#pinactiondiv" + divnumber;
	$(targetpindiv).attr('style', 'display:block');
};

function showPinDetails(pinnum) {
	$('div.pindetails').attr('style', 'display:none');
	current_pin = allPinsList[pinnum];
	console.log(current_pin);
	var detailsDiv = "div#" + current_pin + "_details";
	$(detailsDiv).attr('style', 'display:block');
};

// Show the details div for a chosen Arduino pin
function showArdDetails(identifier) {
	console.log(identifier);
	show = "yes";
	if (identifier <= 13) {
		thisDiv = "D" + identifier;
	}
	else if (identifier >= 51 && identifier <= 53) {
		rem = identifier % 10;
		thisDiv = "GND" + rem;
	}
	else if (identifier >= 20 && identifier <= 25) {
		rem = identifier % 10;
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
	findButton = "button#" + thisDiv + "button"
	$('div.arddetails').attr('style', 'display:none');
	var detailsDiv = "div#" + thisDiv + "_details";
	$(detailsDiv).attr('style', 'display:block');
	}
};


// Show the save div with list of saved pin maps
function saveCurrentMap() {
	$('div#saveformdiv').attr('style', 'display:block');
};

/////////////////////// DRAW PINS

// Populate Arduino div
function getArduinoPins() {
	pincount = 0;
	previousPin = "";
	pageSetText = pageSetText + "<h2 style='color:white'>Arduino</h2>";
	for (var aPin = 1; aPin < arduinoPinList.length + 1; aPin++) {
		pinIndex = aPin - 1;
		thisPin = arduinoPinList[pinIndex];
		
		if (thisPin.indexOf("BLANK") != -1) {
			// Create blank spot for gap in UNO pins
			styletext = "color:blue;background-color:blue;border-color:blue;";
			ardPinNumber = 500
		}
		else if (thisPin.indexOf("GND") != -1) {
			styletext = "background-color:gray;";
			gNum = thisPin[-1]
			ardPinNumber = "3" + gNum
		}
		else if (thisPin.indexOf("A") == 0) {
			styletext = "background-color:maroon;color:white";
			ardPinNumberString = thisPin.replace("A", "");
			ardPinNumber = parseInt(ardPinNumberString) + 20;
		}
		else if (thisPin.indexOf("D") != -1) {
			styletext = "background-color:gold;";
			ardPinNumber = thisPin.replace("D", "");
			
		}
		else if (thisPin == "3V3") {
			styletext = "background-color:orange;";
			ardPinNumber = 33;
		}
		else if (thisPin == "5V") {
			styletext = "background-color:red;";
			ardPinNumber = 50;
		}
		else {
			styletext = "background-color:lightblue;";
			ardPinNumber = 100;
		}

		if (aPin % 2 != 0) {
			// Start new pair of buttons
			pageSetText = pageSetText + "<div class='pinpair'><div class='pi_pin' id='" + thisPin;
			pageSetText = pageSetText + "'><button class='ard_left' onclick='showArdDetails(" + ardPinNumber + ")' style='float:left;" + styletext +  "' id='" + thisPin + "button'>" + thisPin + "</button></div>";
		}
		else {
			if (thisPin.indexOf("BLANK") != -1) {
				pageSetText = pageSetText + "<div class='pi_pin' style='float:right;color:blue;background-color:blue;border-color:blue;' id='" + thisPin;
				pageSetText = pageSetText + "'><button class='ard_right' onclick='showArdDetails(" + ardPinNumber + ")' style='" + styletext + "' id='" + thisPin + "button'>" + thisPin + "</button></div></div>";
			}
			else {
				pageSetText = pageSetText + "<div class='pi_pin' style='float:right' id='" + thisPin;
				pageSetText = pageSetText + "'><button class='ard_right' onclick='showArdDetails(" + ardPinNumber + ")' style='" + styletext + "' id='" + thisPin + "button'>" + thisPin + "</button></div></div>";					
			}
		}
		if (aPin % 2 == 0) {
			// Finish pair of buttons and add details divs below for each button in pair
			pageSetText = pageSetText + "</div><div style='width:100%;display:none' class='arddetails' id='" + thisPin + "_details'><h2 style='float:right'>" + thisPin + "</h2><p>Arduino features are coming soon.</p></div><br>";
			pageSetText = pageSetText + "</div><div style='width:100%;display:none' class='arddetails' id='" + previousPin + "_details'><h2>" + previousPin + "</h2><p>Arduino features are coming soon.</p></div><br><br>";
		}
		else {
			// Save details for left-hand button while creating right-hand button
			previousPin = thisPin;
		}
	}
$('div#ard_pin_set_holder').html(pageSetText);
pageSetText = "";
};

// Get Paspberry Pi pin details from file and display in pin div
function getAllPins() {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
        	var myPin = JSON.parse(xmlhttp.responseText);
        	pinFunction(myPin);
    	}
	};
	xmlhttp.open("GET", "pi_details.txt", true);
	xmlhttp.send();  

	function pinFunction(pinlist) {
		 pincount = 2;
	     previousPin = "";
		pinmaps = Object.keys(pinlist[0].maps).length
		for (var key in pinlist[0].maps) {
			savedMaps.push(key);
		}
		pageSetText = pageSetText + "<h2 style='color:white'>Raspberry Pi</h2>";
		for (var pb = 1; pb <= 40; pb++) {
			pinIndex = pb - 1;
			var buttoncol = "";
			var heading = "";
			thisPin = allPinsList[pinIndex];

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
						buttoncol = "gold";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["setting"].indexOf("Input")) {
						buttoncol = "GreenYellow";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["setting"].indexOf("Output")) {
						buttoncol = "LightGreen";
					}
					else if (pinlist[0].maps[current_pin_map][thisPin]["action"]["type"] != "OutputPartner") {
						buttoncol = "LightGreen";
					}
					if (pinlist[0].maps[current_pin_map][thisPin]["nickname"] != "nickname") {
						newname = pinlist[0].maps[current_pin_map][thisPin]["nickname"] + " ";
						heading = thisPin.replace("gpio_", newname);
					}
					else {
						heading = thisPin.replace("gpio_", "GPIO ");
					}
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
						buttoncol = "orange";
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
				if ((previousPin.indexOf("gpio") != -1)) {
 					pageSetText = pageSetText + "<p>" + previousPinSetting + "</p><p>Default state: " + previousPinState + "</p><p>Action: ";
					if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"].indexOf("switchOut") != -1) {
						pageSetText = pageSetText + "Switch GPIO " + pinlist[0].maps[current_pin_map][previousPin]["action"]["arg1"];
						if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "switchOutOff") {
							pageSetText = pageSetText + " off</p>";
						}
						else {
							pageSetText = pageSetText + " on</p>";
						}
					}
					else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "outManual") {
						pageSetText = pageSetText + "Manual on/off</p>";
					}
					else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "OutputPartner") {
							pageSetText = pageSetText + "MotorPair: GPIO_" + pinlist[0].maps[current_pin_map][previousPin]["action"]["arg1"] + "</p>";
					}
					else if (pinlist[0].maps[current_pin_map][previousPin]["action"]["type"] == "countRecord") {
						pageSetText = pageSetText + "Count input events</p>";
					}
					if (pinlist[0].maps[current_pin_map][previousPin]["action"]["timeout_type"] == "timeout") {
						pageSetText = pageSetText + "<p>Switch back after  " + pinlist[0].maps[current_pin_map][previousPin]["action"]["timeout"] + " seconds</p>";
					}
					pageSetText = pageSetText + "<button onclick='changePin()'>Change setting</button>";
				}

					pageSetText = pageSetText + "</div><div style='width:100%' class='pindetails' id='" + thisPin + "_details'><h2>" + thisPin.replace('gpio_', 'GPIO ') + "</h2>";
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
				pageSetText = pageSetText + "</di></div><br><br>";
				}
				else {
					previousPin = thisPin;
					previousPinSetting = thisPinSetting;
					previousPinState = thisPinState;
				}				
		}
$('div#pin_set_holder').html(pageSetText);
pageSetText = "";
};
};





