import sys
import re
import threading
import time
import csv
import serial
from collections import deque
from datetime import datetime
import pytz
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QCheckBox, QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import QTimer, Qt, QObject, QEvent

# Define parameters
NUM_SENSORS = 4
REPORT_INTERVAL = 1  # Report interval in seconds
WINDOW_SIZE = 10 * REPORT_INTERVAL  # Window size in seconds

# Global variables
LOGGING = False
SEQUENCE = []
current_step_index = 0
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
mindist = [999999 for _ in range(NUM_SENSORS)]
pattern = re.compile(r'D(\d)\s*\(mm\):\s*(\d+)')
building_code = ""
current_step = None  # Initialize current_step globally

# Capture multiple sensors per line
def find_arduino_port():
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description or "USB" in port.description:
            return port.device
    return None

def mm_to_inches(lengths):
    mm_to_in = 0.0393701
    inches_lengths = []
    for length in lengths:
        converted_length = round(length * mm_to_in * 8) / 8
        inches_lengths.append(converted_length)
    return inches_lengths

def capture_data(sensor_id, value):
    sensor_data[sensor_id].append(value)
    mindist[sensor_id] = min(mindist[sensor_id], value)

# def gen_file_name(self, step):
#     """Generates a file name based on the current sequence step, building code, and selected radio option."""
#     global building_code
#     selected_radio = self.radio_group.checkedButton().text()  # Get the selected radio button value
#     pst = datetime.now(pytz.timezone('America/Los_Angeles'))
#     fn = pst.strftime("%Y%m%d_%H%M%S")
#     return f"{fn}_{building_code}{selected_radio}_{step}.csv"

def serial_reader(ser, main_window):
    global sensor_data, LOGGING, current_step
    logging_running = False
    writer = None
    log_file = None

    while True:
        if LOGGING and current_step:
            if not logging_running:
                logging_running = True
                fn = main_window.gen_file_name(current_step)  # Access the method from main_window
                log_file = open(fn, 'w', newline='')
                writer = csv.writer(log_file)
                writer.writerow(['Timestamp (PST)', 'Sensor Number', 'Measurement'])
                print(f"Opened file: {fn}")
        else:
            if logging_running:
                logging_running = False
                if log_file:
                    log_file.close()
                    print(f"Closed file: {fn}")
                
                # After the last file, reset current_step and stop logging
                if not SEQUENCE and current_step:
                    current_step = None  # Ensure logging stops once sequence is exhausted
                    print("No sequence set.")
                    LOGGING = False

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
                    if logging_running and writer:
                        writer.writerow([timestamp, sensor_id, data_value])
        except UnicodeDecodeError:
            print("Error decoding byte sequence from serial port")

