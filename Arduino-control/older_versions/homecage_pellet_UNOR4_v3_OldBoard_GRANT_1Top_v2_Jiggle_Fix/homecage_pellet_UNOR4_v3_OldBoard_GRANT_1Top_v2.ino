/*  AutomatedReaching
 *  For interfacing with MATLAB to control
 *  automated reaching hardware
 *  
 *  This code belongs to the IDEA Core.
 *  
 *  created Mar 2023
 *  by W. Ryan Williamson
 *  ryan.williamson@ucdenver.edu
 */

#include <Servo.h>
#include <analogWave.h>
#include <EEPROM.h>
#include <Wire.h>

analogWave wave(DAC);

Servo myservo;        // create servo object to control a servo
Servo myservo_cy;        // create servo object to control a servo
bool wireAvailable = false;
// Stepper 
const int stepPin = 16;      // Stepper steps
int stepCt = 0; 
const int stepsPerMM = 79; // 157/2 = 1 mm
int energizePin = 0;      // Stepper energy pin
int switchPin = 0; // will be set to one of the physical pins

// Stepper direction pins
const int dirPinX = 19; // physical pin for X axis stepper
const int dirPinY = 18; // physical pin for Y axis stepper
const int dirPinZ = 17; // physical pin for Z axis stepper
bool dirValX = true;
bool dirValY = true;
bool dirValZ = true;

// Stepper motor pins
const int energizeX = 4; // physical pin for X axis stepper
const int energizeY = 3; // physical pin for Y axis stepper
const int energizeZ = 2; // physical pin for Z axis stepper

// Homing switchF
const int switchX = 7; // physical pin for X axis switch
const int switchY = 6; // physical pin for Y axis switch
const int switchZ = 5; // physical pin for Z axis switch

// Current position of the pellet (mm)
int currX = 0;
int currY = 0;
int currZ = 0;

// Positions for the mouse (mm) relative to home
int mouseX = 5;
int mouseY = 25;
int mouseZ = 5;


int stepSpeed = 250; // 250 is fastest - 2000 is slowest/quietest
float servoInterv = 0.0;
int servoCt = 0;
int switchCt = 0; // dealing with noise?
bool isHoming = false; // only test switches when homing
bool homeFail = false; // did it go home?
int deliveryStyle = 0;
unsigned long buttonPressedTime = millis();
int allowButtonStyleChange = 1;
int allowButtonDelivery = 1;

// Ribbon group
const int servoPin_cy = 9;   // Magnet pin
const int servoPin = 11;    // Servo pin

// Button pin
const int buttonPin = 10;

// TTL
const int stimPin = 12;
int stimStyle = 0; // stimulation style

// Tones
int toneFreqA = 5000; // Freq (Hz)
const int toneTTL = 8; // tone pin
int tone2play = 5000;
int toneDur = 1000; // Duration in ms
int period = 100;
int toneIters = 1000;

// Servo empirically determined positions
int spoonHomeVal = 2000;  // level position for servo
int barrierHomeVal = 2000;  // level position for servo
int barrierMidVal = 2000;  // level position for servo
int eeAddress = 0; //EEPROM address to start reading from 
// 1 - 2070
// 2 - 2105
int fullBackSpoon = 2000; // angled back ~30 degrees
int downSpoon = 2000; // straight down
int foodRevealVal = 2000;

// Additional servo variables that do not change
float servoGoalVal = 0.0;  // target position for servo
int prevServoPos = 0;          // variable to store the servo position
int servoSetVal = 0;          // variable to store the servo position
int cylindoorState = 0; // 0=down ; 1=up
int deliveryState = 0; // 0=10mm away ; 1=at mouse
unsigned long timerVal = 0;
unsigned long servoSetTime = millis();
bool servoActive = false;

int msgInt = 0;
int ser2read = 0;
char rxChar = 'x';      // RXcHAR holds the received command
char rxStr[20];   // // Allocate some space for the string
char inChar = -1; // Where to store the character read
static unsigned int mPos = 0; // Index into array; where to store the character
int proxValue = 0;

