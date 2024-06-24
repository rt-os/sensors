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
WIDTH,HEIGHT = 1280,720

# Global variables
LOGGING = False
FILE_PREFIX = ""
FILE_COMMENT = ""

# an array of NUM_SENSORS, each element is a deque of WINDOW_SIZE
sensor_data = [deque([-1] * WINDOW_SIZE, maxlen=WINDOW_SIZE) for _ in range(NUM_SENSORS)]
mindist = [999999 for _ in range(NUM_SENSORS)]

# capture multiple sensors per line
pattern = re.compile(r'D(\d)\s*\(mm\):\s*(\d+)')

from serial.tools import list_ports
def find_arduino_port():
    ports = list(list_ports.comports())
    for port in ports:
        if "CH340" in port.description or "CP210x" in port.description:
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

        self.sl0 = customtkinter.CTkLabel(self, text="1:", padx=5)
        self.sv0 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl1 = customtkinter.CTkLabel(self, text="2:", padx=5)
        self.sv1 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl2 = customtkinter.CTkLabel(self, text="3:", padx=5)
        self.sv2 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl3 = customtkinter.CTkLabel(self, text="4:", padx=5)
        self.sv3 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl4 = customtkinter.CTkLabel(self, text="5:", padx=5)
        self.sv4 = customtkinter.CTkLabel(self, text="-1", width=70, fg_color="black", corner_radius=10)
        self.sl5 = customtkinter.CTkLabel(self, text="6:", padx=5)
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
        self.timer_callback()

    def timer_callback(self):
        global sensor_data
        self.sv0.configure(text=str(sensor_data[0][0])+"mm")
        self.sv1.configure(text=str(sensor_data[1][0])+"mm")
        self.sv2.configure(text=str(sensor_data[2][0])+"mm")
        self.sv3.configure(text=str(sensor_data[3][0])+"mm")
        self.sv4.configure(text=str(sensor_data[4][0])+"mm")
        self.sv5.configure(text=str(sensor_data[5][0])+"mm")
        self.after(1000, self.timer_callback)


class SideFrame(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        # self.master = master
        self.sitelbl = customtkinter.CTkLabel(self, text="Site:")
        self.site = customtkinter.CTkEntry(self, placeholder_text="Site")
        self.bldlbl = customtkinter.CTkLabel(self, text="Building:")
        self.commentl = customtkinter.CTkLabel(self, text="Comment:")
        self.comment = customtkinter.CTkEntry(self, placeholder_text="Comment")

        def optionmenu_callback(choice):
            pass
        def checkbox_event():
            if (self.checkbox_2.get()==1):
                self.site.configure(state="disabled")
                self.comment.configure(state="disabled")
            else:
                self.site.configure(state="normal")
                self.comment.configure(state="normal")


        self.optionmenu = customtkinter.CTkOptionMenu(self,values=["1", "2", "3", "4", "5", "6"],
                                                command=optionmenu_callback)
        self.checkbox_2 = customtkinter.CTkCheckBox(self, text="locked",command=checkbox_event)

        self.sitelbl.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        self.site.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="w")

        self.bldlbl.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        self.optionmenu.grid(row=4, column=0, padx=10, pady=(2, 0), sticky="w")

        self.commentl.grid(row=5, column=0, padx=10, pady=(10, 0), sticky="w")
        self.comment.grid(row=6, column=0, padx=10, pady=(2, 0), sticky="w")

        self.checkbox_2.grid(row=7, column=0, padx=10, pady=(8, 4), sticky="w")

        self.site.bind('<Key>', lambda event: self.pass_check())
    def pass_check(self):
        self.site.configure(textvariable=self.site.get().strip())
        self.comment.configure(textvariable=self.comment.get().strip())
        
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sensors")
        # self.geometry("400x180")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.side_frame = SideFrame(self)
        self.side_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ns")
        self.outputlbl = customtkinter.CTkLabel(self, text="")
        self.outputlbl.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.sensor_frame = sensorBar(self)
        self.sensor_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew",columnspan=2)

        self.button = customtkinter.CTkButton(self, text="start/stop", command=self.button_callback)
        self.button.grid(row=2, column=0, padx=10, pady=10, sticky="ew",columnspan=2)
        self.bindings()
        # self.after(1000, timer_callback)
        self.timer_callback()

    def timer_callback(self):
        pass
        # global sensor_data
        # self.outputlbl.configure(text=datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%Y%m%d_%H%M%S"))
        # self.after(1000, self.timer_callback)
        # print(sensor_data)


    def bindings(self):
        self.bind('<space>', lambda event: self.button_callback())
 

    def button_callback(self):
        global LOGGING, FILE_PREFIX, FILE_COMMENT
        
        pst = datetime.now(pytz.timezone('America/Los_Angeles'))
        time = pst.strftime("%Y%m%d_%H%M%S")
        FILE_PREFIX = self.side_frame.site.get() + self.side_frame.optionmenu.get() + "_"
        FILE_COMMENT = self.side_frame.comment.get()
        if not LOGGING:
            self.outputlbl.configure(text=self.outputlbl._text+"\n"+FILE_PREFIX + time + "_" + FILE_COMMENT + " opened")
        else:
            self.outputlbl.configure(text=self.outputlbl._text+"\n" + " - Closed - ")
        LOGGING = not LOGGING
 

def capture_data(sensor_id, value):
    sensor_data[sensor_id].append(value)
    mindist[sensor_id] = min(mindist[sensor_id], value)

def gen_file_name(type):
    global FILE_PREFIX, FILE_COMMENT
    pst = datetime.now(pytz.timezone('America/Los_Angeles'))
    fn = pst.strftime("%Y%m%d_%H%M%S")
    return FILE_PREFIX+fn+"_"+FILE_COMMENT+".csv"

def serial_reader(ser):
    global sensor_data, LOGGING, FILE_PREFIX
    logging_running = False
    writer = {}
    log_file = {}
    fn = ""
    # logger = logging.getLogger(__name__)
    while True:
        if LOGGING:
            if logging_running:
                pass
            else:
                logging_running = True
                fn = gen_file_name(0)
                log_file = open(fn, 'w', newline='')
                # App.outputlbl.configure(text=App.outputlbl._text+"\n"+fn+" Opened")
                # logger.info(f"starting: {fn}")
                writer = csv.writer(log_file)
                writer.writerow(['milliseconds (PST)', 'Sensor Number', 'Measurement'])
        else:
            if logging_running:
                logging_running = False
                # logger.info(f"saved: {fn}")
                # App.outputlbl.configure(text=App.outputlbl._text+"\n Saved and Closed")
                log_file.close()
                fn = ""
            else:
                pass
        try:
            line = ser.readline().decode('utf-8').strip()
            matches = re.findall(pattern, line)
            timestamp = int(time.time() * 1000)
            for hit in matches:
                # logger.debug("Index:", hit[0], "Measurement:", hit[1])
                sensor_id = int(hit[0])
                data_value = int(hit[1])
                if 0 <= sensor_id < len(sensor_data):
                    capture_data(sensor_id, data_value)
                    if logging_running:
                        writer.writerow([timestamp, sensor_id, data_value])
        except UnicodeDecodeError:
            print("Error decoding byte sequence from serial port")


def main():
    # Open serial port
    ser = serial.Serial(find_arduino_port(), 115200)

    # Start the serial reader thread
    serial_thread = threading.Thread(target=serial_reader, args=(ser,), daemon=True)
    serial_thread.start()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

