# SkyLink Receiver

**SkyLink Receiver** is a powerful Python-based ground station dashboard designed for receiving high-speed video feeds and telemetry from Android devices on drones or robotics platforms.

It features a modern dark-themed GUI, dual-camera support (Split View), and intelligent network tools to make connecting to your drone easier than ever.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Key Features

*   **Dual Stream Monitoring**: View **Front** and **Back** camera feeds simultaneously in a side-by-side split view.
*   **Real-time Telemetry**: High-frequency updates for Accelerometer, Gyroscope, Altitude, and Attitude (Roll/Pitch/Yaw) data.
*   **Modern Dashboard**: A professional dark-mode interface built with Tkinter for low-light legibility.
*   **Smart IP Detection**: Automatically scans your network adapters to find and prioritize your Wi-Fi IP address, preventing connection errors.
*   **Robust Logging**: Integrated system log console to troubleshoot network interface and connection issues in real-time.

## 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Rex1671/SkyLink-Receiver.git
    cd SkyLink-Receiver
    ```

2.  **Install Dependencies**
    You will need Python 3 installed. Install the required libraries:
    ```bash
    pip install opencv-python numpy pillow
    ```
    *(Note: `tkinter` is usually included with Python standard installations)*

## 🚀 Usage

1.  **Start the Receiver**
    Run the GUI application:
    ```bash
    python receiver_gui.py
    ```

2.  **Connect Your Drone/Android App**
    *   Look at the **"Select IP Address"** dropdown at the top of the window.
    *   Select your Wi-Fi IP (usually starts with `192.168...`).
    *   Enter this IP in your Android Drone App as the **Target IP**.
    *   Ensure the ports match:
        *   **Sensor Port**: 5000
        *   **Back Camera**: 5001
        *   **Front Camera**: 5002

3.  **Monitor Feed**
    *   Use the buttons to switch between **Back**, **Front**, or **Both Cameras** (Split View).
    *   Watch the Telemetry panel on the right for sensor data.

## 🔧 Troubleshooting

*   **"Waiting for stream..."**:
    *   Check if your Android device and PC are on the **same Wi-Fi network**.
    *   Verify the **Target IP** on the phone matches the IP selected in the Receiver GUI.
    *   **Firewall**: Ensure Windows Firewall is not blocking Python from receiving UDP packets. You may need to allow `python.exe` for private/public networks.
*   **Wrong IP detected?**:
    *   Check the **System Log** at the bottom of the window application. It lists all detected network adapters. Select the correct one manually from the dropdown.

## 📁 Project Structure

*   `receiver_gui.py`: Main application entry point.
*   `utils/`:
    *   `video_receiver.py`: Handles threaded UDP video packet reassembly and decoding.
    *   `sensor_receiver.py`: Handles high-speed UDP sensor data parsing.
    *   `frame_buffer.py`: Manages frame chunks for smooth playback.

---
**Happy Flying! 🚁**
