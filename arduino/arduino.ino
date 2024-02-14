#include "Sensors.h"

Sensors sensors;
unsigned long previousMillis = 0;
const long interval = 50;  // Interval at which to read the sensors (in milliseconds)
int errors = 0;

void setup() {
    Serial.begin(115200);
    int onlineSensors = sensors.begin(errors);
    Serial.println("Online sensors: " + String(onlineSensors));
}

void loop() {
    if (errors>0) {
        Serial.println("no Mux or sensors detected, Check wireing");
        delay(1000);
        return;
    }
    unsigned long currentMillis = millis();  // Capture the current time
    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;  // Update the last time you performed this action
        int readings[8];
        sensors.getReadings(readings);
        Serial.println();
        for (int i = 0; i < 8; i++) {
            if (readings[i] != -1) {  // Check if the sensor is online
                Serial.print("\t");
                Serial.print("D");
                Serial.print(i);
                Serial.print(" (mm): ");
                Serial.print(readings[i]);
            } else {
                Serial.print("\t");
                Serial.print("D");
                Serial.print(i);
                Serial.print(" (mm): ");
                Serial.print("null");
            }
        }
    }
}