//---------------- setup ---------------------------------------------
void setup(){
  // Load home value if it exists
  getSpoonServoHome();
  getBarrierServoHome();

  // Tone setup
  wave.sine(5000);
  wave.stop();

  // Outputs
  pinMode(toneTTL,OUTPUT);
  digitalWrite(toneTTL, LOW);   
  pinMode(stimPin,OUTPUT);
  digitalWrite(stimPin, LOW);   
  pinMode(stepPin,OUTPUT);
  digitalWrite(stepPin, LOW); 
  pinMode(dirPinX,OUTPUT);
  digitalWrite(dirPinX, LOW); 
  pinMode(dirPinY,OUTPUT);
  digitalWrite(dirPinY, LOW); 
  pinMode(dirPinZ,OUTPUT);
  digitalWrite(dirPinZ, LOW); 

  // Set energize pins to high
  pinMode(energizeX,OUTPUT); 
  pinMode(energizeY,OUTPUT); 
  pinMode(energizeZ,OUTPUT); 
  
  digitalWrite(energizeX, HIGH);
  digitalWrite(energizeY, HIGH);
  digitalWrite(energizeZ, HIGH);
  
  // Set pullup inputs
  pinMode(switchX, INPUT_PULLUP);
  pinMode(switchY, INPUT_PULLUP);
  pinMode(switchZ, INPUT_PULLUP);
  // pinMode(buttonPin,INPUT_PULLUP);
  pinMode(buttonPin,OUTPUT);
  digitalWrite(buttonPin, LOW);  

  //I2C Comm Initialization
  // Wire.begin(4);                // join i2c bus with address #4
  // Wire.onReceive(receiveEvent);          
  Serial.begin(9600);
  Serial1.begin(9600); // Open serial port (115200 bauds).
  Serial.flush();     // Clear receive buffer.

  // Attach servos
  openCylindoor();
  
  if (!myservo.attached()){
    myservo.attach(servoPin);
    while (!myservo.attached()){
      delay(1);
    }
  }
  prevServoPos = (float)spoonHomeVal;
  myservo.writeMicroseconds(prevServoPos);
  delay(500);

}

