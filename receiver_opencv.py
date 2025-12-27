#!/usr/bin/env python3
"""
OpenCV Receiver - Single camera display with sensor overlay

Usage:
    python receiver_opencv.py
    python receiver_opencv.py --port 5000 --camera back
    python receiver_opencv.py --camera front
"""

import argparse
import sys
import time

try:
    import cv2
    import numpy as np
except ImportError:
    print("Error: OpenCV not installed!")
    print("Run: pip install opencv-python numpy")
    sys.exit(1)

from utils import SensorReceiver, VideoReceiver


# Default ports
DEFAULT_SENSOR_PORT = 5000
DEFAULT_VIDEO_BACK_PORT = 5001
DEFAULT_VIDEO_FRONT_PORT = 5002


def draw_overlay(frame, sensor_data, fps, camera_name, sensor_rate):
    """Draw sensor data overlay on frame."""
    h, w = frame.shape[:2]
    
    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (280, 160), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Title
    y = 25
    cv2.putText(frame, f"{camera_name} | {fps} FPS | Sensor: {sensor_rate} Hz", 
               (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Sensor data
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


def create_waiting_frame(width=640, height=480, text="Waiting for stream..."):
    """Create a placeholder frame."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Draw text centered
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 0.8, 2)[0]
    x = (width - text_size[0]) // 2
    y = (height + text_size[1]) // 2
    cv2.putText(frame, text, (x, y), font, 0.8, (255, 255, 255), 2)
    
    return frame


def main():
    parser = argparse.ArgumentParser(description='Android Stream Receiver (OpenCV)')
    parser.add_argument('--port', type=int, default=DEFAULT_SENSOR_PORT,
                       help='Base port number (default: 5000)')
    parser.add_argument('--camera', choices=['back', 'front'], default='back',
                       help='Which camera to display (default: back)')
    args = parser.parse_args()
    
    # Calculate ports
    sensor_port = args.port
    video_port = args.port + 1 if args.camera == 'back' else args.port + 2
    camera_name = args.camera.upper()
    
    print("=" * 50)
    print(f"  📱 Android Stream Receiver - {camera_name} Camera")
    print("=" * 50)
    print(f"  Sensor Port: {sensor_port}")
    print(f"  Video Port:  {video_port}")
    print("=" * 50)
    print("  Press 'q' to quit")
    print("  Press 's' to save screenshot")
    print("=" * 50)
    
    # Start receivers
    sensor_receiver = SensorReceiver(port=sensor_port)
    video_receiver = VideoReceiver(port=video_port, name=camera_name)
    
    sensor_receiver.start()
    video_receiver.start()
    
    # Create window
    window_name = f'Android Stream - {camera_name}'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 800, 600)
    
    screenshot_count = 0
    
    try:
        while True:
            # Get latest frame
            if video_receiver.frame is not None:
                frame = video_receiver.frame.copy()
                frame = draw_overlay(
                    frame,
                    sensor_receiver.data,
                    video_receiver.fps,
                    camera_name,
                    sensor_receiver.rate
                )
            else:
                frame = create_waiting_frame()
            
            cv2.imshow(window_name, frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save screenshot
                filename = f"screenshot_{camera_name}_{screenshot_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Saved: {filename}")
                screenshot_count += 1
                
    except KeyboardInterrupt:
        pass
    
    print("\nStopping...")
    sensor_receiver.stop()
    video_receiver.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()