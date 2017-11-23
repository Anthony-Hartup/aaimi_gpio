<?php	
// Routes all incoming requests to the AAIMI GPIO program via socket
// Monitors pin file times for browser	
// Type of command
$command_type = $_POST['commandsection'];
//parameters
$commands = $_POST['command'];
// Message to indicate successful socket send
$return_message = "Pending";
// Full command to send
$message = $command_type . " " . $commands;

// Check mod time for pin file
if ($command_type == "file_time_check") {
	$fileTime = filemtime("pin_details.txt");
	echo $fileTime;
}
else {
// Open socket and send command to aaimi_gpio.py
if(!($sock = socket_create(AF_INET, SOCK_STREAM, 0))) {
	$errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);    
    die("Couldn't create socket: [$errorcode] $errormsg \n");
	$return_message = "Could not create";
}
if(!socket_connect($sock , '127.0.0.5' , 50001)) {
    $errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);     
    die("Could not connect: [$errorcode] $errormsg \n");
	$return_message = "Could not connect";
} 
if(!socket_send($sock , $message , strlen($message) , 0)) {
    $errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);     
    die("Could not send data: [$errorcode] $errormsg \n");
	$return_message = "Could not send";
}
if ($return_message == "Pending") {
	$return_message = "Done";
}
echo $return_message;
}
?>