//--------------- loop -----------------------------------------------
void loop(){
  if (servoActive == true){
    if ((millis()-servoSetTime) > 2000){
      myservo_cy.detach();
      myservo.detach();
      servoActive = false;
    }
  }
  
  // if (digitalRead(buttonPin) == LOW & allowButtonDelivery == 1){
  //   buttonPressedTime = millis();
  //   while (digitalRead(buttonPin) == LOW){
  //     delay(10);
  //     if ((millis() - buttonPressedTime) > 2000){
  //       if (allowButtonStyleChange == 1){
  //         if (deliveryStyle == 0){
  //           deliveryStyle = 1;
  //         }
  //         else {
  //           deliveryStyle = 0;
  //         }
  //         playTone(2000);
  //         break;
  //       }
  //     }
  //   }
  //   while (digitalRead(buttonPin) == LOW){
  //     delay(10);
  //   }
  //   if ((millis() - buttonPressedTime) < 2000){
  //     if (cylindoorState == 1 & deliveryStyle == 0){
  //       delay(5);
  //       crackCylindoor();
  //       playTone(5000);
  //     }
  //     else if (deliveryState == 1){
  //       stepCt = abs(10)*stepsPerMM;
  //       energizePin = energizeY;
  //       delay(5);
  //       setStepper();
  //       playTone(5000);
  //       deliveryState = 0;
  //     }
  //     else {
  //       delay(5);
  //       sendHome();
  //       if (homeFail == false){
  //         delay(5);
  //         loadPellet();
  //         delay(5);
  //         sendHome();
  //         delay(5);
  //         if (deliveryStyle == 1){
  //           deliveryState = 1;
  //         }
  //         deliverPellet();
  //         playTone(6000);
  //         delay(5);
  //       }
  //     }
  //   }
  // }

 // I2C Comm
  // if (Wire.available() > 0) {
  //   rxChar = Wire.read();
  //   Serial.print("Received via I2C: ");
  //   Serial.println(rxChar);
  //   delay(50);
  //   while (Wire.available() > 0) {
  //     if(mPos < 19) // One less than the size of the array
  //     {
           
  //       inChar = Wire.read();
  //       if (inChar == 'x'){
  //         break;
  //       }
  //       rxStr[mPos] = inChar; // Store it
  //       mPos++; // Increment where to write next
  //     }
  //     delay(5);
  //   }
  //   rxStr[mPos] = '\0'; // Null terminate the string
  //   mPos=0;
  //   msgInt = atoi(rxStr);
  // }

//  Comm from controller
  ser2read = Serial1.available();
  if (ser2read > 0){          // Check receive buffer.
    // Serial.println(ser2read);
    delay(50);
    ser2read = Serial1.available();
    while (ser2read == Serial1.available()){
      rxChar = Serial1.read();
    }
    // Serial.print("Received via Serial: ");
    Serial.print(rxChar);
    if (ser2read > 1){
      for(int x = 1; x < ser2read; x++) {
        if(mPos < 19){ // One less than the size of the array
          // Serial.println((ser2read-x));
          while ((ser2read-x) == Serial1.available()){
            inChar = Serial1.read(); // Read a character
          }
          if (inChar == 'x'){
            break;
          }
          rxStr[mPos] = inChar; // Store it
          mPos++; // Increment where to write next
        }
      }
      rxStr[mPos] = '\0'; // Null terminate the string
      mPos=0;
      msgInt = atoi(rxStr);
    }
    else{
      msgInt = -1;
    }
  }
  
  // Comm from computer
  ser2read = Serial.available();
  if (ser2read > 0){          // Check receive buffer.
    // Serial.println(ser2read);
    delay(50);
    ser2read = Serial.available();
    // Serial.println(ser2read);
    while (ser2read == Serial.available()){
      rxChar = Serial.read();
    }
    // Serial.print("Received via Serial: ");
    Serial.print(rxChar);
    // delay(5);
    if (ser2read > 1){
      for(int x = 1; x < ser2read; x++) {
        if(mPos < 19){ // One less than the size of the array
          // Serial.println((ser2read-x));
          while ((ser2read-x) == Serial.available()){
            inChar = Serial.read(); // Read a character
          }
          if (inChar == 'x'){
            break;
          }
          rxStr[mPos] = inChar; // Store it
          mPos++; // Increment where to write next
        }
      }
      rxStr[mPos] = '\0'; // Null terminate the string
      mPos=0;
      msgInt = atoi(rxStr);
    }
    else{
      msgInt = -1;
    }
  }
        //  Serial.flush();                    // Clear receive buffer.
        //  rxChar = 'P';
  if (rxChar != 'x'){
    if (msgInt >= 0){
      Serial.print(msgInt);
    }

    Serial.print('!');
    if (rxChar == 'A'){
      setSpoonServoHome(msgInt);
      servoGoalVal = (float)spoonHomeVal;
      setServoPos();
    }
    else if (rxChar == 'B'){
      setBarrierServoHome(msgInt);
      setCylindoor();      
    }
    else if (rxChar == 'C'){
      getSpoonServoHome();      
      getBarrierServoHome();
    }
    else if (rxChar == 'D'){
      allowButtonStyleChange = msgInt;
    }
    else if (rxChar == 'E'){
      allowButtonDelivery = msgInt;
    }
    else if (rxChar == 'F'){
      Serial.println("P2");
    }
    else if (rxChar == 'G'){
      Serial.println("Current X, Y, and Z: " + String(currX) + " - " + String(currY) + " - " + String(currZ));
      Serial.println("Mouse X, Y, and Z: " + String(mouseX) + " - " + String(mouseY) + " - " + String(mouseZ));
      Serial.println("Switch X, Y, and Z: " + String(switchX) + " - " + String(switchY) + " - " + String(switchZ));
    }
    else if (rxChar == 'H'){ // Send steppers home
      sendHome();
    }
    else if (rxChar == 'I'){// Set mouse X
      mouseX = msgInt;
      if (mouseX > 10){
        mouseX = 10;
      }
      if (mouseX < 0){
        mouseX = 0;
      }
      deliverPellet();
    }
    else if (rxChar == 'J'){// Set mouse Y
      mouseY = msgInt;
      if (mouseY > 30){
        mouseX = 30;
      }
      if (mouseY < 20){
        mouseY = 20;
      }
      deliverPellet();
    }
    else if (rxChar == 'K'){// Set mouse Z
      mouseZ = msgInt;
      if (mouseZ > 10){
        mouseZ = 10;
      }
      if (mouseZ < 0){
        mouseZ = 0;
      }
      deliverPellet();
    }
    else if (rxChar == 'L'){
      if (msgInt == 0 | msgInt == 1){
        deliveryStyle = msgInt;
      }
    }
    else if (rxChar == 'M'){
      if (deliveryStyle == 1){
        deliveryState = 1;
      }
      deliverPellet();
      if (stimStyle == 1){
        digitalWrite(stimPin, HIGH);
        delay(5); 
        digitalWrite(stimPin, LOW);
      }
      playTone(6000);
    }
    else if (rxChar == 'N'){
      Serial.println("available");
    }
    else if (rxChar == 'O'){
      Serial.println("available");
    }
    else if (rxChar == 'P'){// Load a single pellet
      sendHome();
      loadPellet();
      sendHome();
    }
    else if (rxChar == 'Q'){
      delay(5);
      setCylindoor();
    }
    else if (rxChar == 'R'){
      delay(5);
      if (deliveryStyle == 0){
        crackCylindoor();
      }
      else if (deliveryState == 1){
        stepCt = abs(10)*stepsPerMM;
        energizePin = energizeY;
        setStepper();
        if (stimStyle == 2){
          digitalWrite(stimPin, HIGH);
          delay(5); 
          digitalWrite(stimPin, LOW);
          delay(5);
        }
      }
      playTone(5000);
      deliveryState = 0;
    }
    else if (rxChar == 'S'){//Send stimulation TTL
      digitalWrite(stimPin, HIGH);
      delay(25); 
      digitalWrite(stimPin, LOW);
    }
    else if (rxChar == 'T'){
      if (msgInt == 1){
        energizePin = energizeX;
        switchPin = switchX;
      }
      else if (msgInt == 2){
        energizePin = energizeY;
        switchPin = switchY;
      }
      else if (msgInt == 3){
        energizePin = energizeZ;
        switchPin = switchZ;
      }
    }
    else if (rxChar == 'U'){
      stepCt = msgInt*stepsPerMM;
      dirValX = true;
      dirValY = true;
      dirValZ = true;
      setStepper();
    }
    else if (rxChar == 'V'){
      stepCt = msgInt*stepsPerMM;
      dirValX = false;
      dirValY = false;
      dirValZ = false;
      setStepper();
    }
    else if (rxChar == 'W'){
      stimStyle = 0;
      if (msgInt == 1){
        stimStyle = 1;
      }
      else if (msgInt == 2){
        stimStyle = 2;
      }
    }
    else if (rxChar == 'X'){
      Serial.println("available");
    }
    else if (rxChar == 'Y'){
      Serial.println("available");
    }
    else if (rxChar == 'Z'){
      Serial.println("available");
    }
    Serial.println('%');
  }
  // Serial.flush();                    // Clear receive buffer.
  // myservo.detach();
  rxChar = 'x';
}
//I2C Comm reader function 
// void receiveEvent(int) {
//   // while (Wire.available() > 0) {
//   //   rxChar = Wire.read(); // receive byte as a character
//   Serial.print("Received via I2C: ");
//   Serial.println(rxChar);
//   // }
// }

