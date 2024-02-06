#ifndef SENSORS_H
#define SENSORS_H

#include <Wire.h>
#include <SparkFun_I2C_Mux_Arduino_Library.h>
#include <SparkFun_VL53L1X.h>

class Sensors {
public:
    Sensors();

    int begin(int errors);

    void getReadings(int readings[]);

private:
    static const int numSensors = 8;  // Make numSensors a static constant
    QWIICMUX mux;
    SFEVL53L1X distanceSensors[numSensors];  // Now numSensors is a compile-time constant
    bool sensorOnline[numSensors];
    
    void initSensor(int channel);
};

#endif // SENSORS_H
