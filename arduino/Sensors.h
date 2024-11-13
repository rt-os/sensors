#ifndef SENSORS_H
#define SENSORS_H

// #define DEBUG  // Comment out or remove this line to disable debug messages

#include <Wire.h>
#include <SparkFun_I2C_Mux_Arduino_Library.h>
#include <SparkFun_VL53L1X.h>

class Sensors {
public:
    Sensors();
    int begin(int &errors);
    void getReadings(int readings[]);
    void reinitializeOfflineSensors();

private:
    void initSensor(int channel);
    static const int numSensors = 8;  // Make numSensors a static constant
    QWIICMUX mux;
    SFEVL53L1X distanceSensors[numSensors];  // Now numSensors is a compile-time constant
    bool sensorOnline[numSensors];
    bool previousOnlineState[numSensors];  // Track initial state
    unsigned long lastOfflineTime[numSensors] = {0}; // Last offline timestamp for each sensor
    int failureCount[numSensors] = {0};  // Count of failures to trigger reinitialization
    const int failureThreshold = 3;  // Number of consecutive failures before forcing reinitialization

};

#endif // SENSORS_H
