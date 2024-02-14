from collections import deque
import csv
from datetime import datetime
import time
import threading
import pytz
import serial
import re
from fractions import Fraction
import cv2
import numpy as np

# Define parameters
NUM_SENSORS = 6
REPORT_INTERVAL = 1  # Report interval in seconds
WINDOW_SIZE = 10 * REPORT_INTERVAL  # Window size in seconds

# Global variables
LOGGING = False
# an array of NUM_SENSORS, each element is a deque of WINDOW_SIZE
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]

# Regular expression pattern for parsing serial data old: r'(\d+)\s*D(\d)\s*\(mm\):\s+(\d+)'
# group1 optional timestamp, group2 sensor number group3 distance in mm
pattern = re.compile(r'(?:(\d+)\s*)?D(\d)\s*\(mm\):\s+(\d+)')

from serial.tools import list_ports
def find_arduino_port():
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description:
            return port.device
    return None

def overlay_images(background, overlay, ovrxy):
    x = ovrxy[0]
    y = ovrxy[1]
    alpha_channel = overlay[:, :, 3]
    overlay_rgb = overlay[:, :, :3]
    overlay_height, overlay_width = overlay_rgb.shape[:2]
    roi = background[y:y+overlay_height, x:x+overlay_width]
    mask = np.zeros_like(alpha_channel)
    mask.fill(255)
    mask[alpha_channel == 0] = 0
    inverted_mask = cv2.bitwise_not(mask)
    overlay_rgb = overlay_rgb.astype(float)
    background_roi = roi.astype(float)
    background_roi = cv2.bitwise_and(background_roi, background_roi, mask=inverted_mask)
    overlay_rgb = cv2.bitwise_and(overlay_rgb, overlay_rgb, mask=mask)
    combined = cv2.add(background_roi, overlay_rgb)
    background[y:y+overlay_height, x:x+overlay_width] = combined.astype(np.uint8)
    return background

def mm_to_inches(lengths):
    mm_to_in = 0.0393701
    inches_lengths = []
    for length in lengths:
        # Convert length from millimeters to inches and round to the nearest 1/8 inch
        converted_length = round(length * mm_to_in * 8) / 8
        inches_lengths.append(converted_length)
    return inches_lengths

def fix_numbers(input_array):
    fixed_array = ""
    for item in input_array:
        whole = int(item)
        frac = Fraction(item - whole).limit_denominator(8)
        fixed_array += str(whole) + " " + str(frac) + ", "
    return fixed_array

def add_tuple(a, b):
    return tuple(map(lambda i, j: i+j, a, b))

def capture_data(sensor_id, value):
    # print(f"Capturing data for sensor {sensor_id}: {value}")
    sensor_data[sensor_id].append(value)

def calculate_lowest_readings():
    lowest_readings = []
    for data_queue in sensor_data:
        lowest_reading = min(data_queue) if data_queue else float('inf')
        lowest_readings.append(lowest_reading)
    return lowest_readings

def calculate_avg_readings():
    lowest_readings = []
    for data_queue in sensor_data:
        lowest_reading = sum(data_queue) / len(data_queue)
        lowest_readings.append(lowest_reading)
    return lowest_readings

def gen_file_name():
    start_time = time.time()
    pst = datetime.now(pytz.timezone('America/Los_Angeles'))
    return pst.strftime("%Y%m%d_%H%M%S.csv")

def serial_reader(ser):
    global sensor_data, LOGGING
    logging_running = False
    writer = {}
    log_file = {}
    fn = ""
    while True:
        if LOGGING:
            if logging_running:
                pass
            else:
                logging_running = True
                fn = gen_file_name()
                log_file = open(fn, 'w', newline='')
                print(f"starting: {fn}")
                writer = csv.writer(log_file)
                writer.writerow(['milliseconds (PST)', 'Sensor Number', 'Measurement'])
        else:
            if logging_running:
                logging_running = False
                print(f"saved: {fn}")
                log_file.close()
                fn = ""
            else:
                pass
        try:
            line = ser.readline().decode('utf-8').strip()
            match = pattern.match(line)
            if match:
                sensor_id = int(match.group(2))
                data_value = int(match.group(3))
                timestamp = int(time.time() * 1000)

                if 0 <= sensor_id < len(sensor_data):
                    capture_data(sensor_id, data_value)
                    if logging_running:
                        writer.writerow([timestamp, match.group(2), match.group(3)])
            elif line.startswith('Online sensors:'):
                num_sensors = int(line.split(':')[1].strip())
                # Ensure the number of online sensors doesn't exceed NUM_SENSORS
                num_sensors = min(num_sensors, NUM_SENSORS)
                sensor_data = [deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(num_sensors)]
        except UnicodeDecodeError:
            print("Error decoding byte sequence from serial port")

def draw_label(img, text, posx, color):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.8
    thickness = cv2.FILLED
    margin = 2
    for t in enumerate(text.split(',')):
        textln = t[1].strip()
        dy = (t[0]*25) + 50
        pos_fin = (posx,dy)
        cv2.putText(img, textln, pos_fin, font_face, scale, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, textln, pos_fin, font_face, scale, color, 1, cv2.LINE_AA)
def draw_sensor(img, text, pos, space, color):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.8
    thickness = cv2.FILLED
    margin = 2
    dx = pos[0]
    dy = pos[1]
    for t in enumerate(text.split(',')):
        indx = t[0]
        if indx % 2:
            indx=indx-1
            dpx=dx+270
        else:
            dpx=dx
        textln = t[1].strip()
        dpy = (indx*space) + dy
        # print(f"{t[0]}- ({dpx},{dpy})")
        cv2.putText(img, textln, (dpx,dpy), font_face, scale, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, textln, (dpx,dpy), font_face, scale, color, 1, cv2.LINE_AA)


def show_webcam(overlay, overxy, space, mirror=False):
    global LOGGING
    cam = cv2.VideoCapture(1)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # Check if camera opened successfully
    if (cam.isOpened()== False):
        print("Error opening video stream or file")
    # Read until video is completed
    while(cam.isOpened()):
        # Capture frame-by-frame
        ret, frame = cam.read()
        if ret == True:
            if mirror:
                frame = cv2.flip(frame, 1)
            # add the visual overlay
            overlay_images(frame, overlay, overxy)
            textoffset = add_tuple(overxy, (-100, 25))
            # draw sensors to frame
            draw_sensor(frame, fix_numbers(mm_to_inches(calculate_lowest_readings())), textoffset, space, (255,255,0))
            draw_label(frame, fix_numbers(mm_to_inches(calculate_avg_readings())), 200, (255,255,0))
            # Display the resulting frame
            cv2.imshow('Frame',frame)
            # Press esc on keyboard to  exit
            if cv2.waitKey(1) == 27:
                break
            if cv2.waitKey(1) == ord('a'):
                LOGGING = not LOGGING
        else:
            break
    # When everything done, release the video capture object
    cam.release()
    # Closes all the frames
    cv2.destroyAllWindows()

def main():
    # Open serial port
    ser = serial.Serial(find_arduino_port(), 115200)

    # Start the serial reader thread
    serial_thread = threading.Thread(target=serial_reader, args=(ser,), daemon=True)
    serial_thread.start()

    # Main loop
    overlay = cv2.imread('frame.png', cv2.IMREAD_UNCHANGED)
    show_webcam(overlay, (300,300), 61, mirror=True)

if __name__ == "__main__":
    main()
