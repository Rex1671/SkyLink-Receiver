"""
Dual Camera Receiver - Display both cameras with multiple view modes

Usage:
    python receiver_dual.py
    python receiver_dual.py --port 5000

Controls:
    q - Quit
    1 - Back camera only
    2 - Front camera only
    3 - Side by side view
    4 - Picture in picture (Back main)
    5 - Picture in picture (Front main)
    s - Save screenshot
    f - Toggle fullscreen
"""

import argparse
import sys
import time
from enum import IntEnum

try:
    import cv2
    import numpy as np
except ImportError:
    print("Error: OpenCV not installed!")
    print("Run: pip install opencv-python numpy")
    sys.exit(1)

from utils import SensorReceiver, VideoReceiver


DEFAULT_SENSOR_PORT = 5000
DEFAULT_VIDEO_BACK_PORT = 5001
DEFAULT_VIDEO_FRONT_PORT = 5002


class DisplayMode(IntEnum):
    BACK_ONLY = 1
    FRONT_ONLY = 2
    SIDE_BY_SIDE = 3
    PIP_BACK_MAIN = 4
    PIP_FRONT_MAIN = 5


def draw_overlay(frame, sensor_data, fps, camera_name, sensor_rate, compact=False):
    """Draw sensor data overlay on frame."""
    if compact:
        cv2.putText(frame, f"{camera_name} {fps}fps", 
                   (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        return frame
    
    h, w = frame.shape[:2]
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (290, 165), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    y = 25
    cv2.putText(frame, f"{camera_name} | {fps} FPS | Sensor: {sensor_rate} Hz", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    d = sensor_data
    y += 25
    cv2.putText(frame, f"Accel:  X:{d.acc[0]:6.2f}  Y:{d.acc[1]:6.2f}  Z:{d.acc[2]:6.2f}", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    y += 20
    cv2.putText(frame, f"Gyro:   X:{d.gyro[0]:6.3f}  Y:{d.gyro[1]:6.3f}  Z:{d.gyro[2]:6.3f}", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    y += 20
    cv2.putText(frame, f"Roll: {d.attitude[0]:6.1f}  Pitch: {d.attitude[1]:6.1f}  Yaw: {d.attitude[2]:6.1f}", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    y += 20
    cv2.putText(frame, f"Altitude: {d.altitude:.2f} m", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    y += 20
    cv2.putText(frame, f"Timestamp: {d.timestamp}", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (128, 128, 128), 1)
    
    return frame


def create_waiting_frame(width=640, height=480, text="Waiting..."):
    """Create a placeholder frame."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
    x = (width - text_size[0]) // 2
    y = (height + text_size[1]) // 2
    cv2.putText(frame, text, (x, y), font, 0.7, (255, 255, 255), 2)
    return frame


def resize_to_height(frame, target_height):
    """Resize frame to target height maintaining aspect ratio."""
    h, w = frame.shape[:2]
    if h == target_height:
        return frame
    scale = target_height / h
    new_width = int(w * scale)
    return cv2.resize(frame, (new_width, target_height))


def create_pip_view(main_frame, pip_frame, pip_label, pip_fps):
    """Create picture-in-picture view."""
    h, w = main_frame.shape[:2]
    
    pip_w, pip_h = w // 4, h // 4
    pip_resized = cv2.resize(pip_frame, (pip_w, pip_h))
    
    cv2.rectangle(pip_resized, (0, 0), (pip_w-1, pip_h-1), (255, 255, 255), 2)
    
    cv2.putText(pip_resized, f"{pip_label} {pip_fps}fps", 
               (5, pip_h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    margin = 10
    main_frame[margin:margin+pip_h, w-pip_w-margin:w-margin] = pip_resized
    
    return main_frame


def draw_mode_indicator(frame, mode):
    """Draw current mode indicator."""
    mode_names = {
        DisplayMode.BACK_ONLY: "BACK ONLY (1)",
        DisplayMode.FRONT_ONLY: "FRONT ONLY (2)",
        DisplayMode.SIDE_BY_SIDE: "SIDE BY SIDE (3)",
        DisplayMode.PIP_BACK_MAIN: "PIP - BACK MAIN (4)",
        DisplayMode.PIP_FRONT_MAIN: "PIP - FRONT MAIN (5)",
    }
    
    h, w = frame.shape[:2]
    text = mode_names.get(mode, "UNKNOWN")
    
    cv2.putText(frame, text, (w - 200, h - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
    
    return frame


def main():
    parser = argparse.ArgumentParser(description='Android Dual Camera Receiver')
    parser.add_argument('--port', type=int, default=DEFAULT_SENSOR_PORT,
                       help='Base port number (default: 5000)')
    args = parser.parse_args()
    
    sensor_port = args.port
    back_port = args.port + 1
    front_port = args.port + 2
    
    print("=" * 60)
    print("  📱 Android Dual Camera Stream Receiver")
    print("=" * 60)
    print(f"  Sensor Port:       {sensor_port}")
    print(f"  Back Camera Port:  {back_port}")
    print(f"  Front Camera Port: {front_port}")
    print("=" * 60)
    print("  Controls:")
    print("    q - Quit")
    print("    1 - Back camera only")
    print("    2 - Front camera only")
    print("    3 - Side by side")
    print("    4 - PIP (Back main)")
    print("    5 - PIP (Front main)")
    print("    s - Save screenshot")
    print("    f - Toggle fullscreen")
    print("=" * 60)
    
    sensor_receiver = SensorReceiver(port=sensor_port)
    back_receiver = VideoReceiver(port=back_port, name="Back")
    front_receiver = VideoReceiver(port=front_port, name="Front")
    
    sensor_receiver.start()
    back_receiver.start()
    front_receiver.start()
    
    time.sleep(0.5)
    
    window_name = 'Android Dual Camera Stream'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 480)
    
    display_mode = DisplayMode.SIDE_BY_SIDE
    fullscreen = False
    screenshot_count = 0
    
    try:
        while True:
            back_frame = back_receiver.frame
            front_frame = front_receiver.frame
            sensor = sensor_receiver.data
            
            if display_mode == DisplayMode.BACK_ONLY:
                if back_frame is not None:
                    frame = back_frame.copy()
                    frame = draw_overlay(frame, sensor, back_receiver.fps, 
                                        "BACK", sensor_receiver.rate)
                else:
                    frame = create_waiting_frame(text="Waiting for Back Camera...")
                    
            elif display_mode == DisplayMode.FRONT_ONLY:
                if front_frame is not None:
                    frame = front_frame.copy()
                    frame = draw_overlay(frame, sensor, front_receiver.fps, 
                                        "FRONT", sensor_receiver.rate)
                else:
                    frame = create_waiting_frame(text="Waiting for Front Camera...")
                    
            elif display_mode == DisplayMode.SIDE_BY_SIDE:
                if back_frame is not None:
                    back = back_frame.copy()
                    back = draw_overlay(back, sensor, back_receiver.fps, 
                                       "BACK", sensor_receiver.rate)
                else:
                    back = create_waiting_frame(text="Back: Waiting...")
                
                if front_frame is not None:
                    front = front_frame.copy()
                    front = draw_overlay(front, sensor, front_receiver.fps, 
                                        "FRONT", sensor_receiver.rate)
                else:
                    front = create_waiting_frame(text="Front: Waiting...")
                
                target_h = max(back.shape[0], front.shape[0])
                back = resize_to_height(back, target_h)
                front = resize_to_height(front, target_h)
                
                frame = np.hstack([back, front])
                
            elif display_mode == DisplayMode.PIP_BACK_MAIN:
                if back_frame is not None:
                    frame = back_frame.copy()
                    frame = draw_overlay(frame, sensor, back_receiver.fps, 
                                        "BACK", sensor_receiver.rate)
                else:
                    frame = create_waiting_frame(text="Back: Waiting...")
                
                if front_frame is not None:
                    frame = create_pip_view(frame, front_frame, "FRONT", front_receiver.fps)
                    
            elif display_mode == DisplayMode.PIP_FRONT_MAIN:
                if front_frame is not None:
                    frame = front_frame.copy()
                    frame = draw_overlay(frame, sensor, front_receiver.fps, 
                                        "FRONT", sensor_receiver.rate)
                else:
                    frame = create_waiting_frame(text="Front: Waiting...")
                
                if back_frame is not None:
                    frame = create_pip_view(frame, back_frame, "BACK", back_receiver.fps)
            
            frame = draw_mode_indicator(frame, display_mode)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('1'):
                display_mode = DisplayMode.BACK_ONLY
                cv2.resizeWindow(window_name, 800, 600)
                print("Mode: Back camera only")
            elif key == ord('2'):
                display_mode = DisplayMode.FRONT_ONLY
                cv2.resizeWindow(window_name, 800, 600)
                print("Mode: Front camera only")
            elif key == ord('3'):
                display_mode = DisplayMode.SIDE_BY_SIDE
                cv2.resizeWindow(window_name, 1280, 480)
                print("Mode: Side by side")
            elif key == ord('4'):
                display_mode = DisplayMode.PIP_BACK_MAIN
                cv2.resizeWindow(window_name, 800, 600)
                print("Mode: PIP (Back main)")
            elif key == ord('5'):
                display_mode = DisplayMode.PIP_FRONT_MAIN
                cv2.resizeWindow(window_name, 800, 600)
                print("Mode: PIP (Front main)")
            elif key == ord('s'):
                filename = f"screenshot_{screenshot_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Saved: {filename}")
                screenshot_count += 1
            elif key == ord('f'):
                fullscreen = not fullscreen
                if fullscreen:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 
                                         cv2.WINDOW_FULLSCREEN)
                else:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 
                                         cv2.WINDOW_NORMAL)
                    
    except KeyboardInterrupt:
        pass
    
    print("\nStopping...")
    sensor_receiver.stop()
    back_receiver.stop()
    front_receiver.stop()
    cv2.destroyAllWindows()
    
    print("\n📊 Final Statistics:")
    print(f"  Sensor: {sensor_receiver.packet_count} packets")
    print(f"  Back:   {back_receiver.frame_count} frames")
    print(f"  Front:  {front_receiver.frame_count} frames")


if __name__ == "__main__":
    main()
