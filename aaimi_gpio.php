<?php	
// Routes all incoming requests to the AAIMI GPIO program via socket	
// Type of command
$command_type = $_POST['commandsection'];
//parameters
$commands = $_POST['command'];
// Flags to indicate success
$scope = "socket";
$return_message = "Pending";
// Full command to send
$message = $command_type . " " . $commands;

if ($scope == "socket") {
// Open socket
if(!($sock = socket_create(AF_INET, SOCK_STREAM, 0)))
{
	$errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);    
    die("Couldn't create socket: [$errorcode] $errormsg \n");
	$return_message = "Could not create";
}
// Connect socket to aaimi_gpio.pi
if(!socket_connect($sock , '127.0.0.1' , 50001))
{
    $errorcode = socket_last_error();
    $errormsg = socket_strerror($errorcode);     
    die("Could not connect: [$errorcode] $errormsg \n");
	$return_message = "Could not connect";
} 
// Send the full command
if( ! socket_send ( $sock , $message , strlen($message) , 0))
{
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
