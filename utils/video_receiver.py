"""
Video Stream Receiver - Receives video frames over UDP
"""

import socket
import threading
import struct
import time
from typing import Optional, Callable
import numpy as np

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from .frame_buffer import FrameBuffer


# Packet header format:
# [CAMERA_ID(1) | FRAME_ID(8) | CHUNK_IDX(4) | TOTAL_CHUNKS(4) | TIMESTAMP(8) | DATA_LEN(4)]
HEADER_SIZE = 29

# Camera IDs
CAMERA_BACK = 0
CAMERA_FRONT = 1


class VideoReceiver(threading.Thread):
    """
    Receives video frames over UDP in a background thread.
    
    Handles chunked frame reassembly for large frames that exceed
    UDP packet size limits.
    
    Usage:
        receiver = VideoReceiver(port=5001, name="Back Camera")
        receiver.start()
        
        # Access latest frame
        if receiver.frame is not None:
            cv2.imshow('Video', receiver.frame)
        
        # Stop when done
        receiver.stop()
    """
    
    def __init__(self, port: int, name: str = "Camera",
                 callback: Optional[Callable] = None,
                 buffer_size: int = 4 * 1024 * 1024):
        """
        Initialize video receiver.
        
        Args:
            port: UDP port to listen on
            name: Display name for this camera
            callback: Optional callback(frame, timestamp, frame_id)
            buffer_size: Socket receive buffer size
        """
        super().__init__(daemon=True)
        self.port = port
        self.name = name
        self.callback = callback
        self.buffer_size = buffer_size
        self.running = True
        
        # Latest decoded frame
        self.frame: Optional[np.ndarray] = None
        self.frame_timestamp: int = 0
        self.frame_id: int = 0
        
        # Frame buffer for reassembly
        self.frame_buffer = FrameBuffer()
        
        # Statistics
        self.fps = 0
        self.frame_count = 0
        self.bytes_received = 0
        self._last_fps_time = time.time()
        self._fps_counter = 0
        
        # Socket
        self._socket: Optional[socket.socket] = None
    
    def run(self):
        """Main receiver loop (runs in background thread)."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffer_size)
        self._socket.bind(('0.0.0.0', self.port))
        self._socket.settimeout(1.0)
        
        print(f"🎥 {self.name} receiver listening on port {self.port}")
        
        while self.running:
            try:
                data, addr = self._socket.recvfrom(65535)
                self._process_packet(data)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"{self.name} receiver error: {e}")
        
        self._socket.close()
        print(f"🎥 {self.name} receiver stopped")
    
    def _process_packet(self, data: bytes):
        """Process received UDP packet."""
        if len(data) < HEADER_SIZE:
            return
        
        try:
            # Parse header
            camera_id = data[0]
            frame_id = struct.unpack('>Q', data[1:9])[0]
            chunk_idx = struct.unpack('>I', data[9:13])[0]
            total_chunks = struct.unpack('>I', data[13:17])[0]
            timestamp = struct.unpack('>Q', data[17:25])[0]
            data_len = struct.unpack('>I', data[25:29])[0]
            
            # Extract chunk data
            chunk_data = data[HEADER_SIZE:HEADER_SIZE + data_len]
            self.bytes_received += len(data)
            
            # Try to reassemble frame
            complete_frame = self.frame_buffer.add_chunk(
                frame_id, chunk_idx, total_chunks, chunk_data
            )
            
            if complete_frame:
                self._decode_frame(complete_frame, timestamp, frame_id)
            
            # Cleanup old incomplete frames
            self.frame_buffer.cleanup_old_frames(frame_id)
            
        except Exception as e:
            print(f"Error processing video packet: {e}")
    
    def _decode_frame(self, jpeg_data: bytes, timestamp: int, frame_id: int):
        """Decode JPEG frame data."""
        if not HAS_OPENCV:
            self.frame_count += 1
            return
        
        try:
            # Decode JPEG to numpy array
            img = cv2.imdecode(
                np.frombuffer(jpeg_data, np.uint8),
                cv2.IMREAD_COLOR
            )
            
            if img is not None:
                self.frame = img
                self.frame_timestamp = timestamp
                self.frame_id = frame_id
                self.frame_count += 1
                self._fps_counter += 1
                
                # Update FPS every second
                now = time.time()
                if now - self._last_fps_time >= 1.0:
                    self.fps = self._fps_counter
                    self._fps_counter = 0
                    self._last_fps_time = now
                
                # Call callback if set
                if self.callback:
                    self.callback(img, timestamp, frame_id)
                    
        except Exception as e:
            print(f"Error decoding frame: {e}")
    
    def stop(self):
        """Stop the receiver."""
        self.running = False
    
    def get_stats(self) -> dict:
        """Get receiver statistics."""
        buffer_stats = self.frame_buffer.get_stats()
        return {
            'frames': self.frame_count,
            'fps': self.fps,
            'bytes': self.bytes_received,
            'buffer_pending': buffer_stats['pending'],
            'buffer_dropped': buffer_stats['dropped']
        }