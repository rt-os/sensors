import customtkinter
from collections import deque
import csv
from datetime import datetime
import time
import threading
import pytz
import serial
import re

# Define parameters
NUM_SENSORS = 6
REPORT_INTERVAL = 1  # Report interval in seconds
WINDOW_SIZE = 10 * REPORT_INTERVAL  # Window size in seconds
WIDTH, HEIGHT = 1280, 720

# Global variables
LOGGING = False
FILE_PREFIX = ""
FILE_COMMENT = ""
SEQUENCE = []

# An array of NUM_SENSORS, each element is a deque of WINDOW_SIZE
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
mindist = [999999 for _ in range(NUM_SENSORS)]

# Capture multiple sensors per line
pattern = re.compile(r'D(\d)\s*\(mm\):\s*(\d+)')

from serial.tools import list_ports

def find_arduino_port():
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description or "USB" in port.description:
            return port.device
    return None

def mm_to_inches(lengths):
    mm_to_in = 0.0393701
    inches_lengths = []
    for length in lengths:
        # Convert length from millimeters to inches and round to the nearest 1/8 inch
        converted_length = round(length * mm_to_in * 8) / 8
        inches_lengths.append(converted_length)
    return inches_lengths

class sensorBar(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.display_in_inches = False  # Flag to track the display unit
        self.sl0 = customtkinter.CTkLabel(self, text="0:", padx=5)
        self.sv0 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl1 = customtkinter.CTkLabel(self, text="1:", padx=5)
        self.sv1 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl2 = customtkinter.CTkLabel(self, text="2:", padx=5)
        self.sv2 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl3 = customtkinter.CTkLabel(self, text="3:", padx=5)
        self.sv3 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl4 = customtkinter.CTkLabel(self, text="4:", padx=5)
        self.sv4 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl5 = customtkinter.CTkLabel(self, text="5:", padx=5)
        self.sv5 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)

        self.sl0.grid(row=0, column=0, padx=2, pady=3, sticky="w")
        self.sv0.grid(row=0, column=1, padx=2, pady=3, sticky="w")
        self.sl1.grid(row=0, column=2, padx=2, pady=3, sticky="w")
        self.sv1.grid(row=0, column=3, padx=2, pady=3, sticky="w")
        self.sl2.grid(row=0, column=4, padx=2, pady=3, sticky="w")
        self.sv2.grid(row=0, column=5, padx=2, pady=3, sticky="w")
        self.sl3.grid(row=0, column=6, padx=2, pady=3, sticky="w")
        self.sv3.grid(row=0, column=7, padx=2, pady=3, sticky="w")
        self.sl4.grid(row=0, column=8, padx=2, pady=3, sticky="w")
        self.sv4.grid(row=0, column=9, padx=2, pady=3, sticky="w")
        self.sl5.grid(row=0, column=10, padx=2, pady=3, sticky="w")
        self.sv5.grid(row=0, column=11, padx=2, pady=3, sticky="w")

        # Bind click event to toggle conversion
        self.sv0.bind("<Button-1>", self.toggle_conversion)
        self.sv1.bind("<Button-1>", self.toggle_conversion)
        self.sv2.bind("<Button-1>", self.toggle_conversion)
        self.sv3.bind("<Button-1>", self.toggle_conversion)
        self.sv4.bind("<Button-1>", self.toggle_conversion)
        self.sv5.bind("<Button-1>", self.toggle_conversion)

        self.timer_callback()

    def toggle_conversion(self, event=None):
        self.display_in_inches = not self.display_in_inches  # Toggle the flag
        self.update_display()

    def update_display(self):
        global sensor_data

        # Convert and update labels based on the current unit
        if self.display_in_inches:
            converted_data = mm_to_inches([sensor_data[i][0] for i in range(NUM_SENSORS)])
            for i, label in enumerate([self.sv0, self.sv1, self.sv2, self.sv3, self.sv4, self.sv5]):
                label.configure(text=f"{converted_data[i]:.2f} in")
        else:
            for i, label in enumerate([self.sv0, self.sv1, self.sv2, self.sv3, self.sv4, self.sv5]):
                label.configure(text=f"{sensor_data[i][0]} mm")

    def timer_callback(self):
        self.update_display()  # Update display with current unit
        self.after(1000, self.timer_callback)  # Call this method every second

class SideFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master  # Store reference to the parent App instance

        self.sitelbl = customtkinter.CTkLabel(self, text="Site:")
        self.site = customtkinter.CTkEntry(self, placeholder_text="Site")
        self.num_doors_lbl = customtkinter.CTkLabel(self, text="Number of Dock Doors:")
        self.num_doors = customtkinter.CTkOptionMenu(self, values=["1", "2", "3"])
        self.type_lbl = customtkinter.CTkLabel(self, text="Type:")
        self.type = customtkinter.CTkOptionMenu(self, values=["MDF-DH", "DH"])
        self.zone_lbl = customtkinter.CTkLabel(self, text="Zone:")
        self.zone = customtkinter.CTkOptionMenu(self, values=["A", "B", "C", "D"])
        self.set_sequence_btn = customtkinter.CTkButton(self, text="Set Sequence", command=self.set_sequence)
        self.commentl = customtkinter.CTkLabel(self, text="Comment:")
        self.comment = customtkinter.CTkEntry(self, placeholder_text="Comment")
        self.start_stop_btn = customtkinter.CTkButton(self, text="Start/Stop", command=self.start_stop)

        self.sitelbl.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        self.site.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="w")
        self.num_doors_lbl.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        self.num_doors.grid(row=3, column=0, padx=10, pady=(2, 0), sticky="w")
        self.type_lbl.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")
        self.type.grid(row=5, column=0, padx=10, pady=(2, 0), sticky="w")
        self.zone_lbl.grid(row=6, column=0, padx=10, pady=(10, 0), sticky="w")
        self.zone.grid(row=7, column=0, padx=10, pady=(2, 0), sticky="w")
        self.set_sequence_btn.grid(row=8, column=0, padx=10, pady=(10, 0), sticky="w")
        self.commentl.grid(row=9, column=0, padx=10, pady=(10, 0), sticky="w")
        self.comment.grid(row=10, column=0, padx=10, pady=(2, 0), sticky="w")
        self.start_stop_btn.grid(row=11, column=0, padx=10, pady=(10, 0), sticky="w")


    def set_sequence(self):
        global SEQUENCE

        doors = int(self.num_doors.get())
        type_selected = self.type.get()
        zone = self.zone.get()

        SEQUENCE = []

        # Adding doors in ascending order
        for i in range(1, doors + 1):
            SEQUENCE.append(f"Door {i}")

        # Adding MDF-DH or DH with zone
        if type_selected == "MDF-DH":
            SEQUENCE.append(f"MDF-{zone}")
            SEQUENCE.append(f"DH-{zone}")
        else:
            SEQUENCE.append(f"DH-{zone}")

        # Reversing if Zone is A or D
        if zone in ["A", "D"]:
            if type_selected == "MDF-DH":
                SEQUENCE.append(f"DH-{zone}-exit")
                SEQUENCE.append(f"MDF-{zone}-exit")
            else:
                SEQUENCE.append(f"DH-{zone}-exit")

        # Adding doors in descending order
        for i in range(doors, 0, -1):
            SEQUENCE.append(f"Door {i}")

        # Update the output label with the sequence
        self.master.outputlbl.configure(text=" -> ".join(SEQUENCE))
        # Update the sequence display
        self.master.update_sequence_display()

    def start_stop(self):
        global LOGGING, SEQUENCE, FILE_COMMENT, FILE_PREFIX

        if not LOGGING:
            if SEQUENCE:
                # Pop the first element from the sequence
                FILE_COMMENT = SEQUENCE.pop(0)
                FILE_PREFIX = self.site.get().strip() + "_" + FILE_COMMENT
                LOGGING = True
                self.start_stop_btn.configure(text="Stop")
            else:
                self.master.outputlbl.configure(text="No sequence left to process.")  # Use self.master here
        else:
            LOGGING = False
            self.start_stop_btn.configure(text="Start")
            self.master.outputlbl.configure(text="Logging stopped. Remaining sequence: " + " -> ".join(SEQUENCE))
        # Update the sequence display
        self.master.update_sequence_display()


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sensor Logging System")
        self.geometry(f"{WIDTH}x{HEIGHT}")

        # Configure grid for the main window
        self.grid_rowconfigure(0, weight=1)  # Expand outputlbl vertically
        self.grid_rowconfigure(1, weight=0)  # No vertical expansion for sensorBar
        self.grid_columnconfigure(0, weight=0)  # No horizontal expansion for side_frame
        self.grid_columnconfigure(1, weight=0)  # No horizontal expansion for sequence_label
        self.grid_columnconfigure(2, weight=1)  # Expand outputlbl horizontally

        # Create SideFrame on the left
        self.side_frame = SideFrame(self)
        self.side_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="ns")

        # Create sequence_label for the sequence in the middle
        self.sequence_label = customtkinter.CTkLabel(self, text="Sequence", justify="left", fg_color="slategrey", corner_radius=10, anchor="w")
        self.sequence_label.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Create outputlbl on the right, occupying all expandable space
        self.outputlbl = customtkinter.CTkLabel(self, text="Sequence will be displayed here", fg_color="dimgray", corner_radius=10)
        self.outputlbl.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")  # Expand in all directions

        # Create sensorBar below outputlbl
        self.sensor_bar = sensorBar(self)
        self.sensor_bar.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")  # Expand horizontally

    def update_sequence_display(self):
        """Updates the sequence display with the current sequence steps."""
        global SEQUENCE, FILE_COMMENT, LOGGING

        # Prepare text for sequence_label
        sequence_text = ""
        for step in SEQUENCE:
            if LOGGING and step == FILE_COMMENT:
                # Highlight the current step if logging is active
                sequence_text += f"**{step}**\n"
            else:
                sequence_text += f"{step}\n"

        # Update the sequence label text
        self.sequence_label.configure(text=sequence_text)