void deliverPellet(){
  if (homeFail == true){
    return;
  }
  // Serial.println('  ');
  // Serial.println(currX);
  // Serial.println(mouseX);
  // Serial.println(currY);
  // Serial.println(mouseY);
  // Serial.println(currZ);
  // Serial.println(mouseZ);
  
  dirValX = true;
  if (mouseX > currX){
    dirValX = false;
  }
  stepCt = abs(currX-mouseX)*stepsPerMM;
  energizePin = energizeX;
  delay(5);
  setStepper();
  delay(5);

  dirValZ = true;
  if (mouseZ > currZ){
    dirValZ = false;
  }
  stepCt = abs(currZ-mouseZ)*stepsPerMM;
  energizePin = energizeZ;
  delay(5);
  setStepper();
  delay(5);

  dirValY = true;
  if (mouseY > currY){
    dirValY = false;
  }
  energizePin = energizeY;
  Serial.println(deliveryState);
  if (deliveryState == 1){
    stepCt = abs(currY-mouseY)*stepsPerMM;
    stepCt = stepCt-(10*stepsPerMM);
    Serial.println(stepCt);
  }
  else {
    stepCt = abs(currY-mouseY)*stepsPerMM;
    Serial.println(stepCt);
  }
  delay(5);
  setStepper();
  delay(5);
  if (deliveryState == 1){
    crackCylindoor();
  }
}

