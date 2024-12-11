// Main Arduino Code
#include "Sensors.h"
#include "Logger.h"

Logger logger;
Sensors sensors;
unsigned long previousMillis = 0;
unsigned long reinitMillis = 0;
const long interval = 125;          // Reading interval (in milliseconds)
const long reinitInterval = 5000;   // Reinitialize offline sensors every 5 seconds

void setup() {
    Serial.begin(115200);
    logger.setLogLevel(1);
    int onlineSensors = sensors.begin();
    Serial.println("Online sensors: " + String(onlineSensors));
}

void loop() {
    unsigned long currentMillis = millis();

    // Read sensors
    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;
        sensors.logReadings();
    }

    // Reinitialize offline sensors
    if (currentMillis - reinitMillis >= reinitInterval) {
        reinitMillis = currentMillis;
        sensors.reinitializeOfflineSensors();
    }
}
