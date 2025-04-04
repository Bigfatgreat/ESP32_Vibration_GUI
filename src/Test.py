import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import time
import threading  # For running the serial listener in a separate thread

class ESP32Configurator:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Configuration Tool")
        self.root.geometry("800x600")
        
        # Serial connection variables
        self.serial_conn = None
        self.port_var = tk.StringVar()
        self.baudrate = 115200
        
        # Create connection frame
        self.create_connection_frame()
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill='both')
        
        # Create tabs
        self.create_overview_tab()
        
        # Disable tabs until connected
        self.set_tabs_state('disabled')
        
        # Load available ports
        self.refresh_ports()

        # Flag to ignore the first few data points
        self.initial_run = True

    def create_connection_frame(self):
        """Create the serial connection controls"""
        conn_frame = tk.Frame(self.root)
        conn_frame.pack(fill='x', padx=5, pady=5)
        
        # Port selection
        tk.Label(conn_frame, text="Port:").pack(side='left')
        self.port_combobox = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20)
        self.port_combobox.pack(side='left', padx=5)
        
        # Refresh button
        tk.Button(conn_frame, text="Refresh", command=self.refresh_ports).pack(side='left', padx=5)
        
        # Connect button
        self.connect_button = tk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.pack(side='left', padx=5)

        # Add command buttons for testing
        self.stop_button = tk.Button(conn_frame, text="Stop Reading", command=self.send_stop)
        self.stop_button.pack(side='left', padx=5)

        self.start_button = tk.Button(conn_frame, text="Start Reading", command=self.send_start)
        self.start_button.pack(side='left', padx=5)

        self.reset_button = tk.Button(conn_frame, text="Reset", command=self.send_reset)
        self.reset_button.pack(side='left', padx=5)

    def send_stop(self):
        """Send the stop command to the ESP32"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(b"STOP_READING\n")  # Send stop command to ESP32
        else:
            messagebox.showerror("Error", "Not connected to device")

    def send_start(self):
        """Send the start command to the ESP32"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(b"START_READING\n")  # Send start command to ESP32
        else:
            messagebox.showerror("Error", "Not connected to device")

    def send_reset(self):
        """Send the reset command to the ESP32"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(b"RESET\n")  # Send reset command to ESP32
        else:
            messagebox.showerror("Error", "Not connected to device")

    def create_overview_tab(self):
        """Create the Overview tab"""
        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text="Overview")
        
        # Current status frame
        status_frame = ttk.LabelFrame(self.overview_tab, text="Current Status")
        status_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Status variables
        self.ax_var = tk.StringVar(value="N/A")
        self.ay_var = tk.StringVar(value="N/A")
        self.az_var = tk.StringVar(value="N/A")
        self.temp_var = tk.StringVar(value="N/A")
        self.vx_var = tk.StringVar(value="N/A")
        self.vy_var = tk.StringVar(value="N/A")
        self.vz_var = tk.StringVar(value="N/A")
        self.dx_var = tk.StringVar(value="N/A")
        self.dy_var = tk.StringVar(value="N/A")
        self.dz_var = tk.StringVar(value="N/A")
        self.hx_var = tk.StringVar(value="N/A")
        self.hkDJ_var = tk.StringVar(value="N/A")
        self.hzz_var = tk.StringVar(value="N/A")
        
        # Sensor labels
        ttk.Label(status_frame, text="AX:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.ax_var).grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="AY:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.ay_var).grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="AZ:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.az_var).grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="Temperature:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.temp_var).grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="VX:").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.vx_var).grid(row=4, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="VY:").grid(row=5, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.vy_var).grid(row=5, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="VZ:").grid(row=6, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.vz_var).grid(row=6, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="DX:").grid(row=7, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.dx_var).grid(row=7, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="DY:").grid(row=8, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.dy_var).grid(row=8, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="DZ:").grid(row=9, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.dz_var).grid(row=9, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="HX:").grid(row=10, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.hx_var).grid(row=10, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="HkDJ:").grid(row=11, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.hkDJ_var).grid(row=11, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="HZZ:").grid(row=12, column=0, sticky='w', padx=5, pady=5)
        ttk.Label(status_frame, textvariable=self.hzz_var).grid(row=12, column=1, sticky='w', padx=5, pady=5)

    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_var.set(ports[0])

    def toggle_connection(self):
        """Toggle serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """Connect to the selected serial port"""
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a port")
            return
            
        try:
            self.serial_conn = serial.Serial(port, self.baudrate, timeout=2)
            self.connect_button.config(text="Disconnect")
            self.set_tabs_state('normal')
            messagebox.showinfo("Success", f"Connected to {port}")

            # Clear the serial buffer before starting
            self.serial_conn.reset_input_buffer()

            # Start listening for serial data in a separate thread
            self.serial_thread = threading.Thread(target=self.listen_for_data)
            self.serial_thread.daemon = True  # Allows the thread to exit when the main program exits
            self.serial_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")

    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.serial_conn = None
        self.connect_button.config(text="Connect")
        self.set_tabs_state('disabled')

    def set_tabs_state(self, state):
        """Enable/disable tabs"""
        for tab in [self.overview_tab]:
            self.notebook.tab(tab, state=state)

    def listen_for_data(self):
        """Listen for data from the ESP32 over serial"""
        while True:
            if self.serial_conn.in_waiting:
                # Read the incoming data
                data = self.serial_conn.readline().decode().strip()
                if data:
                    self.process_data(data)

    def process_data(self, data):
        """Process the received sensor data"""
        try:
            # Assuming the ESP32 sends data in JSON format
            if self.initial_run:
                # Ignore the first few pieces of data (give time to stabilize)
                self.initial_run = False
                return
            
            sensor_data = json.loads(data)
            self.ax_var.set(f"{sensor_data['AX_1']}")
            self.ay_var.set(f"{sensor_data['AY_1']}")
            self.az_var.set(f"{sensor_data['AZ_1']}")
            self.temp_var.set(f"{sensor_data['TEMP_1']}")
            self.vx_var.set(f"{sensor_data['VX_1']}")
            self.vy_var.set(f"{sensor_data['VY_1']}")
            self.vz_var.set(f"{sensor_data['VZ_1']}")
            self.dx_var.set(f"{sensor_data['DX_1']}")
            self.dy_var.set(f"{sensor_data['DY_1']}")
            self.dz_var.set(f"{sensor_data['DZ_1']}")
            self.hx_var.set(f"{sensor_data['HX_1']}")
            self.hkDJ_var.set(f"{sensor_data['HkDJ_1']}")
            self.hzz_var.set(f"{sensor_data['HZZ_1']}")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to parse sensor data")

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32Configurator(root)
    root.mainloop()
