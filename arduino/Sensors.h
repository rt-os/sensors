#ifndef SENSORS_H
#define SENSORS_H

#include <Wire.h>
#include <SparkFun_I2C_Mux_Arduino_Library.h>
#include <SparkFun_VL53L1X.h>
#include "Logger.h"

class Sensors {
public:
    Sensors();
    int begin();
    void logReadings();
    void reinitializeOfflineSensors();

private:
    static const int numSensors = 8;
    QWIICMUX mux;
    SFEVL53L1X distanceSensors[numSensors];
    bool sensorOnline[numSensors];
    unsigned long lastOfflineTime[numSensors] = {0};
    const int failureThreshold = 3;
    int failureCount[numSensors] = {0};

    void initSensor(int channel);
};

#endif