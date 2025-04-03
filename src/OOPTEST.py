import customtkinter as ctk
import serial
import serial.tools.list_ports
import time
from tkinter import messagebox

class ConfigApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ESP32 Serial Logger")
        self.geometry("800x600")

        # Use a light theme for a modern, bright look
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Create a Tabview for multiple tabs, all visible at once
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add tabs
        self.tabview.add("Connect")
        self.tabview.add("Data Log")
        self.tabview.add("Settings")
        self.tabview.add("WiFi")
        self.tabview.add("MQTT")

        # Create each tab’s content (frames)
        self.connect_tab = ConnectTab(self.tabview.tab("Connect"), self)
        self.data_log_tab = DataLogTab(self.tabview.tab("Data Log"), self)
        self.settings_tab = SettingsTab(self.tabview.tab("Settings"), self)
        self.wifi_tab = WiFiTab(self.tabview.tab("WiFi"), self)
        self.mqtt_tab = MQTTTab(self.tabview.tab("MQTT"), self)

        # Serial connection state
        self.serial_connection = None
        self.connected = False


# ---------------------------------------------------------------------
# Tab 1: Connect
# ---------------------------------------------------------------------
class ConnectTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Make sure this frame is actually displayed inside the tab
        self.pack(fill="both", expand=True)

        # COM Port Label
        self.port_label = ctk.CTkLabel(self, text="Select COM Port:")
        self.port_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # COM Port dropdown
        self.port_option = ctk.CTkOptionMenu(self, values=self.get_ports(), width=200)
        self.port_option.grid(row=0, column=1, padx=10, pady=10)
        if self.port_option.cget("values"):
            self.port_option.set(self.port_option.cget("values")[0])

        # Baud Rate Label
        self.baud_label = ctk.CTkLabel(self, text="Baud Rate:")
        self.baud_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Baud Rate dropdown
        self.baud_option = ctk.CTkOptionMenu(self, values=["9600", "115200", "230400"], width=200)
        self.baud_option.grid(row=1, column=1, padx=10, pady=10)
        self.baud_option.set("115200")

        # Connect button
        self.connect_button = ctk.CTkButton(self, text="Connect", command=self.connect_serial)
        self.connect_button.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        # Refresh button
        self.refresh_button = ctk.CTkButton(self, text="Refresh Ports", command=self.refresh_ports)
        self.refresh_button.grid(row=2, column=1, padx=10, pady=10, sticky="e")

        # Disconnect button
        self.disconnect_button = ctk.CTkButton(self, text="Disconnect", command=self.disconnect_serial)
        self.disconnect_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Not connected", text_color="gray")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # Let grid expand the last row/column to fill space
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def get_ports(self):
        """Return a list of available COM ports."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        ports = self.get_ports()
        self.port_option.configure(values=ports)
        if ports:
            self.port_option.set(ports[0])
        else:
            self.port_option.set("")

    def connect_serial(self):
        port = self.port_option.get()
        baud = self.baud_option.get()
        if not port or not baud:
            messagebox.showerror("Error", "Please select a COM port and baud rate.")
            return
        try:
            self.app.serial_connection = serial.Serial(port, int(baud), timeout=1)
            self.app.connected = True
            self.status_label.configure(text=f"Connected to {port}", text_color="green")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_label.configure(text="Connection failed", text_color="red")

    def disconnect_serial(self):
        if self.app.serial_connection and self.app.serial_connection.is_open:
            self.app.serial_connection.close()
            self.app.connected = False
            self.status_label.configure(text="Disconnected", text_color="gray")


# ---------------------------------------------------------------------
# Tab 2: Data Log
# ---------------------------------------------------------------------
class DataLogTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        # Textbox to display logs
        self.textbox = ctk.CTkTextbox(self, width=600, height=400)
        self.textbox.pack(padx=10, pady=10, expand=True, fill="both")

        # Fetch button to read from serial
        self.fetch_button = ctk.CTkButton(self, text="Fetch Log", command=self.fetch_log)
        self.fetch_button.pack(pady=5)

    def fetch_log(self):
        """Example: read from serial if your ESP32 code sends data upon request."""
        if self.app.serial_connection and self.app.serial_connection.is_open:
            self.textbox.delete("0.0", "end")
            # Optionally send a command to the ESP
            self.app.serial_connection.write(b'GET_LOG\n')
            time.sleep(1)
            while self.app.serial_connection.in_waiting:
                line = self.app.serial_connection.readline().decode('utf-8', errors='ignore')
                self.textbox.insert("end", line)
        else:
            messagebox.showwarning("Warning", "No serial connection!")

    def append_text(self, text: str):
        """If you want to append text from some other process."""
        self.textbox.insert("end", text)
        self.textbox.see("end")


# ---------------------------------------------------------------------
# Tab 3: Settings
# ---------------------------------------------------------------------
class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="General Settings").pack(pady=20)
        # Add more controls here as needed.


# ---------------------------------------------------------------------
# Tab 4: WiFi
# ---------------------------------------------------------------------
class WiFiTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="WiFi Configuration", font=("", 18)).pack(pady=10)

        self.ssid_entry = ctk.CTkEntry(self, width=300, placeholder_text="Enter WiFi SSID")
        self.ssid_entry.pack(pady=5)

        self.pass_entry = ctk.CTkEntry(self, width=300, placeholder_text="Enter WiFi Password", show="*")
        self.pass_entry.pack(pady=5)

        self.send_button = ctk.CTkButton(self, text="Send WiFi Config", command=self.send_wifi_config)
        self.send_button.pack(pady=10)

        self.check_button = ctk.CTkButton(self, text="Check WiFi Status", command=self.check_wifi_status)
        self.check_button.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="Status: Not connected", text_color="gray")
        self.status_label.pack(pady=10)

    def send_wifi_config(self):
        if self.app.serial_connection and self.app.serial_connection.is_open:
            ssid = self.ssid_entry.get()
            pwd  = self.pass_entry.get()
            if ssid and pwd:
                cmd = f"WIFI:{ssid},{pwd}\n"
                self.app.serial_connection.write(cmd.encode())
                self.status_label.configure(text=f"WiFi Config Sent to {ssid}", text_color="green")
            else:
                self.status_label.configure(text="SSID/Password missing!", text_color="red")
        else:
            self.status_label.configure(text="No serial connection!", text_color="red")

    def check_wifi_status(self):
        if self.app.serial_connection and self.app.serial_connection.is_open:
            self.app.serial_connection.write(b'GET_WIFI_STATUS\n')
            time.sleep(0.5)
            response = ""
            while self.app.serial_connection.in_waiting:
                response += self.app.serial_connection.readline().decode(errors="ignore")
            if response:
                self.status_label.configure(text=f"Status: {response.strip()}", text_color="green")
            else:
                self.status_label.configure(text="No response from device", text_color="red")
        else:
            self.status_label.configure(text="No serial connection!", text_color="red")


# ---------------------------------------------------------------------
# Tab 5: MQTT
# ---------------------------------------------------------------------
class MQTTTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="MQTT Configuration", font=("", 18)).pack(pady=10)

        # Drop-down for servers (main + spares)
        self.server_option = ctk.CTkOptionMenu(self, values=["10.4.32.78", "10.4.88.69", "10.4.88.70"], width=200)
        self.server_option.set("10.4.32.78")
        self.server_option.pack(pady=5)

        self.port_entry = ctk.CTkEntry(self, width=300, placeholder_text="Port (e.g. 1883)")
        self.port_entry.pack(pady=5)

        self.topic_entry = ctk.CTkEntry(self, width=300, placeholder_text="Topic (optional)")
        self.topic_entry.pack(pady=5)

        self.name_entry = ctk.CTkEntry(self, width=300, placeholder_text="MQTT Client Name")
        self.name_entry.pack(pady=5)

        self.host_entry = ctk.CTkEntry(self, width=300, placeholder_text="Host (e.g. ACE)")
        self.host_entry.pack(pady=5)

        self.send_button = ctk.CTkButton(self, text="Send MQTT Config", command=self.send_mqtt_config)
        self.send_button.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="No MQTT config sent yet.", text_color="gray")
        self.status_label.pack(pady=10)

    def send_mqtt_config(self):
        if self.app.serial_connection and self.app.serial_connection.is_open:
            server = self.server_option.get()
            port   = self.port_entry.get() or "1883"
            topic  = self.topic_entry.get() or ""
            name   = self.name_entry.get() or "master"
            host   = self.host_entry.get() or "ACE"

            cmd = f"MQTT:{server},{port},{topic},{name},{host}\n"
            self.app.serial_connection.write(cmd.encode())
            self.status_label.configure(text="MQTT config sent ✅", text_color="green")
        else:
            self.status_label.configure(text="No serial connection!", text_color="red")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()
