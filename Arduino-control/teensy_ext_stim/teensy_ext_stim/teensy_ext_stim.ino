/*
  Teensy 4.0 StimROI TTL trigger
  - Listens for a single character 'S' on Serial.
  - Sets pin 13 HIGH for a short TTL pulse, then LOW.
  - Wire: BNC hot -> pin 13, BNC GND -> pin 14 (GND).
*/

const int TTL_PIN = 13;
const int PULSE_MS = 25; // TTL pulse width in milliseconds
const bool SERIAL_TEST_MODE = false;

void setup() {
  pinMode(TTL_PIN, OUTPUT);
  digitalWrite(TTL_PIN, LOW);
  Serial.begin(115200);
  if (SERIAL_TEST_MODE) {
    Serial.println("Teensy StimROI TTL ready. Send 'S' to pulse.");
  }
}

void loop() {
  if (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (SERIAL_TEST_MODE) {
      Serial.print("RX: ");
      Serial.println(c);
    }
    if (c == 'S') {
      if (SERIAL_TEST_MODE) {
        Serial.println("Test mode: received 'S' (no TTL pulse).");
      } else {
        digitalWrite(TTL_PIN, HIGH);
        delay(PULSE_MS);
        digitalWrite(TTL_PIN, LOW);
      }
    }
  }
}
