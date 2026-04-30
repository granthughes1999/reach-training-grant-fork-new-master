// =======================
// Leonardo TTL Stimulator
// 25 ms pulse on serial trigger
// =======================

// Pin definitions
const int TTL_PIN = 7;    // TTL output
const int GND_PIN = 8;    // Ground reference

// Pulse duration (milliseconds)
const unsigned long PULSE_WIDTH_MS = 25;

// Internal state
bool pulseActive = false;
unsigned long pulseStartTime = 0;

void setup() {
  // Configure pins
  pinMode(TTL_PIN, OUTPUT);
  pinMode(GND_PIN, OUTPUT);

  digitalWrite(TTL_PIN, LOW);
  digitalWrite(GND_PIN, LOW);

  // Serial must match Python baud
  Serial.begin(9600);
}

void loop() {

  // ---------- SERIAL TRIGGER ----------
  if (Serial.available() > 0) {
    char incoming = Serial.read();

    // Match Python: ser.write(b'x')
    if (incoming == 'x' && !pulseActive) {
      digitalWrite(TTL_PIN, HIGH);
      pulseStartTime = millis();
      pulseActive = true;
    }
  }

  // ---------- PULSE TIMING ----------
  if (pulseActive) {
    if (millis() - pulseStartTime >= PULSE_WIDTH_MS) {
      digitalWrite(TTL_PIN, LOW);
      pulseActive = false;
    }
  }
}
