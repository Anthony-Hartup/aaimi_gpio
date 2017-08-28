
var commandPHP = "aaimi_gpio.php"; // PHP file taht sends socket requests to aaimi_gpio.py
var current_pin_map = "session";  // Default pin map from JSON pin file
var current_pin_status = "Pending";  // Is current pin High or Low
var current_pin_setting = "Pending"; // Type of Output or Input?
var active_current_pin = "NoPin"; // Currently user-selected pin
var current_pin = "NoPin";  // Current pin during getPinStatus()
//var current_div = "";
var current_speed = 0; // Speed of currently selected PWM pin
// Pins in use
var activePins = [];
// List of all pin details, rewritten each time getPinStatus() is called. 
var allPins = {};
// List of main details for PWM pins
var activePwmPins = {};
// runMode: Poll for changes if there are any input pins to monitor
var runMode = "Outputs";
var pageText = ""; // HTML to populate pin control div
var oldPageText = "";  // HTML from previou file check to compare with pageText
var previouspindiv = "";  // Keep track of last div shown


$(document).ready(function(){
	// Get a quick-list of defined pins
	getActivePins()
	alert("Entering control mode");
	// Get full details on active pins from Python-generated JSON list
	getPinStatus()
});

setInterval(function(){
	// Poll JSON file for changes if any pins are set as input, do nothing if none
	if (runMode == "Inputs") {
		getPinStatus()
	}
}, 3017);

// Hide details div for previous pin
function hideDetailsDivs() {
	$('div.pindetails').attr('style', 'display:none');	
};

// Direct user to go to the config page to either save a pin map or reset the main map
function showConfig() {
	alert("Go to the Setup page to modify pin configurations");
};

///////////// PWM Functions  ///////////

// Change the direction of a PWM motor
function changeDirection(rotation) {
	var directionComm = allPins[active_current_pin]["nickname"] + " 1 " + rotation;
	$.post(commandPHP, {'commandsection':'switchMotor', 'command':directionComm}, function(data) {
		if (data == "Done") {
			allPins[active_current_pin]["direction"] = rotation;
			allPins[active_current_pin]["speed"] = allPins[active_current_pin]["speed_default"];
			activePwmPins[active_current_pin]['speed'] = allPins[active_current_pin]["speed_default"]
			activePwmPins[active_current_pin]['direction'] = rotation;
			current_speed = allPins[active_current_pin]["speed_default"];
			//$( "#amount" ).val( current_speed );
			$("#speed_div").slider("value", $("#speed_div").slider("option", "min") );
			$( "#amount" ).val( $( "#speed_div" ).slider( "value" ) );
			// Change button border colors to highlight selected direction
			if (rotation == "Forwards") {
				$('button#forwardbutton').attr('style', 'border-color:white;background-color:maroon');
				$('button#reversebutton').attr('style', 'border-color:black;background-color:DarkBlue');				
				console.log("Going forwards");
			}
			else {
				$('button#forwardbutton').attr('style', 'border-color:black;background-color:maroon');
				$('button#reversebutton').attr('style', 'border-color:white;background-color:DarkBlue');
				console.log("Going backwards");
			}			
		}
		else {
			alert(data);
		}
	});	
};

// Handle PWM speed slider adjustments
var speed = 0;
  $( function() {
    $( "#speed_div" ).slider({
      orientation: "horizontal",
      range: "min",
      min: 0,
      max: 100,
      value: current_speed,
      slide: function( event, ui ) {
	if (ui.value != speed) {
	speed = ui.value;
	console.log(activePwmPins[active_current_pin]["direction"]);
	if (activePwmPins[active_current_pin]["direction"] == "none") {
		// Will be LED
		speedMessage = active_current_pin.replace("gpio_", "") + " " + ui.value;
		$.post(commandPHP, {'commandsection':'speedPWM', 'command':speedMessage});
	}
	else {
		// Will be motor
		speedMessage = activePwmPins[active_current_pin]["name"] + " " + activePwmPins[active_current_pin]['direction'] + " " + ui.value;
		$.post(commandPHP, {'commandsection':'speedMotor', 'command':speedMessage});
	}
        $( "#amount" ).val( speed );
	}
      }
    });
    $( "#amount" ).val( $( "#speed_div" ).slider( "value" ) );
  });
//

