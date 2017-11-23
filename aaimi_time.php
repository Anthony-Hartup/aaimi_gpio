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
$fTime = filemtime("pin_details.txt");
echo $fTime;
?>
