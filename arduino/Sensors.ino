#include "Sensors.h"

Sensors::Sensors() {
    Wire.begin();
}

int Sensors::begin(int &errors) {
    if (!mux.begin()) {
        #ifdef DEBUG
        Serial.println("Failed to initialize QWIICMUX");
        #endif
        errors = 1;
        return 0;
    }

    int onlineCount = 0;
    for (int i = 0; i < numSensors; i++) {
        initSensor(i);
        if (sensorOnline[i]) {
            onlineCount++;
            #ifdef DEBUG
            Serial.print("Sensor ");
            Serial.print(i);
            Serial.println(" initialized and online.");
            #endif
        } else {
            #ifdef DEBUG
            Serial.print("Sensor ");
            Serial.print(i);
            Serial.println(" failed to initialize.");
            #endif
        }
        previousOnlineState[i] = sensorOnline[i];
    }

    if (onlineCount < 1) {
        errors = 2;
    }
    return onlineCount;
}

void Sensors::initSensor(int channel) {
    mux.setPort(channel);

    if (distanceSensors[channel].begin() == 0) {
        sensorOnline[channel] = true;
        distanceSensors[channel].setTimingBudgetInMs(50);
        distanceSensors[channel].setIntermeasurementPeriod(100);
        distanceSensors[channel].setDistanceModeLong();
        distanceSensors[channel].startRanging();
        #ifdef DEBUG
        Serial.print("Sensor ");
        Serial.print(channel);
        Serial.println(" started ranging.");
        #endif
    } else {
        sensorOnline[channel] = false;
        #ifdef DEBUG
        Serial.print("Sensor ");
        Serial.print(channel);
        Serial.println(" failed to start ranging.");
        #endif
    }
}

void Sensors::getReadings(int readings[]) {
    for (int i = 0; i < numSensors; i++) {
        if (sensorOnline[i]) {
            mux.setPort(i);

            if (distanceSensors[i].checkForDataReady()) {
                readings[i] = distanceSensors[i].getDistance();
                distanceSensors[i].clearInterrupt();
                failureCount[i] = 0;  // Reset failure count on successful read
                #ifdef DEBUG
                Serial.print("Sensor ");
                Serial.print(i);
                Serial.print(" reading: ");
                Serial.println(readings[i]);
                #endif
            } else {
                readings[i] = -1;
                failureCount[i]++;

                if (failureCount[i] >= failureThreshold) {
                    sensorOnline[i] = false;
                    lastOfflineTime[i] = millis();
                    #ifdef DEBUG
                    Serial.print("Sensor ");
                    Serial.print(i);
                    Serial.println(" marked offline due to repeated failures.");
                    #endif
                }
            }
        } else {
            readings[i] = -1;
        }
    }
}

void Sensors::reinitializeOfflineSensors() {
    for (int i = 0; i < numSensors; i++) {
        if (previousOnlineState[i] && !sensorOnline[i]) {
            if (millis() - lastOfflineTime[i] >= reinitInterval) {
                #ifdef DEBUG
                Serial.print("Attempting to reinitialize sensor ");
                Serial.println(i);
                #endif

                initSensor(i);

                if (sensorOnline[i]) {
                    #ifdef DEBUG
                    Serial.print("Sensor ");
                    Serial.print(i);
                    Serial.println(" reinitialized successfully.");
                    #endif
                    failureCount[i] = 0;  // Reset failure count after successful reinitialization
                } else {
                    #ifdef DEBUG
                    Serial.print("Sensor ");
                    Serial.print(i);
                    Serial.println(" reinitialization failed.");
                    #endif
                }
            }
        }
    }
}