// Switch a PWM motor or LED
function switchPwmMotPin(action, swpin, pwmType) {
	var pwmOn = "yes";
	var mess = "TYPE: " + pwmType;
	var switchCommand = "";
	if (pwmType == 0) {
		// Will be motor
		switchAction = "switchMotor";
		$('div#directionButtonsb').attr('style', 'display:block');
		$('div#directionButtonsf').attr('style', 'display:block');
		var switchCommand = activePwmPins[active_current_pin]["name"] + " " + action + " " + activePwmPins[active_current_pin]["direction"];
	}
	else {
		// Will be LED
		switchAction = "switchPWM";
		$('div#directionButtonsb').attr('style', 'display:none');
		$('div#directionButtonsf').attr('style', 'display:none');
		switchCommand = switchCommand + active_current_pin.replace("gpio_", "") + " " + action;
	}
	$.post(commandPHP, {'commandsection':switchAction, 'command':switchCommand}, function(data) {
		if (data == "Done") {
			pwmOn = "yes";
		}
		else {
			alert(data);
		}
	});
	var pinDisplayName = "GPIO " + swpin + ": PWM output";
	thisdiv = "div#pinid" + active_current_pin.replace("gpio_", "");
	if (action == 1 && pwmOn == "yes") {
		// Show PWM window with slider
		$('h2#speedHeading').text(pinDisplayName);
		$('div#pin_holder').attr('style', 'display:none');
		$('div#speed_display_div').attr('style', 'display:block');
		allPins[active_current_pin]["status"] = "High"	
		allPins[active_current_pin]["speed"] = allPins[active_current_pin]["default_speed"]	
		classChoiceOld = switchAction + "Low";		
		classChoiceNew = switchAction + "High";	
		$(thisdiv).removeClass(classChoiceOld).addClass(classChoiceNew);
	}
	else if (action == 0) {
		// Hide PWM window
		$('div#pin_holder').attr('style', 'display:block');
		$('div#speed_display_div').attr('style', 'display:none');
		allPins[active_current_pin]["status"] = "Low";
		allPins[active_current_pin]["speed"] = 0;	
		$("#speed_div").slider("value", $("#speed_div").slider("option", "min") );
		$( "#amount" ).val( $( "#speed_div" ).slider( "value" ) );
		classChoiceOld = switchAction + "High";		
		classChoiceNew = switchAction + "Low";	
		thisdiv = "div#pinid" + active_current_pin.replace("gpio_", "");
		$(thisdiv).removeClass(classChoiceOld).addClass(classChoiceNew);
	}
	// Get all pin status without opening file
	getPinStatusQuick()
};

// Show the PWM div for the current pin
function showSpeed() {
	var pinDisplayName = current_pin + ": PWM output";
	$('h2#speedHeading').text(pinDisplayName);
	$('div#pin_holder').attr('style', 'display:none');
	$('div#speed_display_div').attr('style', 'display:block');	
};

// Toggle general divs
function swapDiv(divnameOff, divnameOn) {
	dOff = "div#" + divnameOff;
	dOn = "div#" + divnameOn;
	$(dOn).attr('style', 'display:block');
	$(dOff).attr('style', 'display:none');
	getPinStatusQuick()	
};

// Switch a standard output pin (on/off, pin number)
function switchPin(action, swpin) {
	var switchCommand = action + " " + swpin
	$.post(commandPHP, {'commandsection':'switch', 'command':switchCommand}, function(data) {
		if (data == "Done") {
			thisdiv = "div#pinid" + swpin;
			// Change class of pin divs to reflect on/off
			if (action == 0) {
				$(thisdiv).removeClass('OutputHigh').addClass('OutputLow');
			}
			else {
				$(thisdiv).removeClass('OutputLow').addClass('OutputHigh');
			}
		}
		else {
			alert(data);
		}
	});
};

// Show the details div for the selected pin
function showButtonDiv(divnumber) {
	$('div.actiondiv').attr('style', 'display:none');
	var targetpindiv = "div#pinactiondiv" + divnumber;
	$(targetpindiv).attr('style', 'display:block');
	previouspindiv = targetpindiv;
	//pinName = activePins[divnumber];
	active_current_pin = activePins[divnumber];
};

// Create a quick-list of all set pins
function getActivePins() {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    	if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
        	var myPin = JSON.parse(xmlhttp.responseText);
        	pinFunction(myPin);
    	}
	};
	xmlhttp.open("GET", "pi_details.txt", true);
	xmlhttp.send();  
	// Check JSON data for each pin between 2 and 27
	var pincount = 2;
	function pinFunction(pinlist) {
		for (p = 2; p < 28; p++) {
			pinstring = "gpio_" + p;
			if (pinlist[0].maps[current_pin_map][pinstring]["setting"] != "Unset") {
				activePins.push(pinstring);
			}
		}
		var pintext = "";
		for (ap = 0; ap < activePins.length; ap++) {
			pintext = pintext + " " + activePins[ap];
		}
};
};

