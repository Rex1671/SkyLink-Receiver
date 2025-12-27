"""
Sensor Data Receiver - Receives IMU and attitude data over UDP
"""

import socket
import threading
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class SensorData:
    """Container for sensor data from Android device."""
    timestamp: int = 0
    acc: tuple = (0.0, 0.0, 0.0)      # Accelerometer (m/s²)
    gyro: tuple = (0.0, 0.0, 0.0)     # Gyroscope (rad/s)
    attitude: tuple = (0.0, 0.0, 0.0)  # Roll, Pitch, Yaw (degrees)
    altitude: float = 0.0              # Relative altitude (meters)
    frame_id: int = 0
    
    @classmethod
    def from_json(cls, data: dict) -> 'SensorData':
        """Create SensorData from JSON dictionary."""
        imu = data.get('imu', {})
        return cls(
            timestamp=data.get('ts', 0),
            acc=tuple(imu.get('acc', [0, 0, 0])),
            gyro=tuple(imu.get('gyro', [0, 0, 0])),
            attitude=tuple(data.get('attitude', [0, 0, 0])),
            altitude=data.get('altitude', 0.0),
            frame_id=data.get('frame_id', 0)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'acc': self.acc,
            'gyro': self.gyro,
            'attitude': self.attitude,
            'altitude': self.altitude,
            'frame_id': self.frame_id
        }


class SensorReceiver(threading.Thread):
    """
    Receives sensor data over UDP in a background thread.
    
    Usage:
        receiver = SensorReceiver(port=5000)
        receiver.start()
        
        # Access latest data
        data = receiver.data
        print(f"Acceleration: {data.acc}")
        
        # Stop when done
        receiver.stop()
    """
    
    def __init__(self, port: int = 5000, callback: Optional[Callable] = None):
        """
        Initialize sensor receiver.
        
        Args:
            port: UDP port to listen on
            callback: Optional callback function called on each packet
        """
        super().__init__(daemon=True)
        self.port = port
        self.callback = callback
        self.running = True
        
        # Latest sensor data
        self.data = SensorData()
        
        # Statistics
        self.packet_count = 0
        self.rate = 0  # Packets per second
        self._last_rate_time = time.time()
        self._rate_counter = 0
        
        # Socket
        self._socket: Optional[socket.socket] = None
    
    def run(self):
        """Main receiver loop (runs in background thread)."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('0.0.0.0', self.port))
        self._socket.settimeout(1.0)
        
        print(f"📡 Sensor receiver listening on port {self.port}")
        
        while self.running:
            try:
                data, addr = self._socket.recvfrom(4096)
                self._process_packet(data)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Sensor receiver error: {e}")
        
        self._socket.close()
        print("📡 Sensor receiver stopped")
    
    def _process_packet(self, data: bytes):
        """Process received UDP packet."""
        try:
            json_data = json.loads(data.decode('utf-8'))
            self.data = SensorData.from_json(json_data)
            
            self.packet_count += 1
            self._rate_counter += 1
            
            # Update rate every second
            now = time.time()
            if now - self._last_rate_time >= 1.0:
                self.rate = self._rate_counter
                self._rate_counter = 0
                self._last_rate_time = now
            
            # Call callback if set
            if self.callback:
                self.callback(self.data)
                
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
        except Exception as e:
            print(f"Error processing sensor data: {e}")
    
    def stop(self):
        """Stop the receiver."""
        self.running = False
    
    def get_stats(self) -> dict:
        """Get receiver statistics."""
        return {
            'packets': self.packet_count,
            'rate_hz': self.rate
        }