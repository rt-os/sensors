#include "Sensors.h"

Sensors::Sensors() {
    Wire.begin();
}

int Sensors::begin(int errors) {
    if (!mux.begin()) {  // Call begin without arguments or with correct device address
        Serial.println("Failed to initialize QWIICMUX");
        errors = 1;
        return 0;
    }

    int onlineCount = 0;
    for (int i = 0; i < numSensors; i++) {
        initSensor(i);
        if (sensorOnline[i]) {
            onlineCount++;
        }
    }
    if (onlineCount < 1)  {errors = 2;}
    return onlineCount;
}

void Sensors::initSensor(int channel) {
    mux.setPort(channel);
    if (distanceSensors[channel].begin() == 0) {  // Successfully initialized
        sensorOnline[channel] = true;
        distanceSensors[channel].setIntermeasurementPeriod(25);
        distanceSensors[channel].setDistanceModeLong();
        distanceSensors[channel].startRanging();
    } else {
        sensorOnline[channel] = false;
    }
}

void Sensors::getReadings(int readings[]) {
    for (int i = 0; i < numSensors; i++) {
        if (sensorOnline[i]) {
            mux.setPort(i);
            while (!distanceSensors[i].checkForDataReady()) {
                delay(1);
            }
            readings[i] = distanceSensors[i].getDistance();
            distanceSensors[i].clearInterrupt();
        } else {
            readings[i] = -1; // Sensor offline
        }
    }
}