// Update the GUI with currently maintained data rather than re-open JSON file.
//   This avoids rapid file-reads when sliding PWM speed sliders
function getPinStatusQuick() {
	pageText = "";
	for (ap = 0; ap < activePins.length; ap++) {
		current_pin = activePins[ap];
		pinNum = current_pin.replace("gpio_", "");
		current_pin_setting = allPins[current_pin]["setting"];
		if (current_pin_setting == "Input" || current_pin_setting == "InputPullDown" || current_pin_setting == "InputPullUp") {
			runMode = "Inputs";
		}
		current_pin_status = allPins[current_pin]["status"];		
		pinclass = current_pin_setting + current_pin_status;
		pageText = pageText + "<div onclick='showButtonDiv(" + ap + ")' id='pinid" + current_pin.replace("gpio_", "") + "' style='border-style:solid;border-radius:6px;' class='" + pinclass + "'><h2 type='button'>" + activePins[ap] + ": " + allPins[current_pin]['nickname'] + "</h2>";
		pageText = pageText + "<p>" + current_pin_setting + "</p><p>Action: " + allPins[current_pin]["action"]["type"] + "</p><p>Status: " + allPins[current_pin]["status"] + "</p>";
		if (allPins[current_pin]["action"]["type"] == "countRecord") {
			pageText = pageText + "<p>Count: " + allPins[current_pin]["action"]["arg1"] + "</p>";
		}	
		pageText = pageText + "<div class='actiondiv' id='pinactiondiv" + ap + "'>";
		if (current_pin_setting == "Output") {
			pageText = pageText + "<button onclick='switchPin(1, " + current_pin.replace("gpio_", "") + ")' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
			pageText = pageText + "<button onclick='switchPin(0, " + current_pin.replace("gpio_", "") + ")' type='button'>Off</button>";
		}
		else if (current_pin_setting == "PWMOutput") {
			activePwmPins[current_pin] = {};
			activePwmPins[current_pin]["name"] = allPins[current_pin]["nickname"];
			activePwmPins[current_pin]["direction"] = allPins[current_pin]["action"]["arg3"];
			activePwmPins[current_pin]["speed"] = 0;
			activePwmPins[current_pin]["speed_default"] = allPins[current_pin]["action"]["arg2"];
			if (current_pin_status == "High") {
				pageText = pageText + "<button onclick='showSpeed()' style='background-color:LightGreen;margin-bottom:20px' type='button'>Change speed</button>";
			}
			else {
				pageText = pageText + "<button onclick='switchPwmMotPin(1, " + current_pin.replace("gpio_", "") + ", 0)' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
			}
			pageText = pageText + "<button onclick='switchPwmMotPin(0, " + current_pin.replace("gpio_", "") + ", 0)' type='button'>Off</button>";
		}
		else if (current_pin_setting == "PWMOutputLed") {
			activePwmPins[current_pin] = {};
			activePwmPins[current_pin]["name"] = allPins[current_pin]["nickname"];
			activePwmPins[current_pin]["direction"] = "none";
			activePwmPins[current_pin]["speed"] = allPins[current_pin]["action"]["arg1"];
			activePwmPins[current_pin]["speed_default"] = allPins[current_pin]["action"]["arg2"];
			if (current_pin_status == "High") {
				pageText = pageText + "<p>PWM speed: " + activePwmPins[current_pin]["speed"] + "</p>";
				pageText = pageText + "<button id='speedPWM" + current_pin + "' onclick='showSpeed()' onclick='showSpeed()' style='background-color:LightGreen;margin-bottom:20px' type='button'>Change speed</button>";
			}
			else {
				pageText = pageText + "<button id='startPWM" + current_pin + "' onclick='switchPwmMotPin(1, " + current_pin.replace("gpio_", "") + ", 1)' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
			}
			pageText = pageText + "<button onclick='switchPwmMotPin(0, " + current_pin.replace("gpio_", "") + ", 1)' type='button'>Off</button>";
		}
		pageText = pageText + "</div></div><br>";
	}
	$('div#pin_holder').html(pageText);
	pageText = "";
};

