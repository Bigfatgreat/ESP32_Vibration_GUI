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
import paho.mqtt.client as mqtt

class SensorDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Data Monitor")
        self.root.geometry("1100x800")

        # Use a modern TTK theme (try 'clam' or other available themes)
        style = ttk.Style()
        style.theme_use('clam')

        # Serial connection variables
        self.serial_connection = None
        self.serial_queue = queue.Queue()
        self.connected = False

        # For toggling reading (True means "not currently reading")
        self.stop_reading_flag = True  

        # Admin Tab hidden status
        self.admin_tab_added = False

        # Data storage for graphing
        self.graph_data = {
            "Acceleration": {"X": [], "Y": [], "Z": []},
            "Velocity": {"X": [], "Y": [], "Z": []},
            "Distance": {"X": [], "Y": [], "Z": []},
            "Height": {"X": [], "Y": [], "Z": []},
            "Temperature": {"X": []}
        }

        # A buffer to accumulate partial data from the serial queue
        self.buffer = ""

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

        # New MQTT tab for publishing and subscribing
        self.mqtt_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.mqtt_tab, text="MQTT")

        # (Hidden) Admin tab - not added initially
        self.admin_tab = ttk.Frame(self.notebook)

        # Build UI in each tab
        self.build_main_tab()
        self.build_graph_tab()
        self.build_wifi_tab()
        self.build_mqtt_tab()

        # Start serial data processing thread
        self.process_thread = Thread(target=self.process_serial_data, daemon=True)
        self.process_thread.start()

        # Set up Python MQTT client for the MQTT tab
        self.mqtt_client_py = mqtt.Client()
        self.mqtt_client_py.on_connect = self.on_mqtt_connect
        self.mqtt_client_py.on_message = self.on_mqtt_message
        self.mqtt_client_py_connected = False

        # Start MQTT loop in a separate thread
        self.mqtt_thread = Thread(target=self.mqtt_loop, daemon=True)
        self.mqtt_thread.start()

    # -------------------------------------------------------------------------
    # MAIN TAB
    # -------------------------------------------------------------------------
    def build_main_tab(self):
        connection_frame = ttk.Frame(self.main_tab)
        connection_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_combobox = ttk.Combobox(connection_frame, values=self.get_serial_ports(), width=12)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(connection_frame, text="Baud Rate:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.baud_combobox = ttk.Combobox(connection_frame, values=[9600, 19200, 38400, 57600, 115200], width=12)
        self.baud_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.baud_combobox.set("115200")

        # Additional serial settings
        ttk.Label(connection_frame, text="Parity:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.parity_combobox = ttk.Combobox(connection_frame, values=["None", "Even", "Odd"], width=10)
        self.parity_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.parity_combobox.set("None")

        ttk.Label(connection_frame, text="Stop Bits:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.stopbits_combobox = ttk.Combobox(connection_frame, values=["1", "1.5", "2"], width=10)
        self.stopbits_combobox.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.stopbits_combobox.set("1")

        ttk.Label(connection_frame, text="Flow Control:").grid(row=1, column=4, padx=5, pady=5, sticky="w")
        self.flow_control_combobox = ttk.Combobox(connection_frame, values=["None", "RTS/CTS"], width=10)
        self.flow_control_combobox.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        self.flow_control_combobox.set("None")

        # Connect/Disconnect toggle
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=6, rowspan=2, padx=5, pady=5)
        self.status_label = ttk.Label(connection_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=7, rowspan=2, padx=5, pady=5, sticky="w")

        # Commands (START/STOP)
        commands_frame = ttk.Frame(connection_frame)
        commands_frame.grid(row=0, column=8, rowspan=2, padx=5, pady=5, sticky="w")
        self.start_button = ttk.Button(commands_frame, text="Send START", command=self.send_start_command, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(commands_frame, text="Send STOP", command=self.send_stop_command, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Two frames side-by-side: Overview (left), Data Logs (right)
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

        # Data logs (Treeview + event log)
        self.build_data_logs()

    def build_data_logs(self):
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

        self.event_log_frame = ttk.LabelFrame(self.data_logs_frame, text="Event Log")
        self.event_log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.event_log = tk.Text(self.event_log_frame, width=60, height=8)
        self.event_log.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.event_log.config(state=tk.DISABLED)

        self.admin_input = ttk.Entry(self.event_log_frame, width=30)
        self.admin_input.pack(side=tk.BOTTOM, padx=5, pady=5)
        self.admin_input.bind("<Return>", self.check_admin_input)

    # -------------------------------------------------------------------------
    # GRAPH TAB
    # -------------------------------------------------------------------------
    def build_graph_tab(self):
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

    # -------------------------------------------------------------------------
    # WIFI TAB
    # -------------------------------------------------------------------------
    def build_wifi_tab(self):
        container = ttk.Frame(self.wifi_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        status_frame = ttk.LabelFrame(container, text="WiFi Status")
        status_frame.pack(fill=tk.X, pady=5)
        self.wifi_status_dot = ttk.Label(status_frame, text="●", foreground="red")
        self.wifi_status_dot.pack(side=tk.LEFT, padx=5)
        self.wifi_status_label_tab = ttk.Label(status_frame, text="Disconnected")
        self.wifi_status_label_tab.pack(side=tk.LEFT, padx=5)
        self.ip_label = ttk.Label(status_frame, text="IP: Not connected")
        self.ip_label.pack(side=tk.LEFT, padx=20)

        config_frame = ttk.LabelFrame(container, text="WiFi Configuration")
        config_frame.pack(fill=tk.X, pady=5)
        ttk.Label(config_frame, text="SSID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ssid_entry = ttk.Entry(config_frame)
        self.ssid_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(config_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = ttk.Entry(config_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.wifi_toggle_btn = ttk.Button(button_frame, text="Connect", command=self.toggle_wifi_connection)
        self.wifi_toggle_btn.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_wifi_config)
        self.save_button.pack(side=tk.LEFT, padx=5)

        test_frame = ttk.LabelFrame(container, text="Test Connection")
        test_frame.pack(fill=tk.X, pady=5)
        self.test_button = ttk.Button(test_frame, text="Test Internet Connection", command=self.test_internet_connection)
        self.test_button.pack(pady=5)
        self.test_result = ttk.Label(test_frame, text="")
        self.test_result.pack(pady=5)

        self.load_wifi_config()

    def load_wifi_config(self):
        try:
            with open("wifi_config.json", "r") as f:
                config = json.load(f)
                self.ssid_entry.insert(0, config.get("ssid", ""))
                self.password_entry.insert(0, config.get("password", ""))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_wifi_config(self):
        config = {"ssid": self.ssid_entry.get(), "password": self.password_entry.get()}
        with open("wifi_config.json", "w") as f:
            json.dump(config, f)
        messagebox.showinfo("Success", "WiFi configuration saved")

    def toggle_wifi_connection(self):
        if self.wifi_toggle_btn.cget("text") == "Disconnect":
            self.disconnect_wifi()
        else:
            self.connect_wifi()

    def connect_wifi(self):
        ssid = self.ssid_entry.get()
        password = self.password_entry.get()
        if not ssid:
            messagebox.showerror("Error", "Please enter WiFi credentials.")
            return
        self.wifi_toggle_btn.config(text="Disconnect")
        self.wifi_status_label_tab.config(text="Connecting...", foreground="orange")
        if self.serial_connection and self.serial_connection.is_open:
            try:
                cmd = f"SET_WIFI:{ssid},{password}\n"
                self.serial_connection.write(cmd.encode())
                self.log_event(f"Connecting to WiFi: {ssid}")
            except Exception as e:
                self.log_event(f"Error sending WiFi command: {e}")
                self.update_wifi_status(False)
        else:
            self.finish_wifi_connection(ssid, "192.168.1.100")

    def disconnect_wifi(self):
        self.wifi_toggle_btn.config(text="Connect")
        self.wifi_status_label_tab.config(text="Disconnecting...", foreground="orange")
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"DISCONNECT_WIFI\n")
                self.log_event("Disconnecting from WiFi")
            except Exception as e:
                self.log_event(f"Error sending disconnect command: {e}")
        else:
            self.update_wifi_status(False)

    def finish_wifi_connection(self, ssid, ip):
        self.update_wifi_status(True, ssid, ip)
        messagebox.showinfo("Success", f"Connected to {ssid}")

    def update_wifi_status(self, connected, ssid="", ip=""):
        if connected:
            self.wifi_toggle_btn.config(text="Disconnect")
            self.wifi_status_label_tab.config(text=f"Connected to {ssid}", foreground="green")
            self.ip_label.config(text=f"IP: {ip}")
        else:
            self.wifi_toggle_btn.config(text="Connect")
            self.wifi_status_label_tab.config(text="Disconnected", foreground="red")
            self.ip_label.config(text="IP: Not connected")
        self.wifi_dot.config(foreground="green" if connected else "red")
        self.wifi_label.config(text=ssid if connected else "Not connected",
                               foreground="green" if connected else "red")

    def test_internet_connection(self):
        self.test_result.config(text="Testing...")
        try:
            requests.get("http://www.google.com", timeout=5)
            self.test_result.config(text="Internet connection: Working", foreground="green")
        except requests.RequestException:
            self.test_result.config(text="Internet connection: Failed", foreground="red")
    
    def build_mqtt_tab(self):
        container = ttk.Frame(self.mqtt_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        conn_frame = ttk.LabelFrame(container, text="MQTT Connection")
        conn_frame.pack(fill=tk.X, pady=5)
        ttk.Label(conn_frame, text="Broker:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.mqtt_broker_entry = ttk.Entry(conn_frame)
        self.mqtt_broker_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.mqtt_broker_entry.insert(0, "10.4.32.78")
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.mqtt_port_entry = ttk.Entry(conn_frame, width=6)
        self.mqtt_port_entry.grid(row=0, column=3, padx=5, pady=5)
        self.mqtt_port_entry.insert(0, "1883")
        ttk.Label(conn_frame, text="Topic:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.mqtt_topic_entry = ttk.Entry(conn_frame)
        self.mqtt_topic_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.mqtt_topic_entry.insert(0, "")  # Default empty; user can set it.
        button_frame = ttk.Frame(conn_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        self.mqtt_connect_btn = ttk.Button(button_frame, text="Connect MQTT", command=self.connect_mqtt_py)
        self.mqtt_connect_btn.pack(side=tk.LEFT, padx=5)
        self.mqtt_disconnect_btn = ttk.Button(button_frame, text="Disconnect MQTT", command=self.disconnect_mqtt_py)
        self.mqtt_disconnect_btn.pack(side=tk.LEFT, padx=5)
        pub_frame = ttk.LabelFrame(container, text="Publish Message")
        pub_frame.pack(fill=tk.X, pady=5)
        self.mqtt_message_entry = ttk.Entry(pub_frame)
        self.mqtt_message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.mqtt_publish_btn = ttk.Button(pub_frame, text="Publish", command=self.publish_mqtt_message)
        self.mqtt_publish_btn.pack(side=tk.LEFT, padx=5)
        sub_frame = ttk.LabelFrame(container, text="Received MQTT Messages")
        sub_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.mqtt_received_text = tk.Text(sub_frame, height=10)
        self.mqtt_received_text.pack(fill=tk.BOTH, padx=5, pady=5)
        self.mqtt_received_text.config(state=tk.DISABLED)

    def connect_mqtt_py(self):
        broker = self.mqtt_broker_entry.get().strip()
        try:
            port = int(self.mqtt_port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid MQTT port")
            return
        topic = self.mqtt_topic_entry.get().strip()
        if not broker or not topic:
            messagebox.showerror("Error", "Please specify both MQTT broker and topic")
            return
        try:
            self.mqtt_client_py.connect(broker, port, 60)
            self.mqtt_client_py.subscribe(topic)
            self.log_event(f"Connected to MQTT broker {broker}:{port} on topic '{topic}'")
            self.mqtt_connect_btn.config(state=tk.DISABLED)
            self.mqtt_disconnect_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("MQTT Connect Error", str(e))

    def disconnect_mqtt_py(self):
        try:
            self.mqtt_client_py.disconnect()
            self.log_event("Disconnected from MQTT broker.")
            self.mqtt_connect_btn.config(state=tk.NORMAL)
            self.mqtt_disconnect_btn.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("MQTT Disconnect Error", str(e))

    def publish_mqtt_message(self):
        topic = self.mqtt_topic_entry.get().strip()
        message = self.mqtt_message_entry.get().strip()
        if topic and message:
            self.mqtt_client_py.publish(topic, message)
            self.log_event(f"Published to {topic}: {message}")
        else:
            messagebox.showerror("Error", "Enter a message and ensure topic is set")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_event("MQTT client connected successfully.")
        else:
            self.log_event(f"MQTT client connection failed, rc={rc}")

    def on_mqtt_message(self, client, userdata, msg):
        received = f"Topic: {msg.topic}, Message: {msg.payload.decode()}\n"
        self.mqtt_received_text.config(state=tk.NORMAL)
        self.mqtt_received_text.insert(tk.END, received)
        self.mqtt_received_text.see(tk.END)
        self.mqtt_received_text.config(state=tk.DISABLED)

    def mqtt_loop(self):
        try:
            self.mqtt_client_py.loop_forever()
        except Exception as e:
            self.log_event(f"MQTT loop error: {e}")


    # -------------------------------------------------------------------------
    # ADMIN TAB
    # -------------------------------------------------------------------------
    def build_admin_tab(self):
        label = ttk.Label(self.admin_tab, text="Welcome to the Admin Tab!")
        label.pack(pady=20)
        close_btn = ttk.Button(self.admin_tab, text="Close Admin Tab", command=self.hide_admin_tab)
        close_btn.pack(pady=10)

    def check_admin_input(self, event):
        text = self.admin_input.get().strip().lower()
        if text == "admin":
            self.show_admin_tab()
        self.admin_input.delete(0, tk.END)

    def show_admin_tab(self):
        if not self.admin_tab_added:
            self.build_admin_tab()
            self.notebook.add(self.admin_tab, text="Admin")
            self.admin_tab_added = True

    def hide_admin_tab(self):
        if self.admin_tab_added:
            index = self.notebook.index(self.admin_tab)
            self.notebook.forget(index)
            self.admin_tab_added = False

    # -------------------------------------------------------------------------
    # SERIAL / CONNECTION
    # -------------------------------------------------------------------------
    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def toggle_connection(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        port = self.port_combobox.get()
        baud = int(self.baud_combobox.get())
        parity_option = self.parity_combobox.get()
        stopbits_option = self.stopbits_combobox.get()
        flow_option = self.flow_control_combobox.get()

        if parity_option == "None":
            parity = serial.PARITY_NONE
        elif parity_option == "Even":
            parity = serial.PARITY_EVEN
        elif parity_option == "Odd":
            parity = serial.PARITY_ODD
        else:
            parity = serial.PARITY_NONE

        if stopbits_option == "1":
            stopbits = serial.STOPBITS_ONE
        elif stopbits_option == "1.5":
            stopbits = serial.STOPBITS_ONE_POINT_FIVE
        elif stopbits_option == "2":
            stopbits = serial.STOPBITS_TWO
        else:
            stopbits = serial.STOPBITS_ONE

        rtscts = (flow_option == "RTS/CTS")

        try:
            self.serial_connection = serial.Serial(port, baud,
                                                   parity=parity,
                                                   stopbits=stopbits,
                                                   rtscts=rtscts,
                                                   timeout=1)
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
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connected = False
        self.connect_button.config(text="Connect")
        self.status_label.config(text="Disconnected", foreground="red")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.log_event("Disconnected from serial port.")
        self.refresh_graph()

    def refresh_graph(self):
        self.ax.clear()
        if self.graph_data["Acceleration"]["X"]:
            self.ax.plot(self.graph_data["Acceleration"]["X"], label="Acceleration X")
            self.ax.set_title("Sensor Graph")
            self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

    def read_serial_data(self):
        """Reads raw lines from the serial port and puts them into serial_queue."""
        while self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                line = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
                if line:
                    self.serial_queue.put(line)
            except Exception as e:
                self.log_event(f"Serial read error: {e}")
                break

    def process_serial_data(self):
        """Processes lines from serial_queue, extracting full JSON objects from buffer."""
        while True:
            try:
                if not self.serial_queue.empty():
                    new_line = self.serial_queue.get()
                    
                    # Check if this line might be a WiFi status line:
                    if new_line.startswith("WIFI_STATUS:"):
                        parts = new_line.split(":")
                        if len(parts) >= 4:
                            status = parts[1]
                            ssid = parts[2]
                            ip = parts[3]
                            self.update_wifi_status(status == "CONNECTED", ssid, ip)
                        continue

                    # Otherwise, treat as potential partial JSON data
                    self.buffer += new_line + "\n"

                    # Attempt to extract multiple JSON objects from the buffer
                    while True:
                        start_index = self.buffer.find('{')
                        if start_index == -1:
                            # No opening brace found, break
                            break
                        end_index = self.buffer.find('}', start_index)
                        if end_index == -1:
                            # No closing brace found, need more data
                            break

                        # Extract the JSON substring
                        json_str = self.buffer[start_index:end_index+1]
                        # Remove it from the buffer
                        self.buffer = self.buffer[end_index+1:]
                        
                        # Attempt to parse JSON
                        try:
                            sensor_data = json.loads(json_str)
                            # We have valid sensor data, update UI
                            self.update_sensor_ui(sensor_data)
                        except json.JSONDecodeError:
                            self.log_event(f"Invalid JSON data: {json_str}")
                            # we continue searching for next object in the buffer

                self.root.update()
            except Exception as e:
                self.log_event(f"UI update error: {e}")

    def update_sensor_ui(self, sensor_data):
        """Updates the treeview and graph data using a parsed sensor_data dict."""
        # Clear existing rows
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

        # Insert new rows
        self.tree.insert("", tk.END, values=(f"X: {ax}", f"X: {vx}", f"X: {dx}", f"X: {hx}"))
        self.tree.insert("", tk.END, values=(f"Y: {ay}", f"Y: {vy}", f"Y: {dy}", f"Y: {hy}"))
        self.tree.insert("", tk.END, values=(f"Z: {az}", f"Z: {vz}", f"Z: {dz}", f"Z: {hz}"))

        # Store for graph
        self.store_graph_data(ax, ay, az, vx, vy, vz, dx, dy, dz, hx, hy, hz, temp)

        self.log_event("Sensor data received.")

    # -------------------------------------------------------------------------
    # UI UPDATES (Graph Data, etc.)
    # -------------------------------------------------------------------------
    def store_graph_data(self, ax, ay, az, vx, vy, vz, dx, dy, dz, hx, hy, hz, temp):
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

        # Limit to last 100 points
        for sensor_dict in self.graph_data.values():
            for comp_list in sensor_dict.values():
                if len(comp_list) > 100:
                    comp_list.pop(0)

    # -------------------------------------------------------------------------
    # COMMANDS
    # -------------------------------------------------------------------------
    def send_start_command(self):
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
