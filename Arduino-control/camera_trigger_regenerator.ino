/*
 * FLIR Camera Trigger Regenerator
 * 
 * Purpose: Clean up noisy BNC sync signals from master camera
 *          and regenerate clean triggers for slave cameras
 * 
 * Hardware Setup:
 *   - Master Camera Line1 (BNC) → Arduino Digital Pin 2 (via appropriate level shifter if needed)
 *   - Arduino Digital Pin 3 (BNC) → Slave Camera 1 Line3
 *   - Arduino Digital Pin 4 (BNC) → Slave Camera 2 Line3
 *   - Common Ground between all devices
 * 
 * Features:
 *   - Interrupt-driven trigger detection (minimal latency)
 *   - Configurable output pulse width
 *   - Debouncing to filter noise/ringing
 *   - LED indicator for trigger activity
 *   - Serial diagnostics output
 * 
 * Author: Generated for FLIR multi-camera sync troubleshooting
 * Version: 1.0
 * Date: January 2026
 */

// ===== CONFIGURATION =====
const int TRIGGER_INPUT_PIN = 2;      // Digital pin for trigger input from master camera
const int TRIGGER_OUTPUT1_PIN = 3;    // Digital pin for trigger output to slave 1
const int TRIGGER_OUTPUT2_PIN = 4;    // Digital pin for trigger output to slave 2
const int LED_PIN = LED_BUILTIN;      // Built-in LED for visual feedback

const unsigned long PULSE_WIDTH_US = 10;     // Output pulse width in microseconds
const unsigned long DEBOUNCE_US = 100;       // Minimum time between triggers (debounce)
const bool TRIGGER_ON_RISING = true;         // True for rising edge, false for falling edge

const bool ENABLE_SERIAL_DEBUG = true;       // Enable serial diagnostics
const unsigned long STATS_INTERVAL_MS = 5000; // Print statistics every 5 seconds

// ===== GLOBAL VARIABLES =====
volatile unsigned long triggerCount = 0;
volatile unsigned long lastTriggerMicros = 0;
volatile unsigned long minInterval = 999999999;
volatile unsigned long maxInterval = 0;
volatile unsigned long totalInterval = 0;

unsigned long lastStatsTime = 0;
unsigned long lastTriggerCountStats = 0;

