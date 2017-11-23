//AAIMI Sensor Read 0.8
//Part of the AAIMI Project
//aaimi.anthscomputercave.com
//By Anthony Hartup

//Responds to requests from Raspberry Pi to
// read most types of digital analogue sensors and operates relays

//Default AD pins 
int satellite1 = A0;  
int satellite2 = A1;
int satellite3 = A2;
int satellite4 = A3;
int satellite5 = A4;
int satellite6 = A5;
// Digital outputs
int relay1 = 2;
int relay2 = 3;
int relay3 = 4;
int relay4 = 5;
int relay5 = 6;
int relay6 = 7;
int relay7 = 8;
int relay8 = 9;
int relay9 = 10;
int relay10 = 13; // Built-in LED
// Digital inputs
int input1 = 11;
int input2 = 12;
// Store the current pin number for an upcoming function
char currentPin = satellite1;
//float to keep sensor readings
float sensorLevel = 0.0; 

void setup() {
  // Set digital pins
  pinMode(relay1, OUTPUT);
  pinMode(relay2, OUTPUT);
  pinMode(relay3, OUTPUT);
  pinMode(relay4, OUTPUT);
  pinMode(relay5, OUTPUT);
  pinMode(relay6, OUTPUT);
  pinMode(relay7, OUTPUT);
  pinMode(relay8, OUTPUT);  
  pinMode(relay9, OUTPUT);
  pinMode(relay10, OUTPUT);    
  digitalWrite(relay1, LOW);
  digitalWrite(relay2, LOW);
  digitalWrite(relay3, LOW);
  digitalWrite(relay4, LOW);
  digitalWrite(relay5, LOW);
  digitalWrite(relay6, LOW);
  digitalWrite(relay7, LOW);
  digitalWrite(relay8, LOW);  
  digitalWrite(relay9, LOW);
  digitalWrite(relay10, LOW);
  pinMode(input1, INPUT);
  pinMode(input2, INPUT);      

  // Start serial connection
  Serial.begin(9600);
  while (!Serial) {
  }
  Serial.println("Serial Connected");
}

  // Read analog sensors
  float readSensor() {
    float sensorValue = analogRead(currentPin);
    sensorLevel = sensorValue * (5.0 / 1023.0);
    Serial.println(sensorLevel);
  }


void loop() {
  if (Serial.available()) {
     // read the incoming order from Raspberry Pi:
     char order = Serial.read();
     
     // Read analog sensors
     if (order == 'a') {
       currentPin = satellite1;
       readSensor();
      }    
     else if (order == 'b') {
       currentPin = satellite2;
       readSensor();
      }  
     else if (order == 'c') {
       currentPin = satellite3;
       readSensor();
      } 
     else if (order == 'd') {
       currentPin = satellite4;
       readSensor();
      } 
     else if (order == 'e') {
       currentPin = satellite5;
       readSensor();
      }
     else if (order == 'f') {
       currentPin = satellite6;
       readSensor();
      }  
      
     // Check digital inputs
     else if (order == 'K') {
       Serial.println(digitalRead(input1));
      } 
     else if (order == 'M') {
       Serial.println(digitalRead(input2));
      }  
                 
     // Switch Outputs
     else if (order == 'q') {
       digitalWrite(relay1, HIGH);
     }    
     else if (order == 'r') {
       digitalWrite(relay1, LOW);
     }   
     else if (order == 's') {
       digitalWrite(relay2, HIGH);
     }    
     else if (order == 't') {
       digitalWrite(relay2, LOW);
     }     
     else if (order == 'u') {
       digitalWrite(relay3, HIGH);
     }    
     else if (order == 'v') {
       digitalWrite(relay3, LOW);
     }  
     else if (order == 'u') {
       digitalWrite(relay4, HIGH);
     }    
     else if (order == 'v') {
       digitalWrite(relay4, LOW);
     }            
     else if (order == 'y') {
       digitalWrite(relay5, HIGH);
     }    
     else if (order == 'z') {
       digitalWrite(relay5, LOW);
     } 
     else if (order == 'i') {
       digitalWrite(relay6, HIGH);
     }    
     else if (order == 'j') {
       digitalWrite(relay6, LOW);
     }   
     else if (order == 'k') {
       digitalWrite(relay7, HIGH);
     }    
     else if (order == 'l') {
       digitalWrite(relay7, LOW);
     }   
     else if (order == 'm') {
       digitalWrite(relay8, HIGH);
     }    
     else if (order == 'n') {
       digitalWrite(relay8, LOW);
     }  
     else if (order == 'o') {
       digitalWrite(relay9, HIGH);
     }    
     else if (order == 'p') {
       digitalWrite(relay9, LOW);
     } 
     else if (order == 'O') {
       digitalWrite(relay10, HIGH);
     }    
     else if (order == 'P') {
       digitalWrite(relay10, LOW);
     }           
}
}