def capture_data(sensor_id, value):
    sensor_data[sensor_id].append(value)
    mindist[sensor_id] = min(mindist[sensor_id], value)

def gen_file_name(type):
    global FILE_PREFIX
    pst = datetime.now(pytz.timezone('America/Los_Angeles'))
    fn = pst.strftime("%Y%m%d_%H%M%S")
    return fn + FILE_PREFIX + ".csv"

def serial_reader(ser):
    global sensor_data, LOGGING, FILE_PREFIX
    logging_running = False
    writer = None
    log_file = None
    fn = ""
    while True:
        if LOGGING:
            if not logging_running:
                logging_running = True
                fn = gen_file_name(0)
                log_file = open(fn, 'w', newline='')
                writer = csv.writer(log_file)
                writer.writerow(['Timestamp (PST)', 'Sensor Number', 'Measurement'])
        else:
            if logging_running:
                logging_running = False
                if log_file:
                    log_file.close()
                    fn = ""
        try:
            line = ser.readline().decode('utf-8').strip()
            matches = re.findall(pattern, line)
            utc_now = datetime.fromtimestamp(time.time(), pytz.utc)
            timestamp = int(utc_now.astimezone(pytz.timezone('US/Pacific')).timestamp() * 1000)
            for hit in matches:
                sensor_id = int(hit[0])
                data_value = int(hit[1])
                if 0 <= sensor_id < len(sensor_data):
                    capture_data(sensor_id, data_value)
                    if logging_running:
                        writer.writerow([timestamp, sensor_id, data_value])
        except UnicodeDecodeError:
            print("Error decoding byte sequence from serial port")

def main():
    ser = serial.Serial(find_arduino_port(), 115200)
    serial_thread = threading.Thread(target=serial_reader, args=(ser,), daemon=True)
    serial_thread.start()
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
