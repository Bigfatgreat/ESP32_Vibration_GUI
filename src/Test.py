import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import time

esp = None

# ========== Serial Handling ==========
def get_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def refresh_ports():
    port_list = get_ports()
    port_combo['values'] = port_list
    if port_list:
        port_combo.current(0)

def connect_serial():
    global esp
    selected_port = port_combo.get()
    try:
        esp = serial.Serial(selected_port, 115200, timeout=1)
        status_label.config(text=f"Connected to {selected_port}", foreground="green")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))
        status_label.config(text="Failed to connect", foreground="red")

def disconnect_serial():
    global esp
    if esp and esp.is_open:
        esp.close()
        status_label.config(text="Disconnected", foreground="gray")


# ========== Data Log Tab ==========
def get_log():
    if not esp or not esp.is_open:
        messagebox.showwarning("Warning", "No ESP32 connected!")
        return

    log_text.delete(1.0, tk.END)
    esp.reset_input_buffer()
    esp.write(b'GET_LOG\n')
    time.sleep(1)

    while esp.in_waiting:
        line = esp.readline().decode('utf-8', errors='ignore')
        log_text.insert(tk.END, line)

def refresh_log_threaded():
    thread = threading.Thread(target=get_log)
    thread.start()

# ========== GUI ==========
root = tk.Tk()
root.title("ESP32 Serial Logger")
root.geometry("600x400")

# Notebook (Tabs)
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# -------- Tab 1: COM Port Selector --------
tab1 = ttk.Frame(notebook)
notebook.add(tab1, text="COM Selector")

frame = tk.Frame(tab1, padx=10, pady=10)
frame.pack()

tk.Label(frame, text="Select COM Port:").grid(row=0, column=0, sticky="w")
port_combo = ttk.Combobox(frame, state="readonly", width=30)
port_combo.grid(row=0, column=1, padx=5)

refresh_button = tk.Button(frame, text="🔁 Refresh", command=refresh_ports)
refresh_button.grid(row=0, column=2)

connect_button = tk.Button(frame, text="✅ Connect", command=connect_serial)
connect_button.grid(row=1, column=1, pady=10)

status_label = tk.Label(tab1, text="Not connected", fg="red")
status_label.pack()

disconnect_button = tk.Button(frame, text="❌ Disconnect", command=disconnect_serial)
disconnect_button.grid(row=2, column=1, pady=5)


# -------- Tab 2: Data Log --------
tab2 = ttk.Frame(notebook)
notebook.add(tab2, text="📄 Data Log")

log_text = scrolledtext.ScrolledText(tab2, width=70, height=20)
log_text.pack(pady=10)

btn_fetch = tk.Button(tab2, text="📥 Fetch Log", command=refresh_log_threaded)
btn_fetch.pack()

# Start with available ports
refresh_ports()

root.mainloop()