// Get full details for all pins from JSON file and compose HTML for main div.
function getPinStatus() {
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
		if (allPins != pinlist[0].maps[current_pin_map]) {
		for (ap = 0; ap < activePins.length; ap++) {
			current_pin = activePins[ap];
			current_pin_setting = pinlist[0].maps[current_pin_map][current_pin]["setting"];
			if (current_pin_setting == "Input" || current_pin_setting == "InputPullDown" || current_pin_setting == "InputPullUp") {
				runMode = "Inputs";
			}
			current_pin_status = pinlist[0].maps[current_pin_map][current_pin]["status"];			
			pinclass = current_pin_setting + current_pin_status;

			// Created div with details for this pin. If output, add buttons to switch on and off
			pageText = pageText + "<div onclick='showButtonDiv(" + ap + ")' id='pinid" + current_pin.replace("gpio_", "") + "' style='border-style:solid;border-radius:6px;' class='" + pinclass + "'><h2 type='button'>" + activePins[ap] + ": " + pinlist[0].maps[current_pin_map][current_pin]["nickname"] + "</h2>";
			pageText = pageText + "<p>" + current_pin_setting + "</p><p>Action: " + pinlist[0].maps[current_pin_map][current_pin]["action"]["type"] + "</p><p>Status: " + pinlist[0].maps[current_pin_map][current_pin]["status"] + "</p>";
			if (pinlist[0].maps[current_pin_map][current_pin]["action"]["type"] == "countRecord") {
				pageText = pageText + "<p>Count: " + pinlist[0].maps[current_pin_map][current_pin]["action"]["arg1"] + "</p>";
			}	

			pageText = pageText + "<div class='actiondiv' id='pinactiondiv" + ap + "'>";
			if (current_pin_setting == "Output") {
				pageText = pageText + "<button onclick='switchPin(1, " + current_pin.replace("gpio_", "") + ")' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
				pageText = pageText + "<button onclick='switchPin(0, " + current_pin.replace("gpio_", "") + ")' type='button'>Off</button>";
			}
			else if (current_pin_setting == "PWMOutput") {
				activePwmPins[current_pin] = {};
				activePwmPins[current_pin]["name"] = pinlist[0].maps[current_pin_map][current_pin]["nickname"];
				activePwmPins[current_pin]["direction"] = pinlist[0].maps[current_pin_map][current_pin]["action"]["arg3"];
				activePwmPins[current_pin]["speed"] = 0;
				activePwmPins[current_pin]["speed_default"] = pinlist[0].maps[current_pin_map][current_pin]["action"]["arg2"];
				if (current_pin_status == "High") {
					pageText = pageText + "<button onclick='showSpeed()' style='background-color:LightGreen;margin-bottom:20px' type='button'>Change speed</button>";
				}
				else {
					pageText = pageText + "<button onclick='switchPwmMotPin(1, " + current_pin.replace("gpio_", "") + ", 0)' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
				}
				pageText = pageText + "<button onclick='switchPwmMotPin(0, " + current_pin.replace("gpio_", "") + ", 0)' type='button'>Off</button>";
			}
			else if (current_pin_setting == "PWMOutputLed") {
				activePwmPins[current_pin] = {};
				activePwmPins[current_pin]["name"] = pinlist[0].maps[current_pin_map][current_pin]["nickname"];
				activePwmPins[current_pin]["direction"] = "none";
				activePwmPins[current_pin]["speed"] = pinlist[0].maps[current_pin_map][current_pin]["action"]["arg1"];
				activePwmPins[current_pin]["speed_default"] = pinlist[0].maps[current_pin_map][current_pin]["action"]["arg2"];
				if (current_pin_status == "High") {
					pageText = pageText + "<p>PWM speed: " + activePwmPins[current_pin]["speed"] + "</p>";
					pageText = pageText + "<button id='startPWM" + current_pin + "' onclick='switchPwmMotPin(1, " + current_pin.replace("gpio_", "") + ", 1)' style='background-color:LightGreen;margin-bottom:20px;display:none' type='button'>On</button>";
					pageText = pageText + "<button id='speedPWM" + current_pin + "' onclick='showSpeed()' onclick='showSpeed()' style='background-color:LightGreen;margin-bottom:20px' type='button'>Change speed</button>";
				}
				else {
					pageText = pageText + "<button id='startPWM" + current_pin + "' onclick='switchPwmMotPin(1, " + current_pin.replace("gpio_", "") + ", 1)' style='background-color:LightGreen;margin-bottom:20px' type='button'>On</button>";
					pageText = pageText + "<button id='speedPWM" + current_pin + "' onclick='showSpeed()' style='background-color:LightGreen;margin-bottom:20px;display:none' type='button'>Change speed</button>"
				}
				pageText = pageText + "<button onclick='switchPwmMotPin(0, " + current_pin.replace("gpio_", "") + ", 1)' type='button'>Off</button>";
			}
			pageText = pageText + "</div></div><br>";
		}
		// Write to pin holder div only if details have changed since last read
		if (oldPageText != pageText) {
			$('div#pin_holder').html(pageText);
			$(previouspindiv).attr('style', 'display:block')
			oldPageText = pageText;
		}
		pageText = "";
		allPins = pinlist[0].maps[current_pin_map]
}
};
};





