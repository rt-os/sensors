#include "Sensors.h"

Sensors sensors;
unsigned long previousMillis = 0;
unsigned long reinitMillis = 0;
const long interval = 125;          // Reading interval (in milliseconds)
const long reinitInterval = 5000;   // Reinitialize offline sensors every 5 seconds
int errors = 0;

void setup() {
    Serial.begin(115200);
    int onlineSensors = sensors.begin(errors);
    Serial.println("Online sensors: " + String(onlineSensors));
}

void loop() {
    if (errors > 0) {
        Serial.println("No Mux or sensors detected. Check wiring.");
        delay(1000);
        return;
    }

    unsigned long currentMillis = millis();

    // Check if it's time to read sensors
    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;
        int readings[8];
        sensors.getReadings(readings);

        for (int i = 0; i < 8; i++) {
            Serial.print("\tD");
            Serial.print(i);
            Serial.print(" (mm): ");
            Serial.print((readings[i] != -1) ? String(readings[i]) : "null");
        }
        Serial.println();
    }

    // Check if it's time to reinitialize offline sensors
    if (currentMillis - reinitMillis >= reinitInterval) {
        reinitMillis = currentMillis;
        sensors.reinitializeOfflineSensors();
    }
}
