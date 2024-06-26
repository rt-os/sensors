import serial
import re
import time
import sys
from collections import deque
from datetime import datetime, timedelta
import pytz
import csv

# Define parameters
NUM_SENSORS = 6
REPORT_INTERVAL = 1  # Report interval in seconds
WINDOW_SIZE = 10 * REPORT_INTERVAL  # Window size in seconds

# Global variables
LOGGING = False

# an array of NUM_SENSORS, each element is a deque of WINDOW_SIZE
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
mindist = [999999 for _ in range(NUM_SENSORS)]


from serial.tools import list_ports
def find_arduino_port():
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description:
            return port.device
    return None

def capture_data(sensor_id, value):
    sensor_data[sensor_id].append(value)
    mindist[sensor_id] = min(mindist[sensor_id], value)

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
                    pattern = re.compile(r'D(\d)\s*\(mm\):\s*(\d+)')
                    # match = re.match(r'(\d+)\s*D(\d)\s*\(mm\):\s+(\d+)', line)
                    matches = re.findall(pattern, line)
                    timestamp = int(time.time() * 1000)
                    # print(match)
                    for hit in matches:
                        # logger.debug("Index:", hit[0], "Measurement:", hit[1])
                        sensor_id = int(hit[0])
                        data_value = int(hit[1])
                        if 0 <= sensor_id < len(sensor_data):
                            capture_data(sensor_id, data_value)
                            writer.writerow([timestamp, sensor_id, data_value])

            except Exception as e:
                print(f"Error: {e}")

    return readings

def main():
    port = find_arduino_port()
    if port is None:
        print("Arduino not found. Please check your connection.")
        return

    duration = 1
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