// ===== SETUP =====
void setup() {
  // Initialize pins
  pinMode(TRIGGER_INPUT_PIN, INPUT);
  pinMode(TRIGGER_OUTPUT1_PIN, OUTPUT);
  pinMode(TRIGGER_OUTPUT2_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Ensure outputs are low
  digitalWrite(TRIGGER_OUTPUT1_PIN, LOW);
  digitalWrite(TRIGGER_OUTPUT2_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  
  // Initialize serial communication for diagnostics
  if (ENABLE_SERIAL_DEBUG) {
    Serial.begin(115200);
    while (!Serial && millis() < 3000); // Wait up to 3s for serial connection
    Serial.println("===================================");
    Serial.println("FLIR Camera Trigger Regenerator");
    Serial.println("===================================");
    Serial.println("Configuration:");
    Serial.print("  Input Pin: ");
    Serial.println(TRIGGER_INPUT_PIN);
    Serial.print("  Output Pin 1: ");
    Serial.println(TRIGGER_OUTPUT1_PIN);
    Serial.print("  Output Pin 2: ");
    Serial.println(TRIGGER_OUTPUT2_PIN);
    Serial.print("  Pulse Width: ");
    Serial.print(PULSE_WIDTH_US);
    Serial.println(" µs");
    Serial.print("  Debounce Time: ");
    Serial.print(DEBOUNCE_US);
    Serial.println(" µs");
    Serial.print("  Trigger Edge: ");
    Serial.println(TRIGGER_ON_RISING ? "RISING" : "FALLING");
    Serial.println("===================================");
    Serial.println("System ready. Waiting for triggers...");
  }
  
  // Attach interrupt
  int interruptMode = TRIGGER_ON_RISING ? RISING : FALLING;
  attachInterrupt(digitalPinToInterrupt(TRIGGER_INPUT_PIN), triggerISR, interruptMode);
  
  lastStatsTime = millis();
}

// ===== MAIN LOOP =====
void loop() {
  // Print statistics periodically
  if (ENABLE_SERIAL_DEBUG && (millis() - lastStatsTime >= STATS_INTERVAL_MS)) {
    printStatistics();
    lastStatsTime = millis();
  }
  
  // Blink LED briefly to show we're alive
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink >= 1000) {
    digitalWrite(LED_PIN, HIGH);
    delay(1);
    digitalWrite(LED_PIN, LOW);
    lastBlink = millis();
  }
}

// ===== INTERRUPT SERVICE ROUTINE =====
void triggerISR() {
  unsigned long currentMicros = micros();
  
  // Debouncing: ignore triggers that occur too quickly
  if (currentMicros - lastTriggerMicros < DEBOUNCE_US) {
    return; // Too soon, likely noise/ringing
  }
  
  // Calculate interval for statistics
  if (lastTriggerMicros > 0) {
    unsigned long interval = currentMicros - lastTriggerMicros;
    
    if (interval < minInterval) minInterval = interval;
    if (interval > maxInterval) maxInterval = interval;
    totalInterval += interval;
  }
  
  lastTriggerMicros = currentMicros;
  triggerCount++;
  
  // Generate clean output pulses
  digitalWrite(TRIGGER_OUTPUT1_PIN, HIGH);
  digitalWrite(TRIGGER_OUTPUT2_PIN, HIGH);
  digitalWrite(LED_PIN, HIGH);
  
  delayMicroseconds(PULSE_WIDTH_US);
  
  digitalWrite(TRIGGER_OUTPUT1_PIN, LOW);
  digitalWrite(TRIGGER_OUTPUT2_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
}

// ===== STATISTICS FUNCTION =====
void printStatistics() {
  unsigned long currentCount = triggerCount;
  unsigned long deltaCount = currentCount - lastTriggerCountStats;
  
  Serial.println("\n--- Trigger Statistics ---");
  Serial.print("Total Triggers: ");
  Serial.println(currentCount);
  Serial.print("Triggers/sec: ");
  Serial.println(deltaCount / (STATS_INTERVAL_MS / 1000.0), 1);
  
  if (currentCount > 1) {
    Serial.print("Avg Interval: ");
    Serial.print(totalInterval / (currentCount - 1));
    Serial.println(" µs");
    
    Serial.print("Avg Freq: ");
    Serial.print(1000000.0 / (totalInterval / (currentCount - 1)), 1);
    Serial.println(" Hz");
    
    Serial.print("Min Interval: ");
    Serial.print(minInterval);
    Serial.println(" µs");
    
    Serial.print("Max Interval: ");
    Serial.print(maxInterval);
    Serial.println(" µs");
  }
  Serial.println("-------------------------\n");
  
  lastTriggerCountStats = currentCount;
  
  // Reset min/max for next period
  minInterval = 999999999;
  maxInterval = 0;
  totalInterval = 0;
  triggerCount = 1; // Keep count going but reset interval stats
}

// ===== ALTERNATIVE: POLLING VERSION (if interrupts cause issues) =====
/*
 * If the interrupt-driven approach causes timing issues, 
 * uncomment this polling version and comment out the interrupt code
 * 
void loop() {
  static bool lastState = LOW;
  bool currentState = digitalRead(TRIGGER_INPUT_PIN);
  
  // Detect edge
  if (TRIGGER_ON_RISING && currentState == HIGH && lastState == LOW) {
    generateTriggerPulse();
  } else if (!TRIGGER_ON_RISING && currentState == LOW && lastState == HIGH) {
    generateTriggerPulse();
  }
  
  lastState = currentState;
  
  // Statistics printing (keep same as above)
  if (ENABLE_SERIAL_DEBUG && (millis() - lastStatsTime >= STATS_INTERVAL_MS)) {
    printStatistics();
    lastStatsTime = millis();
  }
}

void generateTriggerPulse() {
  unsigned long currentMicros = micros();
  
  if (currentMicros - lastTriggerMicros < DEBOUNCE_US) {
    return;
  }
  
  lastTriggerMicros = currentMicros;
  triggerCount++;
  
  digitalWrite(TRIGGER_OUTPUT1_PIN, HIGH);
  digitalWrite(TRIGGER_OUTPUT2_PIN, HIGH);
  delayMicroseconds(PULSE_WIDTH_US);
  digitalWrite(TRIGGER_OUTPUT1_PIN, LOW);
  digitalWrite(TRIGGER_OUTPUT2_PIN, LOW);
}
*/
