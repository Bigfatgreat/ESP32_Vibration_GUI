import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
from tkinter import messagebox

# ---------- SERIAL ----------
esp = None

def get_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def refresh_ports():
    ports = get_ports()
    port_menu.configure(values=ports)
    if ports:
        port_menu.set(ports[0])

def connect_serial():
    global esp
    try:
        port = port_menu.get()
        baud = int(baud_menu.get())
        esp = serial.Serial(port, baud, timeout=1)
        status_label.configure(text=f"✅ Connected to {port}", text_color="green")
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))
        status_label.configure(text="❌ Failed to connect", text_color="red")

def disconnect_serial():
    global esp
    if esp and esp.is_open:
        esp.close()
        status_label.configure(text="🔌 Disconnected", text_color="gray")

# ---------- LOG ----------
def get_log():
    if not esp or not esp.is_open:
        messagebox.showwarning("Warning", "No ESP32 connected!")
        return

    log_textbox.delete("0.0", "end")
    esp.reset_input_buffer()
    esp.write(b'GET_LOG\n')
    time.sleep(1)

    while esp.in_waiting:
        line = esp.readline().decode('utf-8', errors='ignore')
        log_textbox.insert("end", line)

def refresh_log_threaded():
    threading.Thread(target=get_log).start()

def clear_log():
    if not esp or not esp.is_open:
        messagebox.showwarning("Warning", "No ESP32 connected!")
        return

    esp.write(b'CLEAR_LOG\n')
    time.sleep(0.5)
    log_textbox.delete("0.0", "end")
    messagebox.showinfo("Done", "Log cleared on ESP32")

# ---------- GUI ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("ESP32 Serial Logger")
app.geometry("700x650")

tabs = ctk.CTkTabview(app, width=680, height=420)
tabs.pack(pady=10, padx=10)
tabs.add("🔌 Connect")
tabs.add("📄 Data Log")
tabs.add("⚙️ Settings")

# ---------- Tab 1: Connect ----------
tab1 = tabs.tab("🔌 Connect")

port_label = ctk.CTkLabel(tab1, text="Select COM Port:")
port_label.pack(pady=5)

port_menu = ctk.CTkOptionMenu(tab1, values=[])
port_menu.pack()

baud_label = ctk.CTkLabel(tab1, text="Baud Rate:")
baud_label.pack(pady=5)

baud_menu = ctk.CTkOptionMenu(tab1, values=["9600", "115200", "230400"])
baud_menu.set("115200")
baud_menu.pack()

connect_button = ctk.CTkButton(tab1, text="✅ Connect", command=connect_serial)
connect_button.pack(pady=10)

disconnect_button = ctk.CTkButton(tab1, text="❌ Disconnect", command=disconnect_serial)
disconnect_button.pack()

refresh_button = ctk.CTkButton(tab1, text="🔁 Refresh Ports", command=refresh_ports)
refresh_button.pack(pady=10)

status_label = ctk.CTkLabel(tab1, text="Not connected", text_color="gray")
status_label.pack(pady=10)

# ---------- Tab 2: Log Viewer ----------
tab2 = tabs.tab("📄 Data Log")

log_textbox = ctk.CTkTextbox(tab2, width=650, height=300)
log_textbox.pack(pady=10)

fetch_button = ctk.CTkButton(tab2, text="📥 Fetch Log", command=refresh_log_threaded)
fetch_button.pack(pady=5)

clear_button = ctk.CTkButton(tab2, text="🗑️ Clear Log", command=clear_log)
clear_button.pack(pady=5)

# ---------- Tab 3: Setting  ----------
tab3 = tabs.tab("⚙️ Settings")

write_entry = ctk.CTkEntry(tab3, width=300, placeholder_text="Enter value to send")
write_entry.pack(pady=10)

def send_value():
    if esp and esp.is_open:
        val = write_entry.get()
        if val:
            esp.write(f"SET:{val}\n".encode())
            status_output.configure(text=f"Sent: {val}")
        else:
            status_output.configure(text="Input is empty")

send_button = ctk.CTkButton(tab3, text="📤 Send to ESP32", command=send_value)
send_button.pack(pady=5)

def read_value():
    if esp and esp.is_open:
        esp.reset_input_buffer()
        esp.write(b"GET_VALUE\n")
        time.sleep(0.5)
        result = esp.readline().decode(errors='ignore')
        status_output.configure(text=f"Received: {result.strip()}")

read_button = ctk.CTkButton(tab3, text="📥 Read from ESP32", command=read_value)
read_button.pack(pady=5)

status_output = ctk.CTkLabel(tab3, text="Status will appear here")
status_output.pack(pady=10)

# Load ports on start
refresh_ports()

app.mainloop()
