# Sensors project #
## setup ##
* first run the setuppython.bat this will enable a virtual env with python 3.10 and all needed libraries
* After first time from this folder run .\310\Scripts\activate
* then run: "python gather.py" or "python3 gather.py" to create the CSV
* run python or python3 plot.py <csv file> to produce the graph of that time
  

## Arduino programming
* install arduino ide
* open arduino folder project in the arduino ide
* add the libraries:
* * SparkFun_I2C_Mux_Arduino_Library
* * SparkFun_VL53L1X_4m_Laser_Distance_Sensor
* set arduno to the Uno board and whatever com port is active
* upload
