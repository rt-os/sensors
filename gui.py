import sys
import re
import threading
import time
import csv
import serial
import yaml
from collections import deque
from datetime import datetime
import pytz
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QCheckBox, QPushButton, QTextEdit, QLabel, QLineEdit, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import QTimer, Qt, QObject, QEvent

# Define parameters
NUM_SENSORS = 4
REPORT_INTERVAL = 1  # Report interval in seconds
WINDOW_SIZE = 10 * REPORT_INTERVAL  # Window size in seconds

# Global variables
LOGGING = False
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
mindist = [999999 for _ in range(NUM_SENSORS)]
pattern = re.compile(r'D(\d)\s*\(mm\):\s*(\d+)')
building_code = ""
SEQUENCE = []
current_step = None
current_step_index = 0

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

def serial_reader(ser, main_window):
    global sensor_data, LOGGING, current_step
    logging_running = False
    writer = None
    log_file = None

    while True:
        if LOGGING and current_step:
            if not logging_running:
                logging_running = True
                fn = main_window.gen_file_name(current_step)
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
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Space:
            obj.start_stop_logging()
            return True
        return super().eventFilter(obj, event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load door_list from config.yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        self.checkbox_options = config.get('door_list', [])

        self.setWindowTitle("Sensors")
        self.setGeometry(100, 100, 800, 600)
        self.display_in_inches = False
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        top_layout = QHBoxLayout()
        bottom_panel = self.create_bottom_panel()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(bottom_panel)
        left_panel = self.create_left_panel()
        self.text_output = self.create_text_output()
        top_layout.addWidget(left_panel)
        top_layout.addWidget(self.text_output, 1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensor_values)
        self.timer.start(500)
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
        # Add radio button group
        radio_layout = QHBoxLayout()
        self.radio_group = QButtonGroup(self)
        radio_options = ["A", "B", "C", "D"]
        for option in radio_options:
            radio_button = QRadioButton(option, self)
            self.radio_group.addButton(radio_button)
            radio_layout.addWidget(radio_button)
        # Select "A" by default
        self.radio_group.buttons()[0].setChecked(True)
        layout.addLayout(radio_layout)
        # Define the dynamic door selector
        self.checkboxes = []
        for option in self.checkbox_options:
            checkbox = QCheckBox(option, self)
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)
        # Set Sequence button
        set_sequence_button = QPushButton("Set Sequence", self)
        set_sequence_button.clicked.connect(self.set_sequence)
        layout.addWidget(set_sequence_button)
        layout.addStretch(1)
        return left_panel

    def create_text_output(self):
        """Creates the central text output area"""
        text_output = QTextEdit(self)
        text_output.setReadOnly(True)
        text_output.setText("")
        return text_output

    def create_bottom_panel(self):
        """Creates the bottom panel that contains sensor readings and a Start/Stop button"""
        bottom_panel = QFrame(self)
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(bottom_panel)
        # Create sensor value labels and text boxes
        sensor_layout = QHBoxLayout()
        self.sensor_labels = []
        self.sensor_boxes = []
        for i in range(NUM_SENSORS):
            label = QLabel(f"{i}: ", self)
            sensor_box = QLineEdit(self)
            sensor_box.setReadOnly(True)
            sensor_box.mousePressEvent = lambda event, index=i: self.toggle_units()  # Attach toggle behavior
            self.sensor_labels.append(label)
            self.sensor_boxes.append(sensor_box)
            sensor_layout.addWidget(label)
            sensor_layout.addWidget(sensor_box)
        layout.addLayout(sensor_layout)
        # Add Start/Stop button
        self.start_stop_button = QPushButton("Start", self)
        self.start_stop_button.clicked.connect(self.toggle_logging)
        layout.addWidget(self.start_stop_button)
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
        selected_radio = self.radio_group.checkedButton().text()  # Get the selected radio button value
        pst = datetime.now(pytz.timezone('America/Los_Angeles'))
        fn = pst.strftime("%Y%m%d_%H%M%S")
        building_code = self.building_input.text()
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

    def set_sequence(self):
        """Collects the checked options and stores them in the SEQUENCE global variable"""
        global SEQUENCE, current_step_index
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

    def start_stop_logging(self):
        """Handles the start/stop logic for logging data"""
        global LOGGING, SEQUENCE, current_step

        if SEQUENCE or current_step:
            if LOGGING:
                LOGGING = False
                self.text_output.append("Logging stopped and file closed.")
                self.start_stop_button.setText("Start")
                current_step = None
            else:
                if current_step is None and SEQUENCE:
                    # Pop the first step from the sequence each time logging starts
                    current_step = SEQUENCE.pop(0)
                if current_step:
                    LOGGING = True
                    filename = self.gen_file_name(current_step)
                    self.text_output.append(f"Logging started. Opened file: {filename}")
                    self.start_stop_button.setText("Stop")
                else:
                    self.text_output.append("No sequence set.")
                    LOGGING = False
        else:
            self.text_output.append("No sequence set.")

    def toggle_logging(self):
        """Toggles logging when the Start/Stop button is pressed"""
        self.start_stop_logging()

def apply_monokai_theme(app):
    dark_stylesheet = """
    QMainWindow {
        background-color: #272822;
        color: #F8F8F2;
    }
    
    QWidget {
        background-color: #272822;
        color: #F8F8F2;
    }
    
    QLineEdit, QTextEdit, QFrame {
        background-color: #272822;
        border: 1px solid #75715E;
        border-radius: 5px;
        color: #F8F8F2;
        padding: 1px;
    }

    QLabel {
        background-color: transparent;
        border: none;
        color: #F8F8F2;
    }

    QCheckBox {
        background-color: #272822;
        color: #F8F8F2;
    }

    QRadioButton {
        background-color: #272822;
        color: #F8F8F2;
    }

    QPushButton {
        background-color: #66D9EF;
        color: #272822;
        border-radius: 12px;
        padding: 5px;
    }

    QPushButton:pressed {
        background-color: #A6E22E;
    }

    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #A6E22E;
    }
    
    QCheckBox::indicator {
        background-color: #66D9EF;
        border: 1px solid #75715E;
    }

    QCheckBox::indicator:checked {
        background-color: #A6E22E;
        border: 1px solid #A6E22E;
    }

    QCheckBox::indicator:unchecked {
        background-color: #272822;
        border: 1px solid #75715E;
    }

    QRadioButton::indicator {
        width: 12px;
        height: 12px;
        border-radius: 6px;
        background-color: #66D9EF;
        border: 1px solid #75715E;
    }

    QRadioButton::indicator:checked {
        background-color: #A6E22E;
        border: 1px solid #A6E22E;
    }

    QRadioButton::indicator:unchecked {
        background-color: #272822;
        border: 1px solid #75715E;
    }

    QScrollBar:vertical, QScrollBar:horizontal {
        background-color: #3E3D32;
        width: 10px;
    }

    QScrollBar::handle {
        background-color: #66D9EF;
    }

    QScrollBar::add-line, QScrollBar::sub-line {
        background-color: #272822;
    }

    QScrollBar::add-page, QScrollBar::sub-page {
        background-color: #272822;
    }
    """
    app.setStyleSheet(dark_stylesheet)


def main():
    # Start the serial reader in a background thread
    ser = serial.Serial(find_arduino_port(), 115200)
    
    # Create and run the Qt application
    app = QApplication(sys.argv)
    apply_monokai_theme(app)
    window = MainWindow()
    window.show()
    # Pass the MainWindow instance to the serial reader
    serial_thread = threading.Thread(target=serial_reader, args=(ser, window), daemon=True)
    serial_thread.start()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
