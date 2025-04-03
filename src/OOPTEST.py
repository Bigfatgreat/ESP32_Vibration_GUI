import customtkinter as ctk
import serial
import serial.tools.list_ports
import random
import json
from tkinter import ttk, messagebox

class ConfigApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Configuration Program")
        self.geometry("800x600")

        # --- Load Forest Theme ---
        try:
            # Ensure forest-dark.tcl is in the same directory.
            self.tk.call("source", "forest-dark.tcl")
            style = ttk.Style(self)
            style.theme_use("forest-dark")
        except Exception as e:
            print("Forest theme could not be loaded:", e)

        # --- Create Notebook and Tabs ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both")

        self.connection_tab = ConnectionTab(self.notebook, self)
        self.data_log_tab   = DataLogTab(self.notebook, self)
        self.settings_tab   = SettingsTab(self.notebook, self)
        self.wifi_tab       = WiFiTab(self.notebook, self)
        self.mqtt_tab       = MQTTTab(self.notebook, self)

        self.notebook.add(self.connection_tab, text="Connect")
        self.notebook.add(self.data_log_tab, text="Data Log")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.wifi_tab, text="WiFi")
        self.notebook.add(self.mqtt_tab, text="MQTT")

        # --- Disable other tabs until connection is established ---
        for index in range(1, 5):
            self.notebook.tab(index, state="disabled")

        self.serial_connection = None
        self.connected = False

    def enable_other_tabs(self):
        """Enable tabs 2-5 after a successful connection."""
        for index in range(1, 5):
            self.notebook.tab(index, state="normal")

    def start_serial_output(self):
        """Begin periodic output of simulated JSON config values."""
        self.update_serial_output()

    def update_serial_output(self):
        if self.connected:
            # Simulate reading configuration values from ESP (only MQTT values are randomized)
            config = {
                "MQTT": {
                    "server": f"mqtt{random.randint(1,100)}.example.com",
                    "port": random.choice([1883, 8883])
                },
                "WiFi": {
                    "ssid": "SAAA-KKN",      # Fixed value
                    "password": "Ace@6489"   # Fixed value
                }
            }
            json_value = json.dumps(config)
            # Append the JSON string to the Data Log tab (acting as a serial monitor)
            self.data_log_tab.append_text(json_value + "\n")
        # Schedule next update in 100ms
        self.after(100, self.update_serial_output)

# ---------------------------------------------------------------------
# Tab 1: Connection
# ---------------------------------------------------------------------
class ConnectionTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # --- COM Port Selection ---
        ttk.Label(self, text="Select COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_combo = ttk.Combobox(self, values=self.get_ports(), state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5, pady=5)
        if self.port_combo['values']:
            self.port_combo.set(self.port_combo['values'][0])
        
        # --- Baud Rate Selection ---
        ttk.Label(self, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.baud_combo = ttk.Combobox(self, values=["9600", "115200", "230400"], state="readonly")
        self.baud_combo.grid(row=1, column=1, padx=5, pady=5)
        self.baud_combo.set("115200")

        # --- Refresh Button ---
        self.refresh_btn = ttk.Button(self, text="Refresh Ports", command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # --- Connect Button ---
        self.connect_btn = ttk.Button(self, text="Connect", command=self.connect)
        self.connect_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=10)

        # --- Status Label ---
        self.status_label = ttk.Label(self, text="Not connected", foreground="gray")
        self.status_label.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

    def get_ports(self):
        """Return a list of available COM ports."""
        return [port.device for port in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        ports = self.get_ports()
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
        else:
            self.port_combo.set('')

    def connect(self):
        port = self.port_combo.get()
        baud = self.baud_combo.get()
        if not port or not baud:
            messagebox.showerror("Error", "Please select a COM port and baud rate.")
            return
        try:
            # Open serial connection
            self.app.serial_connection = serial.Serial(port, int(baud), timeout=1)
            self.app.connected = True
            self.status_label.config(text=f"Connected to {port}", foreground="green")
            # Enable the other tabs now that we're connected
            self.app.enable_other_tabs()
            # Start printing simulated JSON values to the serial monitor
            self.app.start_serial_output()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_label.config(text="Connection failed", foreground="red")

# ---------------------------------------------------------------------
# Tab 2: Data Log
# ---------------------------------------------------------------------
class DataLogTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        # --- Create a Text widget to act as a serial monitor ---
        self.text = ctk.CTkTextbox(self, wrap="word", height=20)
        self.text.pack(expand=True, fill="both", padx=10, pady=10)

    def append_text(self, content):
        self.text.insert("end", content)
        self.text.see("end")  # auto-scroll to the bottom

# ---------------------------------------------------------------------
# Tab 3: Settings
# ---------------------------------------------------------------------
class SettingsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        ttk.Label(self, text="Settings (LITTLEFS configuration values)").pack(padx=10, pady=10)
        # Here you can add widgets to display or modify configuration values.

# ---------------------------------------------------------------------
# Tab 4: WiFi
# ---------------------------------------------------------------------
class WiFiTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        ttk.Label(self, text="WiFi Configuration").pack(padx=10, pady=10)
        # Add WiFi configuration widgets here (no randomization).

# ---------------------------------------------------------------------
# Tab 5: MQTT
# ---------------------------------------------------------------------
class MQTTTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        ttk.Label(self, text="MQTT Configuration").pack(padx=10, pady=10)
        # Add MQTT configuration widgets here.

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()