class EventFilter(QObject):
    """An event filter to capture spacebar key events globally"""
    def eventFilter(self, obj, event):
        global LOGGING, SEQUENCE, current_step

        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Space:
            if SEQUENCE or current_step:
                if LOGGING:
                    LOGGING = False
                    obj.text_output.append("Logging stopped and file closed.")
                    current_step = None  # Reset current_step after logging is stopped
                else:
                    if current_step is None and SEQUENCE:
                        # Pop the first step from the sequence each time logging starts
                        current_step = SEQUENCE.pop(0)
                    
                    if current_step:
                        LOGGING = True
                        filename = obj.gen_file_name(current_step)  # Call with 'obj' to access class instance
                        obj.text_output.append(f"Logging started. Opened file: {filename}")
                    else:
                        obj.text_output.append("No sequence set.")
                        LOGGING = False
            else:
                obj.text_output.append("No sequence set.")
            return True
        return super().eventFilter(obj, event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sensors")
        self.setGeometry(100, 100, 800, 600)

        # Flag to track whether we are showing inches or millimeters
        self.display_in_inches = False

        # Create central widget and set layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create the main layout as a vertical box layout
        main_layout = QVBoxLayout(central_widget)

        # Split the layout into two main parts: top and bottom
        top_layout = QHBoxLayout()  # Top part contains the left panel and text output
        bottom_panel = self.create_bottom_panel()  # Bottom panel

        # Add top layout and bottom panel to the main layout
        main_layout.addLayout(top_layout)
        main_layout.addWidget(bottom_panel)

        # Add left docked panel and text output area to top_layout
        left_panel = self.create_left_panel()  # Store as an instance attribute to access later
        self.text_output = self.create_text_output()

        top_layout.addWidget(left_panel)
        top_layout.addWidget(self.text_output, 1)  # Text output should take the remaining space

        # Timer to update sensor values every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_values)
        self.timer.start(1000)  # Update every second

        # Install event filter to capture global spacebar press
        self.event_filter = EventFilter()
        self.installEventFilter(self.event_filter)

    def create_left_panel(self):
        """Creates the left panel with a building input, dynamic checkboxes, radio buttons, and a button"""
        left_panel = QFrame(self)
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setFixedWidth(200)

        layout = QVBoxLayout(left_panel)

        # Add building input field
        self.building_input = QLineEdit(self)
        self.building_input.setPlaceholderText("Building Code")
        layout.addWidget(QLabel("Building"))
        layout.addWidget(self.building_input)

        # Add radio button group for A, B, C, D selection
        radio_layout = QHBoxLayout()
        self.radio_group = QButtonGroup(self)

        # Create radio buttons for A, B, C, D
        radio_options = ["A", "B", "C", "D"]
        for option in radio_options:
            radio_button = QRadioButton(option, self)
            self.radio_group.addButton(radio_button)
            radio_layout.addWidget(radio_button)

        # Select "A" by default
        self.radio_group.buttons()[0].setChecked(True)

        layout.addLayout(radio_layout)

        # Define the dynamic checkbox options
        self.checkbox_options = ["Dock-inner", "Middle", "Dock-outer", "Hallway", "MDFIn", "DH-in", "DH-return", "MDF-return", "Hallway-return", "Dock-outer-return", "middle-return", "Dock-inner-return"]  # Add more options here as needed

        # Create checkboxes dynamically based on the list of options
        self.checkboxes = []
        for option in self.checkbox_options:
            checkbox = QCheckBox(option, self)
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)  # Store checkboxes in a list

        # Add the Set Sequence button
        set_sequence_button = QPushButton("Set Sequence", self)
        set_sequence_button.clicked.connect(self.set_sequence)  # Connect button click to function

        layout.addWidget(set_sequence_button)
        layout.addStretch(1)  # Add stretch to push elements up

        return left_panel

    def create_text_output(self):
        """Creates the central text output area"""
        text_output = QTextEdit(self)
        text_output.setReadOnly(True)
        text_output.setText("Text output will be displayed here.")
        return text_output

    def create_bottom_panel(self):
        """Creates the bottom panel that contains four text boxes for sensor values"""
        bottom_panel = QFrame(self)
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        bottom_panel.setFixedHeight(50)  # Fixed height for the bottom panel

        layout = QHBoxLayout(bottom_panel)

        # Create sensor value labels and text boxes
        self.sensor_labels = []
        self.sensor_boxes = []
        for i in range(NUM_SENSORS):
            label = QLabel(f"{i}: ", self)
            sensor_box = QLineEdit(self)
            sensor_box.setReadOnly(True)
            sensor_box.mousePressEvent = lambda event, index=i: self.toggle_units()  # Attach toggle behavior
            self.sensor_labels.append(label)
            self.sensor_boxes.append(sensor_box)
            layout.addWidget(label)
            layout.addWidget(sensor_box)

        return bottom_panel

    def update_sensor_values(self):
        """Updates the sensor values in the text boxes"""
        for i in range(NUM_SENSORS):
            mm_value = sensor_data[i][0]
            if self.display_in_inches:
                inches_value = mm_to_inches([mm_value])[0]
                self.sensor_boxes[i].setText(f"{inches_value:.2f} in")
            else:
                self.sensor_boxes[i].setText(f"{mm_value} mm")

    def gen_file_name(self, step):
        """Generates a file name based on the current sequence step, building code, and selected radio option."""
        global building_code
        selected_radio = self.radio_group.checkedButton().text()  # Get the selected radio button value
        pst = datetime.now(pytz.timezone('America/Los_Angeles'))
        fn = pst.strftime("%Y%m%d_%H%M%S")
        return f"{fn}_{building_code}{selected_radio}_{step}.csv"

    def toggle_units(self):
        """Toggles the display between millimeters and inches"""
        self.display_in_inches = not self.display_in_inches
        self.update_sensor_values()  # Immediately update to reflect the toggled unit

    def convert_to_inches(self, index):
        """Converts the mm value to inches for the clicked sensor text box"""
        mm_value = sensor_data[index][0]
        inches_value = mm_to_inches([mm_value])[0]
        self.sensor_boxes[index].setText(f"{inches_value:.2f} in")

    def validate_building_code(self):
        """Validate the building code input (three letters followed by one number)"""
        global building_code
        text = self.building_input.text()
        if re.fullmatch(r'[A-Za-z]{3}[0-9]', text):
            building_code = text
            return True
        else:
            building_code = ""
            return False

    def set_sequence(self):
        """Collects the checked options and stores them in the SEQUENCE global variable"""
        global SEQUENCE, current_step_index

        # Validate the building code before setting the sequence
        if not self.validate_building_code():
            QMessageBox.warning(self, "Invalid Input", "Building code must be 3 letters followed by 1 number.")
            return

        SEQUENCE = []  # Clear the sequence
        current_step_index = 0  # Reset to the first step

        # Loop through the checkboxes and check if they are selected
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                SEQUENCE.append(checkbox.text())

        # Print the sequence in the text output area
        if SEQUENCE:
            sequence_text = " -> ".join(SEQUENCE)
        else:
            sequence_text = "No options selected."
        
        self.text_output.append(f"Sequence: {sequence_text}")


def main():
    # Start the serial reader in a background thread
    ser = serial.Serial(find_arduino_port(), 115200)
    
    # Create and run the Qt application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Pass the MainWindow instance to the serial reader
    serial_thread = threading.Thread(target=serial_reader, args=(ser, window), daemon=True)
    serial_thread.start()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()