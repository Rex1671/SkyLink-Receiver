import tkinter as tk
from tkinter import ttk
import socket
import threading
import time
import cv2
from PIL import Image, ImageTk
import sys
import os
import datetime

sys.path.append(os.getcwd())

try:
    from utils.sensor_receiver import SensorReceiver
    from utils.video_receiver import VideoReceiver
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from utils.sensor_receiver import SensorReceiver
    from utils.video_receiver import VideoReceiver

COLOR_BG = "#1e1e1e"
COLOR_FG = "#ffffff"
COLOR_ACCENT = "#007acc"
COLOR_SUCCESS = "#4ec9b0"
COLOR_WARNING = "#ce9178"
COLOR_PANEL = "#252526"
COLOR_BORDER = "#3e3e42"
FONT_MAIN = ("Segoe UI", 11)
FONT_HEADER = ("Segoe UI", 24, "bold")
FONT_MONO = ("Consolas", 10)

class DroneReceiverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Drone Stream Receiver Pro")
        self.root.geometry("1200x800")
        self.root.configure(bg=COLOR_BG)
        
        self.network_interfaces = self.detect_network_interfaces()
        _, self.ip_address = self.select_best_ip(self.network_interfaces)
        self.running = True
        self.current_camera = "back" 
        self.show_debug = True
        
        
        self.setup_styles()
        
        self.create_widgets()
        
        self.BASE_PORT = 5000
        self.setup_receivers()
        
        self.update_gui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Dark.TFrame", background=COLOR_BG)
        style.configure("Panel.TFrame", background=COLOR_PANEL, relief="flat")
        
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG, font=FONT_MAIN)
        style.configure("Header.TLabel", background=COLOR_BG, foreground=COLOR_SUCCESS, font=FONT_HEADER)
        style.configure("SubLabel.TLabel", background=COLOR_BG, foreground="#aaaaaa", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=COLOR_PANEL, foreground=COLOR_FG, font=FONT_MAIN)
        style.configure("Data.TLabel", background=COLOR_PANEL, foreground=COLOR_SUCCESS, font=FONT_MONO)
        
        style.configure("TButton", background=COLOR_ACCENT, foreground=COLOR_FG, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", "#0062a3")])
        
        style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_FG, bordercolor=COLOR_BORDER)
        style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR_FG)

    def detect_network_interfaces(self):
        """
        Parse ipconfig to find all adapters and their IPv4 addresses.
        Returns a dict: {'Adapter Name': 'IP Address'}
        """
        interfaces = {}
        import subprocess
        try:
            output = subprocess.check_output("ipconfig", shell=True, text=True)
            lines = output.split('\n')
            current_adapter = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if (line.startswith("Ethernet adapter") or line.startswith("Wireless LAN adapter")) and line.endswith(":"):
                    current_adapter = line.replace(":", "").strip()
                
                if current_adapter and "IPv4 Address" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        ip = parts[-1].strip()
                        if "(" in ip:
                            ip = ip.split("(")[0].strip()
                        interfaces[current_adapter] = ip
        except Exception as e:
            print(f"Error parsing ipconfig: {e}")
            
        return interfaces

    def select_best_ip(self, interfaces):
        """Select the most likely Wi-Fi IP, or fallback to any."""
       
        for name, ip in interfaces.items():
            if "wi-fi" in name.lower():
                return name, ip
        
        for name, ip in interfaces.items():
            if "wireless" in name.lower():
                return name, ip

        for name, ip in interfaces.items():
            if ip and not ip.startswith("127.") and not ip.startswith("169.254"):
                return name, ip
                
        return "Unknown", "127.0.0.1"

    def log_network_info(self):
        self.log("--- Network Interfaces Detected ---")
        if not self.network_interfaces:
            self.log("No network interfaces found via ipconfig.")
        else:
            for name, ip in self.network_interfaces.items():
                self.log(f"{name}: {ip}")
        self.log("-----------------------------------")
        self.log(f"Selected IP: {self.ip_address}")

    def create_widgets(self):
        main_container = ttk.Frame(self.root, style="Dark.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header_frame = ttk.Frame(main_container, style="Dark.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ip_frame = ttk.Frame(header_frame, style="Dark.TFrame")
        ip_frame.pack(side=tk.LEFT)
        
        ttk.Label(ip_frame, text="Select IP Address:", style="SubLabel.TLabel").pack(anchor="w")
        
        combo_values = [f"{name}: {ip}" for name, ip in self.network_interfaces.items()]
        
        self.ip_var = tk.StringVar()
        self.ip_combo = ttk.Combobox(ip_frame, textvariable=self.ip_var, values=combo_values, state="readonly", width=40, font=("Segoe UI", 12))
        self.ip_combo.pack(anchor="w", pady=(2, 0))
        
        best_name, best_ip = self.select_best_ip(self.network_interfaces)
        default_val = f"{best_name}: {best_ip}"
        if default_val in combo_values:
            self.ip_combo.set(default_val)
        elif combo_values:
             self.ip_combo.current(0)
             
        info_frame = ttk.Frame(header_frame, style="Panel.TFrame", padding=10)
        info_frame.pack(side=tk.RIGHT)
        
        self.create_port_label(info_frame, "Sensor", 5000)
        self.create_port_label(info_frame, "Camera Back", 5001)
        self.create_port_label(info_frame, "Camera Front", 5002)

        content_frame = ttk.Frame(main_container, style="Dark.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        video_panel = ttk.LabelFrame(content_frame, text=" Live Feed ", padding=2)
        video_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.video_canvas = tk.Canvas(video_panel, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        controls = ttk.Frame(video_panel, style="Dark.TFrame", padding=5)
        controls.pack(fill=tk.X)
        
        self.btn_back = ttk.Button(controls, text="Back Camera (Main)", command=lambda: self.set_camera("back"))
        self.btn_back.pack(side=tk.LEFT, padx=5)
        
        self.btn_front = ttk.Button(controls, text="Front Camera", command=lambda: self.set_camera("front"))
        self.btn_front.pack(side=tk.LEFT, padx=5)
        
        self.btn_both = ttk.Button(controls, text="Both Cameras", command=lambda: self.set_camera("both"))
        self.btn_both.pack(side=tk.LEFT, padx=5)
        
        self.lbl_cam_status = ttk.Label(controls, text="Waiting for stream...", foreground=COLOR_WARNING)
        self.lbl_cam_status.pack(side=tk.RIGHT, padx=5)

        data_panel = ttk.LabelFrame(content_frame, text=" Telemetry ", padding=10)
        data_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.lbl_fps_back = self.create_data_row(data_panel, "Back FPS:", "0", 0)
        self.lbl_fps_front = self.create_data_row(data_panel, "Front FPS:", "0", 1)
        self.lbl_sensor_rate = self.create_data_row(data_panel, "Sensor Rate:", "0 Hz", 2)
        
        ttk.Separator(data_panel, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        
        self.lbl_acc = self.create_data_row(data_panel, "Accel:", "0.00, 0.00, 0.00", 4)
        self.lbl_gyro = self.create_data_row(data_panel, "Gyro:", "0.00, 0.00, 0.00", 5)
        self.lbl_alt = self.create_data_row(data_panel, "Altitude:", "0.00 m", 6)
        self.lbl_roll = self.create_data_row(data_panel, "Roll:", "0.0°", 7)
        self.lbl_pitch = self.create_data_row(data_panel, "Pitch:", "0.0°", 8)
        self.lbl_yaw = self.create_data_row(data_panel, "Yaw:", "0.0°", 9)
        
        debug_frame = ttk.LabelFrame(main_container, text=" System Log ", padding=5)
        debug_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.log_text = tk.Text(debug_frame, height=6, bg="#111", fg="#ddd", font=("Consolas", 9), relief="flat")
        self.log_text.pack(fill=tk.BOTH)
        
    def create_port_label(self, parent, name, port):
        f = ttk.Frame(parent, style="Panel.TFrame")
        f.pack(anchor="w")
        ttk.Label(f, text=f"{name}:", style="Panel.TLabel", width=12).pack(side=tk.LEFT)
        ttk.Label(f, text=str(port), style="Data.TLabel", foreground="#4ec9b0").pack(side=tk.LEFT)

    def create_data_row(self, parent, label, value, row):
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        lbl = ttk.Label(parent, text=value, style="Data.TLabel", width=18)
        lbl.grid(row=row, column=1, sticky="e", pady=2, padx=(10, 0))
        return lbl

    def setup_receivers(self):
        self.log("Starting receivers...")
        self.sensor_receiver = SensorReceiver(port=self.BASE_PORT)
        
        self.back_receiver = VideoReceiver(port=self.BASE_PORT + 1, name="Back")
        self.front_receiver = VideoReceiver(port=self.BASE_PORT + 2, name="Front")
        
        self.sensor_receiver.start()
        self.back_receiver.start()
        self.front_receiver.start()
        self.log(f"Listening on ports: {self.BASE_PORT}-{self.BASE_PORT+2}")

    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def set_camera(self, camera_name):
        self.current_camera = camera_name
        self.log(f"Switched to {camera_name.title()} camera view")
        self.btn_back.configure(state="normal")
        self.btn_front.configure(state="normal")
        self.btn_both.configure(state="normal")
        
        if camera_name == "back":
            self.btn_back.configure(state="disabled")
        elif camera_name == "front":
            self.btn_front.configure(state="disabled")
        else:
            self.btn_both.configure(state="disabled")

    def update_gui(self):
        if not self.running:
            return

        frame = None
        
        if self.current_camera == "both":
            import numpy as np
            f_back = self.back_receiver.frame
            f_front = self.front_receiver.frame
            
            if f_back is None:
                f_back = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(f_back, "Back Cam Waiting...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            if f_front is None:
                f_front = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(f_front, "Front Cam Waiting...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
            h, w = f_back.shape[:2]
            f_front_resized = f_front
            if f_front.shape[0] != h:
                scale = h / f_front.shape[0]
                new_w = int(f_front.shape[1] * scale)
                f_front_resized = cv2.resize(f_front, (new_w, h))
            
            frame = np.hstack((f_back, f_front_resized))
            
            status = f"Back: {self.back_receiver.fps} FPS | Front: {self.front_receiver.fps} FPS"
            self.lbl_cam_status.configure(text=status, foreground=COLOR_SUCCESS)

        else:
            current_receiver = self.back_receiver if self.current_camera == "back" else self.front_receiver
            
            if current_receiver.frame is not None:
                frame = current_receiver.frame
                self.lbl_cam_status.configure(text=f"Connected ({current_receiver.fps} FPS)", foreground=COLOR_SUCCESS)
            else:
                self.lbl_cam_status.configure(text=f"Waiting for {self.current_camera} connection...", foreground=COLOR_WARNING)

        if frame is not None:
            c_w = self.video_canvas.winfo_width()
            c_h = self.video_canvas.winfo_height()
            
            if c_w > 10 and c_h > 10: 
                h, w = frame.shape[:2]
                scale = min(c_w/w, c_h/h)
                new_w, new_h = int(w*scale), int(h*scale)
                
                frame_resized = cv2.resize(frame, (new_w, new_h))
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.video_canvas.delete("all")
                x_center = c_w // 2
                y_center = c_h // 2
                self.video_canvas.create_image(x_center, y_center, anchor=tk.CENTER, image=imgtk)
                self.video_canvas.imgtk = imgtk
        else:
            self.video_canvas.delete("all")
            self.video_canvas.create_text(
                self.video_canvas.winfo_width()//2, 
                self.video_canvas.winfo_height()//2,
                text="NO SIGNAL", 
                fill="#444", 
                font=("Segoe UI", 20, "bold")
            )

        self.lbl_fps_back.configure(text=str(self.back_receiver.fps))
        self.lbl_fps_front.configure(text=str(self.front_receiver.fps))
        self.lbl_sensor_rate.configure(text=f"{self.sensor_receiver.rate} Hz")
        
        d = self.sensor_receiver.data
        if d:
            self.lbl_acc.configure(text=f"{d.acc[0]:.2f}, {d.acc[1]:.2f}, {d.acc[2]:.2f}")
            self.lbl_gyro.configure(text=f"{d.gyro[0]:.2f}, {d.gyro[1]:.2f}, {d.gyro[2]:.2f}")
            self.lbl_alt.configure(text=f"{d.altitude:.2f} m")
            self.lbl_roll.configure(text=f"{d.attitude[0]:.1f}°")
            self.lbl_pitch.configure(text=f"{d.attitude[1]:.1f}°")
            self.lbl_yaw.configure(text=f"{d.attitude[2]:.1f}°")

        
        if int(time.time()) % 2 == 0:
            pass 

        self.root.after(30, self.update_gui)

    def on_closing(self):
        self.running = False
        self.sensor_receiver.stop()
        self.back_receiver.stop()
        self.front_receiver.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DroneReceiverGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
