import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
from threading import Thread
import queue
import json
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import socket
import requests

class SensorDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Data Monitor")
        self.root.geometry("1100x800")

        # Serial connection variables
        self.serial_connection = None
        self.serial_queue = queue.Queue()
        self.connected = False
        
        # For toggling reading (True means "not currently reading")
        self.stop_reading_flag = True  

        # Admin Tab hidden status
        self.admin_tab_added = False

        # Create a Notebook for Main, Graph and WiFi tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create Main tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")

        # Create Graph tab
        self.graph_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.graph_tab, text="Graph")

        # Create WiFi tab
        self.wifi_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.wifi_tab, text="WiFi")

        # (Hidden) Admin tab - not added initially
        self.admin_tab = ttk.Frame(self.notebook)

        # Build UI in each tab
        self.build_main_tab()
        self.build_graph_tab()
        self.build_wifi_tab()

        # Start serial data processing thread
        self.process_thread = Thread(target=self.process_serial_data, daemon=True)
        self.process_thread.start()

    # -------------------------------------------------------------------------
    # MAIN TAB
    # -------------------------------------------------------------------------
    def build_main_tab(self):
        """
        Build the layout for the Main tab:
          - Serial connection controls (toggle Connect/Disconnect)
          - Overview (Wi-Fi and MQTT status placeholders)
          - Data Logs (sensor data treeview and event log)
        """
        # Top: Connection Frame
        connection_frame = ttk.Frame(self.main_tab)
        connection_frame.pack(fill=tk.X, padx=5, pady=5)

        # Port Label and Combo
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_combobox = ttk.Combobox(connection_frame, values=self.get_serial_ports(), width=12)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Baud Label and Combo
        ttk.Label(connection_frame, text="Baud Rate:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.baud_combobox = ttk.Combobox(connection_frame, values=[9600, 19200, 38400, 57600, 115200], width=12)
        self.baud_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.baud_combobox.set("115200")

        # Serial Connect/Disconnect Toggle Button
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)

        # Status Label for serial connection
        self.status_label = ttk.Label(connection_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # Commands Frame for sending START/STOP commands
        commands_frame = ttk.Frame(connection_frame)
        commands_frame.grid(row=0, column=6, padx=5, pady=5, sticky="w")
        self.start_button = ttk.Button(commands_frame, text="Send START", command=self.send_start_command, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(commands_frame, text="Send STOP", command=self.send_stop_command, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Middle: Two frames side-by-side: Overview (left), Data Logs (right)
        content_frame = ttk.Frame(self.main_tab)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.overview_frame = ttk.LabelFrame(content_frame, text="Overview")
        self.overview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.data_logs_frame = ttk.LabelFrame(content_frame, text="Data Logs")
        self.data_logs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Overview: Wi-Fi & MQTT placeholders
        ttk.Label(self.overview_frame, text="Wi-Fi: ").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.wifi_dot = ttk.Label(self.overview_frame, text="\u25CF", foreground="red")
        self.wifi_dot.grid(row=0, column=1, padx=2, pady=5, sticky="w")
        self.wifi_label = ttk.Label(self.overview_frame, text="Not connected", foreground="red")
        self.wifi_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(self.overview_frame, text="MQTT:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mqtt_dot = ttk.Label(self.overview_frame, text="\u25CF", foreground="red")
        self.mqtt_dot.grid(row=1, column=1, padx=2, pady=5, sticky="w")
        self.mqtt_label = ttk.Label(self.overview_frame, text="Not connected", foreground="red")
        self.mqtt_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Data Logs: sensor values (treeview) and event log
        self.build_data_logs()

    def build_data_logs(self):
        """Build the treeview for sensor data and a compact event log."""
        # Sensor data treeview
        self.tree = ttk.Treeview(self.data_logs_frame, columns=("A", "V", "D", "H"), show="headings", height=8)
        self.tree.heading("A", text="Acceleration")
        self.tree.heading("V", text="Velocity")
        self.tree.heading("D", text="Distance")
        self.tree.heading("H", text="Height")
        self.tree.column("A", width=150, anchor=tk.CENTER)
        self.tree.column("V", width=150, anchor=tk.CENTER)
        self.tree.column("D", width=150, anchor=tk.CENTER)
        self.tree.column("H", width=150, anchor=tk.CENTER)
        self.tree.pack(fill=tk.X, padx=5, pady=5)

        # Compact event log area
        self.event_log_frame = ttk.LabelFrame(self.data_logs_frame, text="Event Log")
        self.event_log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.event_log = tk.Text(self.event_log_frame, width=60, height=8)
        self.event_log.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.event_log.config(state=tk.DISABLED)
        # Hidden Admin Tab Input (for toggling admin tab on 'admin' command)
        self.admin_input = ttk.Entry(self.event_log_frame, width=30)
        self.admin_input.pack(side=tk.BOTTOM, padx=5, pady=5)
        self.admin_input.bind("<Return>", self.check_admin_input)

    # -------------------------------------------------------------------------
    # GRAPH TAB
    # -------------------------------------------------------------------------
    def build_graph_tab(self):
        """Create the Graph tab with matplotlib visualization for sensor data."""
        graph_control_frame = ttk.LabelFrame(self.graph_tab, text="Graph Controls")
        graph_control_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(graph_control_frame, text="Select Sensor:").pack(side=tk.LEFT, padx=5, pady=5)
        self.sensor_var = tk.StringVar()
        sensor_options = ["Acceleration", "Velocity", "Distance", "Height", "Temperature"]
        self.sensor_menu = ttk.OptionMenu(graph_control_frame, self.sensor_var, sensor_options[0], *sensor_options)
        self.sensor_menu.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(graph_control_frame, text="Component:").pack(side=tk.LEFT, padx=5, pady=5)
        self.component_var = tk.StringVar()
        self.component_menu = ttk.OptionMenu(graph_control_frame, self.component_var, "X", "X", "Y", "Z")
        self.component_menu.pack(side=tk.LEFT, padx=5, pady=5)
        update_button = ttk.Button(graph_control_frame, text="Update Graph", command=self.update_graph)
        update_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.graph_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # Data storage for graphing
        self.graph_data = {
            "Acceleration": {"X": [], "Y": [], "Z": []},
            "Velocity": {"X": [], "Y": [], "Z": []},
            "Distance": {"X": [], "Y": [], "Z": []},
            "Height": {"X": [], "Y": [], "Z": []},
            "Temperature": {"X": []}
        }

    # -------------------------------------------------------------------------
    # WIFI TAB
    # -------------------------------------------------------------------------
    def build_wifi_tab(self):
        """Build the WiFi configuration tab with a single toggle button."""
        container = ttk.Frame(self.wifi_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Status frame for WiFi
        status_frame = ttk.LabelFrame(container, text="WiFi Status")
        status_frame.pack(fill=tk.X, pady=5)
        self.wifi_status_dot = ttk.Label(status_frame, text="●", foreground="red")
        self.wifi_status_dot.pack(side=tk.LEFT, padx=5)
        self.wifi_status_label_tab = ttk.Label(status_frame, text="Disconnected")
        self.wifi_status_label_tab.pack(side=tk.LEFT, padx=5)
        self.ip_label = ttk.Label(status_frame, text="IP: Not connected")
        self.ip_label.pack(side=tk.LEFT, padx=20)

        # Configuration frame for WiFi credentials
        config_frame = ttk.LabelFrame(container, text="WiFi Configuration")
        config_frame.pack(fill=tk.X, pady=5)
        ttk.Label(config_frame, text="SSID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ssid_entry = ttk.Entry(config_frame)
        self.ssid_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(config_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = ttk.Entry(config_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        # Button frame with single toggle button
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.wifi_toggle_btn = ttk.Button(button_frame, text="Connect", command=self.toggle_wifi_connection)
        self.wifi_toggle_btn.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_wifi_config)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Test Internet connection
        test_frame = ttk.LabelFrame(container, text="Test Connection")
        test_frame.pack(fill=tk.X, pady=5)
        self.test_button = ttk.Button(test_frame, text="Test Internet Connection", command=self.test_internet_connection)
        self.test_button.pack(pady=5)
        self.test_result = ttk.Label(test_frame, text="")
        self.test_result.pack(pady=5)
        
        # Load saved configuration if exists
        self.load_wifi_config()

    def load_wifi_config(self):
        """Load WiFi configuration from a file."""
        try:
            with open("wifi_config.json", "r") as f:
                config = json.load(f)
                self.ssid_entry.insert(0, config.get("ssid", ""))
                self.password_entry.insert(0, config.get("password", ""))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_wifi_config(self):
        """Save WiFi configuration to a file."""
        config = {
            "ssid": self.ssid_entry.get(),
            "password": self.password_entry.get()
        }
        with open("wifi_config.json", "w") as f:
            json.dump(config, f)
        messagebox.showinfo("Success", "WiFi configuration saved")

    def toggle_wifi_connection(self):
        """Toggle the WiFi connection state using a single button."""
        if self.wifi_toggle_btn.cget("text") == "Disconnect":
            self.disconnect_wifi()
        else:
            self.connect_wifi()

    def connect_wifi(self):
        """Handle WiFi connection via serial command."""
        ssid = self.ssid_entry.get()
        password = self.password_entry.get()
        if not ssid:
            messagebox.showerror("Error", "Please enter WiFi credentials.")
            return
        self.wifi_toggle_btn.config(text="Disconnect")
        self.wifi_status_label_tab.config(text="Connecting...", foreground="orange")
        # Send command to device for WiFi connection
        if self.serial_connection and self.serial_connection.is_open:
            try:
                cmd = f"SET_WIFI:{ssid},{password}\n"
                self.serial_connection.write(cmd.encode())
                self.log_event(f"Connecting to WiFi: {ssid}")
            except Exception as e:
                self.log_event(f"Error sending WiFi command: {e}")
                self.update_wifi_status(False)
        else:
            # For testing without serial connection, simulate a connection
            self.finish_wifi_connection(ssid, "192.168.1.100")

    def disconnect_wifi(self):
        """Handle WiFi disconnection."""
        self.wifi_toggle_btn.config(text="Connect")
        self.wifi_status_label_tab.config(text="Disconnecting...", foreground="orange")
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"DISCONNECT_WIFI\n")
                self.log_event("Disconnecting from WiFi")
            except Exception as e:
                self.log_event(f"Error sending disconnect command: {e}")
        else:
            # Simulate immediate disconnection for testing
            self.update_wifi_status(False)

    def finish_wifi_connection(self, ssid, ip):
        """Finish the WiFi connection process and update UI accordingly."""
        self.update_wifi_status(True, ssid, ip)
        messagebox.showinfo("Success", f"Connected to {ssid}")

    def update_wifi_status(self, connected, ssid="", ip=""):
        """Update WiFi status labels in the WiFi tab and main tab overview."""
        if connected:
            self.wifi_toggle_btn.config(text="Disconnect")
            self.wifi_status_label_tab.config(text=f"Connected to {ssid}", foreground="green")
            self.ip_label.config(text=f"IP: {ip}")
        else:
            self.wifi_toggle_btn.config(text="Connect")
            self.wifi_status_label_tab.config(text="Disconnected", foreground="red")
            self.ip_label.config(text="IP: Not connected")
        # Update main tab overview status as well
        self.wifi_dot.config(foreground="green" if connected else "red")
        self.wifi_label.config(text=ssid if connected else "Not connected",
                               foreground="green" if connected else "red")

    def test_internet_connection(self):
        """Test active Internet connection."""
        self.test_result.config(text="Testing...")
        try:
            requests.get("http://www.google.com", timeout=5)
            self.test_result.config(text="Internet connection: Working", foreground="green")
        except requests.RequestException:
            self.test_result.config(text="Internet connection: Failed", foreground="red")

    # -------------------------------------------------------------------------
    # ADMIN TAB (same as before)
    # -------------------------------------------------------------------------
    def build_admin_tab(self):
        """Create the admin tab layout (only if needed)."""
        label = ttk.Label(self.admin_tab, text="Welcome to the Admin Tab!")
        label.pack(pady=20)
        close_btn = ttk.Button(self.admin_tab, text="Close Admin Tab", command=self.hide_admin_tab)
        close_btn.pack(pady=10)

    def check_admin_input(self, event):
        """Check if the user typed 'admin' to reveal the Admin tab."""
        text = self.admin_input.get().strip().lower()
        if text == "admin":
            self.show_admin_tab()
        self.admin_input.delete(0, tk.END)

    def show_admin_tab(self):
        """Add the admin tab if not already added."""
        if not self.admin_tab_added:
            self.build_admin_tab()
            self.notebook.add(self.admin_tab, text="Admin")
            self.admin_tab_added = True

    def hide_admin_tab(self):
        """Remove the admin tab."""
        if self.admin_tab_added:
            index = self.notebook.index(self.admin_tab)
            self.notebook.forget(index)
            self.admin_tab_added = False

    # -------------------------------------------------------------------------
    # SERIAL / CONNECTION
    # -------------------------------------------------------------------------
    def get_serial_ports(self):
        """Get list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def toggle_connection(self):
        """Toggle serial connection state."""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        """Connect to the serial port."""
        port = self.port_combobox.get()
        baud = int(self.baud_combobox.get())
        try:
            self.serial_connection = serial.Serial(port, baud, timeout=1)
            self.connected = True
            self.connect_button.config(text="Disconnect")
            self.status_label.config(text="Connected", foreground="green")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.serial_thread = Thread(target=self.read_serial_data, daemon=True)
            self.serial_thread.start()
            self.log_event("Connected to serial port.")
        except Exception as e:
            self.log_event(f"Connection error: {e}")

    def disconnect(self):
        """Disconnect from serial port and refresh graph."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connected = False
        self.connect_button.config(text="Connect")
        self.status_label.config(text="Disconnected", foreground="red")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.log_event("Disconnected from serial port.")
        # Refresh graph so that previous data remains visible
        self.refresh_graph()

    def refresh_graph(self):
        """Redraw the graph with existing data (if any)."""
        self.ax.clear()
        # Example: Plot acceleration X if available
        if self.graph_data["Acceleration"]["X"]:
            self.ax.plot(self.graph_data["Acceleration"]["X"], label="Acceleration X")
            self.ax.set_title("Sensor Graph")
            self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

    def read_serial_data(self):
        """Read data from serial port in a separate thread."""
        while self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                line = self.serial_connection.readline().decode('utf-8').strip()
                if line:
                    self.serial_queue.put(line)
            except Exception as e:
                self.log_event(f"Serial read error: {e}")
                break

    def process_serial_data(self):
        """Process incoming serial data in the main thread."""
        while True:
            try:
                if not self.serial_queue.empty():
                    data = self.serial_queue.get()
                    # If data is a WiFi status message, update WiFi UI accordingly
                    if data.startswith("WIFI_STATUS:"):
                        parts = data.split(":")
                        if len(parts) >= 4:
                            status = parts[1]
                            ssid = parts[2]
                            ip = parts[3]
                            self.update_wifi_status(status == "CONNECTED", ssid, ip)
                        continue
                    self.update_ui(data)
                self.root.update()
            except Exception as e:
                self.log_event(f"UI update error: {e}")

    # -------------------------------------------------------------------------
    # UI UPDATES
    # -------------------------------------------------------------------------
    def update_ui(self, data):
        """Update the UI with new sensor data."""
        try:
            sensor_data = json.loads(data)
            self.tree.delete(*self.tree.get_children())
            ax = sensor_data.get("AX_1", "-")
            ay = sensor_data.get("AY_1", "-")
            az = sensor_data.get("AZ_1", "-")
            vx = sensor_data.get("VX_1", "-")
            vy = sensor_data.get("VY_1", "-")
            vz = sensor_data.get("VZ_1", "-")
            dx = sensor_data.get("DX_1", "-")
            dy = sensor_data.get("DY_1", "-")
            dz = sensor_data.get("DZ_1", "-")
            hx = sensor_data.get("HX_1", "-")
            hy = sensor_data.get("HY_1", "-")
            hz = sensor_data.get("HZ_1", "-")
            temp = sensor_data.get("TEMP_1", None)
            self.tree.insert("", tk.END, values=(f"X: {ax}", f"X: {vx}", f"X: {dx}", f"X: {hx}"))
            self.tree.insert("", tk.END, values=(f"Y: {ay}", f"Y: {vy}", f"Y: {dy}", f"Y: {hy}"))
            self.tree.insert("", tk.END, values=(f"Z: {az}", f"Z: {vz}", f"Z: {dz}", f"Z: {hz}"))
            self.store_graph_data(ax, ay, az, vx, vy, vz, dx, dy, dz, hx, hy, hz, temp)
            self.log_event("Sensor data received.")
        except json.JSONDecodeError:
            self.log_event("Invalid JSON data received.")
        except Exception as e:
            self.log_event(f"Error updating UI: {e}")

    def store_graph_data(self, ax, ay, az, vx, vy, vz, dx, dy, dz, hx, hy, hz, temp):
        """Store data for plotting in the graph tab."""
        def safe_float(val):
            try:
                return float(val)
            except:
                return None
        axf, ayf, azf = safe_float(ax), safe_float(ay), safe_float(az)
        vxf, vyf, vzf = safe_float(vx), safe_float(vy), safe_float(vz)
        dxf, dyf, dzf = safe_float(dx), safe_float(dy), safe_float(dz)
        hxf, hyf, hzf = safe_float(hx), safe_float(hy), safe_float(hz)
        tf = safe_float(temp) if temp else None
        if axf is not None: self.graph_data["Acceleration"]["X"].append(axf)
        if ayf is not None: self.graph_data["Acceleration"]["Y"].append(ayf)
        if azf is not None: self.graph_data["Acceleration"]["Z"].append(azf)
        if vxf is not None: self.graph_data["Velocity"]["X"].append(vxf)
        if vyf is not None: self.graph_data["Velocity"]["Y"].append(vyf)
        if vzf is not None: self.graph_data["Velocity"]["Z"].append(vzf)
        if dxf is not None: self.graph_data["Distance"]["X"].append(dxf)
        if dyf is not None: self.graph_data["Distance"]["Y"].append(dyf)
        if dzf is not None: self.graph_data["Distance"]["Z"].append(dzf)
        if hxf is not None: self.graph_data["Height"]["X"].append(hxf)
        if hyf is not None: self.graph_data["Height"]["Y"].append(hyf)
        if hzf is not None: self.graph_data["Height"]["Z"].append(hzf)
        if tf is not None:
            self.graph_data["Temperature"]["X"].append(tf)
        for sensor_dict in self.graph_data.values():
            for comp_list in sensor_dict.values():
                if len(comp_list) > 100:
                    comp_list.pop(0)

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------
    def send_start_command(self):
        """Send START_READING command to Arduino."""
        if self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"START_READING\n")
                self.stop_reading_flag = False
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.log_event("Sent START_READING command.")
            except Exception as e:
                self.log_event(f"Error sending START command: {e}")

    def send_stop_command(self):
        """Send STOP_READING command to Arduino."""
        if self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"STOP_READING\n")
                self.stop_reading_flag = True
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.log_event("Sent STOP_READING command.")
            except Exception as e:
                self.log_event(f"Error sending STOP command: {e}")

    def update_graph(self):
        """Update the graph with selected sensor data."""
        sensor = self.sensor_var.get()
        component = self.component_var.get()
        if sensor == "Temperature":
            component = "X"
        data = self.graph_data[sensor][component]
        self.ax.clear()
        self.ax.plot(data, label=f"{sensor} {component}")
        self.ax.set_title(f"{sensor} {component} over Time")
        self.ax.set_xlabel("Time (samples)")
        self.ax.set_ylabel("Value")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

    # -------------------------------------------------------------------------
    # LOGGING
    # -------------------------------------------------------------------------
    def log_event(self, message):
        """Log an event with a timestamp in the event log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.event_log.config(state=tk.NORMAL)
        self.event_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.event_log.see(tk.END)
        self.event_log.config(state=tk.DISABLED)

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SensorDataGUI(root)
    root.mainloop()