void loadPellet(){
  openCylindoor();
  if (deliveryState == 1){
    return;
  }
  if (homeFail == true){
    return;
  }
  delay(5);
  openCylindoor();
  delay(5);
  
  dirValX = false;
  dirValY = false;
  dirValZ = false;
  // Set X
  stepCt = 23*stepsPerMM;
  energizePin = energizeX;
  setStepper();
  
  servoGoalVal = (float)fullBackSpoon;
  setServoPos();
  
  // Set Z
  stepCt = 20*stepsPerMM;
  energizePin = energizeZ;
  setStepper();
  // setServoStep();

  servoGoalVal = (float)downSpoon;
  stepCt = 4*stepsPerMM;
  setServoStep();
  
  servoGoalVal = (float)spoonHomeVal;
  stepCt = 4*stepsPerMM;
  energizePin = energizeY;
  setServoStep();

  dirValZ = true;
  stepCt = 24*stepsPerMM;
  energizePin = energizeZ;
  setStepper();
  delay(5);
  
  delay(5);
  setCylindoor();
  delay(5);
  
  // myservo.detach();
//      digitalWrite(magnetPin, LOW);
//      delay(1000);

  // Serial.print(' ');
}

void stepPrep(){
  delay(5);
  digitalWrite(energizePin, LOW);
  delay(5);

  if (energizePin == energizeX){
    
    if (dirValX){
      digitalWrite(dirPinX,HIGH); // Enables the motor to move in a particular direction
      currX -= stepCt/stepsPerMM;
    }
    else {
      digitalWrite(dirPinX,LOW); // Enables the motor to move in a particular direction
      currX += stepCt/stepsPerMM;
    }
  }
  if (energizePin == energizeY){
    if (dirValY){
      digitalWrite(dirPinY,LOW); // Enables the motor to move in a particular direction
      currY -= stepCt/stepsPerMM;
    }
    else {
      digitalWrite(dirPinY,HIGH); // Enables the motor to move in a particular direction
      currY += stepCt/stepsPerMM;
    }
  }
  if (energizePin == energizeZ){
    if (dirValZ){
      digitalWrite(dirPinZ,HIGH); // Enables the motor to move in a particular direction
      currZ -= stepCt/stepsPerMM;
    }
    else {
      digitalWrite(dirPinZ,LOW); // Enables the motor to move in a particular direction
      currZ += stepCt/stepsPerMM;
    }
  }
}

