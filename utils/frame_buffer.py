"""
Frame Buffer - Reassembles chunked video frames from UDP packets
"""

from collections import defaultdict
from typing import Dict, Optional


class FrameBuffer:
    """
    Handles reassembly of chunked video frames.
    
    Video frames are split into multiple UDP packets for transmission.
    This class collects all chunks and reassembles them into complete frames.
    """
    
    def __init__(self, max_pending_frames: int = 30):
        """
        Initialize frame buffer.
        
        Args:
            max_pending_frames: Maximum number of incomplete frames to keep
        """
        self.frames: Dict[int, Dict[int, bytes]] = defaultdict(dict)
        self.frame_info: Dict[int, int] = {}  # frame_id -> total_chunks
        self.max_pending = max_pending_frames
        self.completed_count = 0
        self.dropped_count = 0
    
    def add_chunk(self, frame_id: int, chunk_idx: int, 
                  total_chunks: int, data: bytes) -> Optional[bytes]:
        """
        Add a chunk and return complete frame if all chunks received.
        
        Args:
            frame_id: Unique frame identifier
            chunk_idx: Index of this chunk (0 to total_chunks-1)
            total_chunks: Total number of chunks for this frame
            data: Chunk data bytes
            
        Returns:
            Complete frame bytes if all chunks received, None otherwise
        """
        self.frames[frame_id][chunk_idx] = data
        self.frame_info[frame_id] = total_chunks
        
        # Check if frame is complete
        if len(self.frames[frame_id]) == total_chunks:
            # Reassemble frame in order
            try:
                frame_data = b''.join(
                    self.frames[frame_id][i] 
                    for i in range(total_chunks)
                )
                self.completed_count += 1
            except KeyError:
                # Missing chunk somehow
                frame_data = None
            
            # Cleanup this frame
            del self.frames[frame_id]
            del self.frame_info[frame_id]
            
            return frame_data
        
        return None
    
    def cleanup_old_frames(self, current_frame_id: int, max_age: int = 10):
        """
        Remove incomplete frames that are too old.
        
        Args:
            current_frame_id: Current frame ID for reference
            max_age: Maximum frame age to keep
        """
        old_frames = [
            fid for fid in list(self.frames.keys())
            if current_frame_id - fid > max_age
        ]
        
        for fid in old_frames:
            self.dropped_count += 1
            del self.frames[fid]
            if fid in self.frame_info:
                del self.frame_info[fid]
    
    def get_pending_count(self) -> int:
        """Get number of incomplete frames in buffer."""
        return len(self.frames)
    
    def get_stats(self) -> dict:
        """Get buffer statistics."""
        return {
            'completed': self.completed_count,
            'dropped': self.dropped_count,
            'pending': len(self.frames)
        }
    
    def clear(self):
        """Clear all pending frames."""
        self.frames.clear()
        self.frame_info.clear()