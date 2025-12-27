#!/usr/bin/env python3
"""
Simple Console Receiver - No OpenCV required
Displays sensor data and frame statistics in terminal

Usage:
    python receiver_simple.py
    python receiver_simple.py --port 5000
"""

import argparse
import socket
import threading
import json
import struct
import time
import sys
import os
from collections import defaultdict
from dataclasses import dataclass


# Ports
DEFAULT_SENSOR_PORT = 5000
DEFAULT_VIDEO_BACK_PORT = 5001
DEFAULT_VIDEO_FRONT_PORT = 5002

# Header size for video packets
HEADER_SIZE = 29


@dataclass
class Stats:
    """Statistics container."""
    sensor_packets: int = 0
    sensor_rate: int = 0
    back_frames: int = 0
    back_fps: int = 0
    back_bytes: int = 0
    front_frames: int = 0
    front_fps: int = 0
    front_bytes: int = 0


class SimpleReceiver:
    """Simple receiver that just counts packets and displays stats."""
    
    def __init__(self, sensor_port: int, video_back_port: int, video_front_port: int):
        self.sensor_port = sensor_port
        self.video_back_port = video_back_port
        self.video_front_port = video_front_port
        
        self.running = True
        self.stats = Stats()
        self.latest_sensor = {}
        
        # Rate counters
        self._sensor_counter = 0
        self._back_counter = 0
        self._front_counter = 0
        self._last_time = time.time()
        
        # Frame buffers for reassembly
        self._back_buffer = defaultdict(dict)
        self._front_buffer = defaultdict(dict)
    
    def start(self):
        """Start all receiver threads."""
        threading.Thread(target=self._sensor_thread, daemon=True).start()
        threading.Thread(target=self._video_thread, 
                        args=(self.video_back_port, 'back'), daemon=True).start()
        threading.Thread(target=self._video_thread, 
                        args=(self.video_front_port, 'front'), daemon=True).start()
        threading.Thread(target=self._stats_thread, daemon=True).start()
    
    def _sensor_thread(self):
        """Receive sensor data."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.sensor_port))
        sock.settimeout(1.0)
        
        print(f"📡 Sensor receiver on port {self.sensor_port}")
        
        while self.running:
            try:
                data, _ = sock.recvfrom(4096)
                self.latest_sensor = json.loads(data.decode())
                self.stats.sensor_packets += 1
                self._sensor_counter += 1
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    print(f"Sensor error: {e}")
    
    def _video_thread(self, port: int, camera: str):
        """Receive video data."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4*1024*1024)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(1.0)
        
        print(f"🎥 {camera.upper()} camera receiver on port {port}")
        
        buffer = self._back_buffer if camera == 'back' else self._front_buffer
        
        while self.running:
            try:
                data, _ = sock.recvfrom(65535)
                if len(data) < HEADER_SIZE:
                    continue
                
                # Parse header
                frame_id = struct.unpack('>Q', data[1:9])[0]
                chunk_idx = struct.unpack('>I', data[9:13])[0]
                total_chunks = struct.unpack('>I', data[13:17])[0]
                data_len = struct.unpack('>I', data[25:29])[0]
                
                # Track bytes
                if camera == 'back':
                    self.stats.back_bytes += len(data)
                else:
                    self.stats.front_bytes += len(data)
                
                # Add chunk to buffer
                buffer[frame_id][chunk_idx] = True
                
                # Check if frame complete
                if len(buffer[frame_id]) == total_chunks:
                    if camera == 'back':
                        self.stats.back_frames += 1
                        self._back_counter += 1
                    else:
                        self.stats.front_frames += 1
                        self._front_counter += 1
                    del buffer[frame_id]
                
                # Cleanup old frames
                old = [fid for fid in buffer if frame_id - fid > 10]
                for fid in old:
                    del buffer[fid]
                    
            except socket.timeout:
                pass
            except Exception as e:
                if self.running:
                    print(f"{camera} error: {e}")
    
    def _stats_thread(self):
        """Update rates every second."""
        while self.running:
            time.sleep(1)
            self.stats.sensor_rate = self._sensor_counter
            self.stats.back_fps = self._back_counter
            self.stats.front_fps = self._front_counter
            self._sensor_counter = 0
            self._back_counter = 0
            self._front_counter = 0
    
    def stop(self):
        """Stop all receivers."""
        self.running = False
    
    def display(self):
        """Display current stats."""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 60)
        print("  📱 ANDROID SENSOR STREAM RECEIVER")
        print("=" * 60)
        print(f"  Sensor Port:  {self.sensor_port}")
        print(f"  Back Port:    {self.video_back_port}")
        print(f"  Front Port:   {self.video_front_port}")
        print("-" * 60)
        print(f"  Sensor Rate:    {self.stats.sensor_rate:4d} Hz")
        print(f"  Sensor Packets: {self.stats.sensor_packets}")
        print("-" * 60)
        print(f"  Back Camera:    {self.stats.back_fps:4d} FPS  |  "
              f"{self.stats.back_frames} frames  |  "
              f"{self.stats.back_bytes / 1024 / 1024:.1f} MB")
        print(f"  Front Camera:   {self.stats.front_fps:4d} FPS  |  "
              f"{self.stats.front_frames} frames  |  "
              f"{self.stats.front_bytes / 1024 / 1024:.1f} MB")
        print("-" * 60)
        
        # Display sensor data
        if self.latest_sensor:
            imu = self.latest_sensor.get('imu', {})
            acc = imu.get('acc', [0, 0, 0])
            gyro = imu.get('gyro', [0, 0, 0])
            att = self.latest_sensor.get('attitude', [0, 0, 0])
            alt = self.latest_sensor.get('altitude', 0)
            
            print(f"  Accel (m/s²):  X:{acc[0]:7.2f}  Y:{acc[1]:7.2f}  Z:{acc[2]:7.2f}")
            print(f"  Gyro (rad/s):  X:{gyro[0]:7.3f}  Y:{gyro[1]:7.3f}  Z:{gyro[2]:7.3f}")
            print(f"  Attitude (°):  R:{att[0]:7.1f}  P:{att[1]:7.1f}  Y:{att[2]:7.1f}")
            print(f"  Altitude:      {alt:.2f} m")
        else:
            print("  Waiting for sensor data...")
        
        print("=" * 60)
        print("  Press Ctrl+C to stop")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Android Stream Receiver (Console)')
    parser.add_argument('--port', type=int, default=DEFAULT_SENSOR_PORT,
                       help='Base port number (default: 5000)')
    args = parser.parse_args()
    
    receiver = SimpleReceiver(
        sensor_port=args.port,
        video_back_port=args.port + 1,
        video_front_port=args.port + 2
    )
    
    receiver.start()
    
    try:
        while True:
            receiver.display()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        receiver.stop()


if __name__ == "__main__":
    main()