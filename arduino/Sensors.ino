#include "Sensors.h"

extern Logger logger;

Sensors::Sensors() {
    Wire.begin();
}

int Sensors::begin() {
    if (!mux.begin()) {
        logger.error("Failed to initialize QWIICMUX.");
        return 0;
    }

    int onlineCount = 0;
    for (int i = 0; i < numSensors; i++) {
        initSensor(i);
        if (sensorOnline[i]) onlineCount++;
    }

    return onlineCount;
}

void Sensors::initSensor(int channel) {
    mux.setPort(channel);
    if (distanceSensors[channel].begin() == 0) {
        distanceSensors[channel].setTimingBudgetInMs(50);
        distanceSensors[channel].setIntermeasurementPeriod(100);
        distanceSensors[channel].setDistanceModeLong();
        distanceSensors[channel].startRanging();
        sensorOnline[channel] = true;
    } else {
        sensorOnline[channel] = false;
    }
}

void Sensors::logReadings() {
    String line;
    for (int i = 0; i < numSensors; i++) {
        if (sensorOnline[i]) {
            mux.setPort(i);
            if (distanceSensors[i].checkForDataReady()) {
                int distance = distanceSensors[i].getDistance();
                distanceSensors[i].clearInterrupt();
                line += "D" + String(i) + " (mm): " + String(distance) + " ";
                failureCount[i] = 0;
            } else {
                line += "D" + String(i) + " (mm): null ";
                if (++failureCount[i] >= failureThreshold) {
                    sensorOnline[i] = false;
                }
            }
        } else {
            line += "D" + String(i) + " (mm): null ";
        }
    }
    line.trim(); // Remove trailing space
    logger.mainOutput(line);
}

void Sensors::reinitializeOfflineSensors() {
    for (int i = 0; i < numSensors; i++) {
        if (!sensorOnline[i] && millis() - lastOfflineTime[i] >= 5000) {
            initSensor(i);
        }
    }
}
