import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
from threading import Thread
import queue
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class SensorDataGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Data Monitor")
        self.root.geometry("1100x800")
        
        # Serial connection variables
        self.serial_connection = None
        self.serial_queue = queue.Queue()
        self.stop_reading = False
        self.connected = False
        
        # Temperature threshold
        self.temp_threshold = 25  # Default threshold (can be changed)
        self.temp_exceeded = False

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

         # Create main container
        self.main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel (main content)
        self.left_panel = ttk.Frame(self.main_container)
        self.main_container.add(self.left_panel, weight=4)
        
        # Create right panel (temperature monitor)
        self.right_panel = ttk.Frame(self.main_container)
        self.main_container.add(self.right_panel, weight=1)

        
        # Create Main tab
        self.create_main_tab()
        
        # Create Graph tab
        self.create_graph_tab()

        # Create Temperature Monitor in right panel
        self.create_temperature_panel()
        
        # Start serial data processing thread
        self.process_thread = Thread(target=self.process_serial_data, daemon=True)
        self.process_thread.start()
        
    def create_temperature_panel(self):
        """Create the temperature monitoring panel on the right side"""
        temp_frame = ttk.LabelFrame(self.right_panel, text="Temperature Monitor")
        temp_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Threshold control
        threshold_frame = ttk.Frame(temp_frame)
        threshold_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(threshold_frame, text="Threshold (°C):").pack(side=tk.LEFT)
        self.threshold_entry = ttk.Entry(threshold_frame, width=5)
        self.threshold_entry.pack(side=tk.LEFT, padx=5)
        self.threshold_entry.insert(0, "25")
        
        set_button = ttk.Button(threshold_frame, text="Set", command=self.set_threshold)
        set_button.pack(side=tk.LEFT)
        
        # Current temperature display
        self.current_temp_var = tk.StringVar()
        self.current_temp_var.set("-- °C")
        temp_display = ttk.Label(temp_frame, textvariable=self.current_temp_var, 
                               font=('Helvetica', 24), foreground="blue")
        temp_display.pack(pady=10)
        
        # Temperature bar graph
        self.temp_fig = Figure(figsize=(3, 4), dpi=80)
        self.temp_ax = self.temp_fig.add_subplot(111)
        self.temp_ax.set_ylim(0, 50)  # Assuming temperature range 0-50°C
        self.temp_ax.axhline(y=self.temp_threshold, color='r', linestyle='--')
        self.temp_bar = self.temp_ax.bar(0, 0, width=0.8, color='blue')
        self.temp_ax.set_title("Temperature")
        self.temp_ax.set_ylabel("°C")
        self.temp_ax.set_xticks([])  # Remove x-axis ticks
        
        self.temp_canvas = FigureCanvasTkAgg(self.temp_fig, master=temp_frame)
        self.temp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def set_threshold(self):
        """Set the temperature threshold"""
        try:
            self.temp_threshold = float(self.threshold_entry.get())
            self.temp_ax.lines[0].set_ydata([self.temp_threshold, self.temp_threshold])
            self.temp_canvas.draw()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for threshold")
    
    def update_temperature_display(self, temp):
        """Update the temperature display and bar graph"""
        try:
            temp_value = float(temp)
            self.current_temp_var.set(f"{temp_value:.1f} °C")
            
            # Update bar graph
            self.temp_bar[0].set_height(temp_value)
            
            # Change color based on threshold
            if temp_value > self.temp_threshold:
                self.temp_bar[0].set_color('red')
                if not self.temp_exceeded:
                    self.show_temp_alert(temp_value)
                    self.temp_exceeded = True
            else:
                self.temp_bar[0].set_color('blue')
                self.temp_exceeded = False
            
            self.temp_canvas.draw()
        except (ValueError, TypeError):
            pass
    
    def show_temp_alert(self, temp_value):
        """Show popup alert when temperature exceeds threshold"""
        messagebox.showwarning(
            "Temperature Alert",
            f"Temperature exceeded threshold!\nCurrent: {temp_value:.1f}°C\nThreshold: {self.temp_threshold}°C"
        )
         
    def create_main_tab(self):
        """Create the Main tab with connection controls and data display"""
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Main")
        
        # Connection frame
        connection_frame = ttk.LabelFrame(self.main_tab, text="Connection")
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Port selection
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_combobox = ttk.Combobox(connection_frame, values=self.get_serial_ports())
        self.port_combobox.grid(row=0, column=1, padx=5, pady=5)
        
        # Baud rate selection
        ttk.Label(connection_frame, text="Baud Rate:").grid(row=0, column=2, padx=5, pady=5)
        self.baud_combobox = ttk.Combobox(connection_frame, values=[9600, 19200, 38400, 57600, 115200])
        self.baud_combobox.grid(row=0, column=3, padx=5, pady=5)
        self.baud_combobox.set("115200")
        
        # Connect/Disconnect button
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Status indicator
        self.status_label = ttk.Label(connection_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=5, pady=5)
        
        # Control frame - Simplified command buttons
        control_frame = ttk.LabelFrame(self.main_tab, text="Commands")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start button - sends command immediately
        self.start_button = ttk.Button(control_frame, text="Send START", command=self.send_start_command)
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Stop button - sends command immediately
        self.stop_button = ttk.Button(control_frame, text="Send STOP", command=self.send_stop_command)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Data display frame
        data_frame = ttk.LabelFrame(self.main_tab, text="Sensor Data")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for data display
        self.tree = ttk.Treeview(data_frame, columns=("A", "V", "D", "H"), show="headings")
        self.tree.heading("A", text="Acceleration")
        self.tree.heading("V", text="Velocity")
        self.tree.heading("D", text="Distance")
        self.tree.heading("H", text="Height")
        
        self.tree.column("A", width=200, anchor=tk.CENTER)
        self.tree.column("V", width=200, anchor=tk.CENTER)
        self.tree.column("D", width=200, anchor=tk.CENTER)
        self.tree.column("H", width=200, anchor=tk.CENTER)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
    

    def create_graph_tab(self):
        """Create the Graph tab with matplotlib visualization (without temperature)"""
        self.graph_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.graph_tab, text="Graph")
        
        # Control frame for graph options
        graph_control_frame = ttk.LabelFrame(self.graph_tab, text="Graph Controls")
        graph_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Sensor selection
        ttk.Label(graph_control_frame, text="Select Sensor:").pack(side=tk.LEFT, padx=5, pady=5)
        self.sensor_var = tk.StringVar()
        sensor_options = ["Acceleration", "Velocity", "Distance", "Height"]
        self.sensor_menu = ttk.OptionMenu(graph_control_frame, self.sensor_var, sensor_options[0], *sensor_options)
        self.sensor_menu.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Component selection
        ttk.Label(graph_control_frame, text="Component:").pack(side=tk.LEFT, padx=5, pady=5)
        self.component_var = tk.StringVar()
        self.component_menu = ttk.OptionMenu(graph_control_frame, self.component_var, "X", "X", "Y", "Z")
        self.component_menu.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Update button
        update_button = ttk.Button(graph_control_frame, text="Update Graph", command=self.update_graph)
        update_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Matplotlib figure
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
            "Height": {"X": [], "Y": [], "Z": []}
        }
        
    def get_serial_ports(self):
        """Get list of available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if not self.connected:
            port = self.port_combobox.get()
            baud = int(self.baud_combobox.get())
            try:
                self.serial_connection = serial.Serial(port, baud, timeout=1)
                self.connected = True
                self.connect_button.config(text="Disconnect")
                self.status_label.config(text="Connected", foreground="green")
                self.start_button.config(state=tk.NORMAL)
                # Start serial reading thread
                self.serial_thread = Thread(target=self.read_serial_data, daemon=True)
                self.serial_thread.start()
            except Exception as e:
                print(f"Connection error: {e}")
        else:
            self.disconnect()
    
    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connected = False
        self.connect_button.config(text="Connect")
        self.status_label.config(text="Disconnected", foreground="red")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
    
    def read_serial_data(self):
        """Read data from serial port in a separate thread"""
        while self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                line = self.serial_connection.readline().decode('utf-8').strip()
                if line:
                    self.serial_queue.put(line)
            except Exception as e:
                print(f"Serial read error: {e}")
                break
    
    def process_serial_data(self):
        """Process incoming serial data in the main thread"""
        while True:
            try:
                if not self.serial_queue.empty():
                    data = self.serial_queue.get()
                    self.update_ui(data)
                self.root.update()
            except Exception as e:
                print(f"UI update error: {e}")
    
    def update_ui(self, data):
        """Update the UI with new sensor data"""
        try:
            sensor_data = json.loads(data)
            
            # Update Main tab table
            self.tree.delete(*self.tree.get_children())
            
            # Extract values from JSON
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
            hy = sensor_data.get("HkDJ_1", "-")
            hz = sensor_data.get("HZZ_1", "-")
            
            temp = sensor_data.get("TEMP_1", None)
            
            # Insert data into treeview
            self.tree.insert("", tk.END, values=(f"X: {ax}", f"X: {vx}", f"X: {dx}", f"X: {hx}"))
            self.tree.insert("", tk.END, values=(f"Y: {ay}", f"Y: {vy}", f"Y: {dy}", f"Y: {hy}"))
            self.tree.insert("", tk.END, values=(f"Z: {az}", f"Z: {vz}", f"Z: {dz}", f"Z: {hz}"))
            
            # Update temperature display if available
            if temp is not None:
                self.update_temperature_display(temp)
            
            # Store data for graphing (excluding temperature)
            if isinstance(ax, (int, float)):
                self.graph_data["Acceleration"]["X"].append(ax)
                self.graph_data["Acceleration"]["Y"].append(ay)
                self.graph_data["Acceleration"]["Z"].append(az)
                
                self.graph_data["Velocity"]["X"].append(vx)
                self.graph_data["Velocity"]["Y"].append(vy)
                self.graph_data["Velocity"]["Z"].append(vz)
                
                self.graph_data["Distance"]["X"].append(dx)
                self.graph_data["Distance"]["Y"].append(dy)
                self.graph_data["Distance"]["Z"].append(dz)
                
                self.graph_data["Height"]["X"].append(hx)
                self.graph_data["Height"]["Y"].append(hy)
                self.graph_data["Height"]["Z"].append(hz)
                
                # Keep only the last 100 points for performance
                for sensor in self.graph_data.values():
                    for component in sensor.values():
                        if len(component) > 100:
                            component.pop(0)
            
        except json.JSONDecodeError:
            print("Invalid JSON data received")
        except Exception as e:
            print(f"Error updating UI: {e}")

    def send_start_command(self):
        """Send START_READING command to Arduino"""
        if self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"START_READING\n")
                print("Sent START_READING command")
            except Exception as e:
                print(f"Error sending START command: {e}")
    
    def send_stop_command(self):
        """Send STOP_READING command to Arduino"""
        if self.connected and self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(b"STOP_READING\n")
                print("Sent STOP_READING command")
            except Exception as e:
                print(f"Error sending STOP command: {e}")

    
    def update_graph(self):
        """Update the graph with selected data"""
        sensor = self.sensor_var.get()
        component = self.component_var.get()
        
        if sensor == "Temperature":
            component = "X"  # Temperature only has one component
            
        data = self.graph_data[sensor][component]
        
        self.ax.clear()
        self.ax.plot(data, label=f"{sensor} {component}")
        self.ax.set_title(f"{sensor} {component} over Time")
        self.ax.set_xlabel("Time (samples)")
        self.ax.set_ylabel("Value")
        self.ax.legend()
        self.ax.grid(True)
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = SensorDataGUI(root)
    root.mainloop()