void setServoStep(){
  stepPrep();
  delay(5);
  servoInterv = (float)stepCt;
  servoInterv = (servoGoalVal-(float)prevServoPos)/servoInterv;
  if (!myservo.attached()){
    myservo.attach(servoPin);
    while (!myservo.attached()){
      delay(1);
    }
  }
  for(int x = 0; x < stepCt; x++) {
    servoSetVal = prevServoPos+servoInterv*(float)x;
    myservo.writeMicroseconds(servoSetVal);
    // analogWrite(servoPin, map(servoSetVal, 600, 2400, 0, 4095));
    
    digitalWrite(stepPin,HIGH); 
    delayMicroseconds(1000); 
    digitalWrite(stepPin,LOW); 
    delayMicroseconds(1000);
  }
  prevServoPos = servoGoalVal;
  
  // 12-16-2025 NEW CODE: detach spoon servo immediately when at level (home) position
  if ((int)servoGoalVal == spoonHomeVal) {  // NEW CODE
    myservo.detach();                       // NEW CODE
  }                                         // NEW CODE
  // NEW CODE: detach spoon servo immediately when at level (home) position

  digitalWrite(dirPinX,LOW);
  delay(5);
  digitalWrite(dirPinY,LOW);
  delay(5);
  digitalWrite(dirPinZ,LOW);
  delay(5);
  digitalWrite(energizePin, HIGH);
  delay(5);
  servoSetTime = millis();
  servoActive = true;
}

void sendHome(){
  isHoming = true;
  homeFail = false;
  dirValX = true;  dirValY = true;  dirValZ = true;
  stepCt = 40*stepsPerMM;
  // Home Y
  energizePin = energizeY;
  switchPin = switchY;
  if (homeFail == false){
    setStepper();
  }
  // Home Z
  energizePin = energizeZ;
  switchPin = switchZ;
  if (homeFail == false){
    setStepper();
  }
  // Home X
  energizePin = energizeX;
  switchPin = switchX;
  if (homeFail == false){
    setStepper();
  }

  // Test for faulty or unplugged switch
  if (homeFail == false){
    isHoming = false;
    currX = 0;  currY = 0;  currZ = 0;

    stepCt = 1*stepsPerMM;
    dirValX = false;          dirValY = false;          dirValZ = false;
    energizePin = energizeY;  switchPin = switchY;
    setStepper();// Test Y
    if (digitalRead(switchPin) == HIGH){
      homeFail = true;
    }
    energizePin = energizeZ;  switchPin = switchZ;
    setStepper();// Test Z
    if (digitalRead(switchPin) == HIGH){
      homeFail = true;
    }
    energizePin = energizeX;  switchPin = switchX;
    setStepper();// Test X
    if (digitalRead(switchPin) == HIGH){
      homeFail = true;
    }
    if (homeFail == true){
      dirValX = true;           dirValY = true;           dirValZ = true;
      energizePin = energizeY;  switchPin = switchY;
      setStepper();// Test Y
      energizePin = energizeZ;  switchPin = switchZ;
      setStepper();// Test Z
      energizePin = energizeX;  switchPin = switchX;
      setStepper();// Test X
    }
  }
  if (homeFail == true){
    Serial.println("HomeFail");
  }
}

void setStepper(){
  stepPrep();
  delay(5);
  if (isHoming){
    homeFail = true;
    switchCt = 0;
  }
  // Makes 200 pulses for making one full cycle rotation
  for(int x = 0; x < stepCt; x++) {
    if (dirValX | dirValY | dirValZ){
      if (isHoming){
        if (digitalRead(switchPin) == HIGH){
          switchCt+=1;
          if (switchCt > 2){
            homeFail = false;
            // Serial.println(String(energizePin)+" pin "+String(x));
            break;
          }
        }
        else {
          switchCt = 0;
        }
      }
    }
    if (x > (stepCt-25) | x < 25){
      digitalWrite(stepPin,HIGH); 
      delayMicroseconds(stepSpeed*2); 
      digitalWrite(stepPin,LOW); 
      delayMicroseconds(stepSpeed*2);
    } 
    digitalWrite(stepPin,HIGH); 
    delayMicroseconds(stepSpeed); 
    digitalWrite(stepPin,LOW); 
    delayMicroseconds(stepSpeed);
  }
  
  // if (isHoming){
  //   for(int x = 0; x < 10; x++) {
  //     if (digitalRead(switchPin) == LOW){
  //       homeFail = false;
  //     }
  //     delay(1);
  //   }
  // }
  
  digitalWrite(dirPinX,LOW);
  delay(5);
  digitalWrite(dirPinY,LOW);
  delay(5);
  digitalWrite(dirPinZ,LOW);
  delay(5);
  digitalWrite(energizePin, HIGH);
  delay(5);
}

