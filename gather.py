import serial
import re
import time
import sys
from datetime import datetime, timedelta
import pytz
import csv

from serial.tools import list_ports
def find_arduino_port():
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description:
            return port.device
    return None

def log_sensor_readings(ser, duration, csv_filename):
    start_time = time.time()
    readings = {}
    first_reading_time = None
    pst_timezone = pytz.timezone('America/Los_Angeles')

    with open(csv_filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp (PST)', 'Sensor Number', 'Measurement'])

        while time.time() - start_time < duration * 60:  # Convert minutes to seconds
            try:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    print(line)
                    # Updated regex pattern for integer measurements in mm
                    match = re.match(r'(\d+)\s*D(\d)\s*\(mm\):\s+(\d+)', line)
                    print(match)
                    if match:
                        arduino_millis, sensor, reading = int(match.group(1)), match.group(2), int(match.group(3))
                        readings[sensor] = min(readings.get(sensor, float('inf')), reading)

                        # Set first reading time as base time
                        if first_reading_time is None:
                            first_reading_time = datetime.now(pst_timezone) - timedelta(milliseconds=arduino_millis)

                        # Calculate the actual timestamp
                        actual_timestamp = first_reading_time + timedelta(milliseconds=arduino_millis)
                        timestamp = actual_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Truncate microseconds to milliseconds

                        writer.writerow([timestamp, sensor, reading])
            except Exception as e:
                print(f"Error: {e}")

    return readings

def main():
    port = find_arduino_port()
    if port is None:
        print("Arduino not found. Please check your connection.")
        return

    duration = 5
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Invalid duration. Using default 5 minutes.")

    pst = datetime.now(pytz.timezone('America/Los_Angeles'))
    csv_filename = pst.strftime("%Y%m%d_%H%M%S.csv")

    ser = serial.Serial(port, 115200, timeout=1)

    readings = log_sensor_readings(ser, duration, csv_filename)

    ser.close()

    # Display the lowest reading for each sensor
    if readings:
        for sensor in sorted(readings.keys()):
            lowest_reading = readings[sensor]
            print(f"Lowest reading for sensor {sensor}: {lowest_reading}")

    # Display the filename of the CSV
    print(f"Data logged in: {csv_filename}")

if __name__ == "__main__":
    main()