void setServoPos(){  
  if (!myservo.attached()){
    myservo.attach(servoPin);
    while (!myservo.attached()){
      delay(1);
    }
  }
  
  servoCt = abs((servoGoalVal-prevServoPos)/2)+1;
  servoInterv = (servoGoalVal-(float)prevServoPos)/(float)servoCt;
  if (servoCt > 0){
    for(int x = 0; x < servoCt; x++) {
      servoSetVal = prevServoPos+servoInterv*(float)x;
      myservo.writeMicroseconds(servoSetVal);
      // analogWrite(servoPin, map(servoSetVal, 600, 2400, 0, 4095));
      delay(3);
    }
    prevServoPos = servoGoalVal;
  }

    // 12-16-2025 NEW CODE: detach spoon servo immediately when at level (home) position
  if ((int)servoGoalVal == spoonHomeVal) {  // NEW CODE
    myservo.detach();                       // NEW CODE
  }                                         // NEW CODE

  servoSetTime = millis();                  // old code
  servoActive = true;                       // old code
    // 12-16-2025 NEW CODE: detach spoon servo immediately when at level (home) position

  servoSetTime = millis();
  servoActive = true;
}

void setCylindoor(){
  myservo_cy.writeMicroseconds(barrierHomeVal);
  cylindoorState = 1;
}

void crackCylindoor(){
  if (stimStyle == 2){
    if (deliveryStyle == 0){
      digitalWrite(stimPin, HIGH);
      delay(5); 
      digitalWrite(stimPin, LOW);
      delay(5);
    }
  }
  if (!myservo_cy.attached()){
    myservo_cy.attach(servoPin_cy);
    while (!myservo_cy.attached()){
      delay(1);
    }
  }
  myservo_cy.writeMicroseconds(barrierMidVal);
  cylindoorState = 0;
  servoSetTime = millis();
  servoActive = true;
}

void openCylindoor(){
  if (!myservo_cy.attached()){
    myservo_cy.attach(servoPin_cy);
    while (!myservo_cy.attached()){
      delay(1);
    }
  }
  myservo_cy.writeMicroseconds(foodRevealVal);
  servoSetTime = millis();
  servoActive = true;
}
void getSpoonServoHome(){
  eeAddress = 0;
  EEPROM.get(eeAddress, spoonHomeVal);
  if (spoonHomeVal == -1){
    spoonHomeVal = 2000;
  }
  setSpoonServoHome(spoonHomeVal);
  Serial.println(spoonHomeVal);
  Serial.println("Spoon home: " + String(spoonHomeVal));
}

void setSpoonServoHome(int home){
  eeAddress = 0;
  EEPROM.put(eeAddress, home);
  spoonHomeVal = home;
  fullBackSpoon = spoonHomeVal-1200; // angled back ~30 degrees
  downSpoon = spoonHomeVal-800; // straight down 
}

void getBarrierServoHome(){
  eeAddress = sizeof(int32_t);
  EEPROM.get(eeAddress, barrierHomeVal);
  if (barrierHomeVal == -1){
    barrierHomeVal = 1000;
  }
  setBarrierServoHome(barrierHomeVal);
  Serial.println("Barrier home: " + String(barrierHomeVal));
}

void setBarrierServoHome(int foodHome){
  eeAddress = sizeof(int32_t);
  EEPROM.put(eeAddress, foodHome);
  barrierHomeVal = foodHome;
  foodRevealVal = barrierHomeVal+250; // straight down 
  barrierMidVal = barrierHomeVal+100; // straight down 
}

void playTone(int freq){
  wave.freq(freq);
  wave.start();
  if (freq == 6000){
    digitalWrite(toneTTL, HIGH);
    delay(25);
    digitalWrite(toneTTL, LOW);
  }
  else{
    digitalWrite(buttonPin, HIGH);
    delay(25);
    digitalWrite(buttonPin, LOW);
  }
  delay(5);
  Serial.println("T"+String(freq));
  delay(290);
  wave.stop();
}
// End of the Sketch.
