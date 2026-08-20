import cv2
import threading
import time
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import queue
import numpy as np
from mysql_database import MySQLDatabase

logger = logging.getLogger(__name__)

class VideoRecorder:
    def __init__(self, database: MySQLDatabase, output_dir: str = "uploads/videos"):
        self.db = database
        self.output_dir = output_dir
        self.recording = False
        self.current_recording = None
        self.recording_thread = None
        self.frame_queue = queue.Queue(maxsize=100)
        self.event_callbacks = []
        
        # Recording settings
        self.fps = 15
        self.resolution = (640, 480)
        self.codec = cv2.VideoWriter_fourcc(*'mp4v')
        self.max_file_size_mb = 100  # Max file size before splitting
        self.max_duration_minutes = 30  # Max duration per file
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "thumbnails"), exist_ok=True)
        
        logger.info("Video recorder initialized")
    
    def add_event_callback(self, callback: Callable):
        """Add callback function for recording events"""
        self.event_callbacks.append(callback)
    
    def _notify_event(self, event_type: str, data: dict):
        """Notify all event callbacks"""
        for callback in self.event_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    def start_continuous_recording(self, user_id: int, camera_id: str = "default"):
        """Start continuous recording"""
        if self.recording:
            logger.warning("Recording already in progress")
            return
        
        self.recording = True
        self.recording_thread = threading.Thread(
            target=self._continuous_recording_worker,
            args=(user_id, camera_id),
            daemon=True
        )
        self.recording_thread.start()
        
        logger.info(f"Started continuous recording for user {user_id}, camera {camera_id}")
        self._notify_event("recording_started", {"type": "continuous", "user_id": user_id, "camera_id": camera_id})
    
    def start_event_recording(self, user_id: int, camera_id: str = "default", duration_seconds: int = 30):
        """Start event-triggered recording"""
        if self.recording:
            logger.warning("Recording already in progress")
            return
        
        self.recording = True
        self.recording_thread = threading.Thread(
            target=self._event_recording_worker,
            args=(user_id, camera_id, duration_seconds),
            daemon=True
        )
        self.recording_thread.start()
        
        logger.info(f"Started event recording for user {user_id}, camera {camera_id}, duration {duration_seconds}s")
        self._notify_event("recording_started", {"type": "event", "user_id": user_id, "camera_id": camera_id, "duration": duration_seconds})
    
    def stop_recording(self):
        """Stop current recording"""
        if not self.recording:
            return
        
        self.recording = False
        
        # Add sentinel to queue to stop worker
        try:
            self.frame_queue.put(None, timeout=1)
        except queue.Full:
            pass
        
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=5)
        
        # Close current video writer
        if self.current_recording and self.current_recording['writer']:
            self.current_recording['writer'].release()
            self._finalize_recording()
        
        logger.info("Recording stopped")
        self._notify_event("recording_stopped", {})
    
    def add_frame(self, frame: np.ndarray, timestamp: Optional[datetime] = None):
        """Add frame to recording queue"""
        if not self.recording:
            return
        
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            self.frame_queue.put((frame, timestamp), timeout=0.1)
        except queue.Full:
            logger.warning("Frame queue is full, dropping frame")
    
    def _continuous_recording_worker(self, user_id: int, camera_id: str):
        """Worker thread for continuous recording"""
        start_time = datetime.now()
        file_start_time = start_time
        frame_count = 0
        
        # Create initial video file
        self._create_new_video_file(user_id, camera_id, "continuous")
        
        while self.recording:
            try:
                item = self.frame_queue.get(timeout=1.0)
                if item is None:
                    break
                
                frame, timestamp = item
                
                # Resize frame if needed
                if frame.shape[:2] != self.resolution[::-1]:
                    frame = cv2.resize(frame, self.resolution)
                
                # Write frame
                self.current_recording['writer'].write(frame)
                frame_count += 1
                self.current_recording['frame_count'] = frame_count
                self.current_recording['end_time'] = timestamp
                
                # Check if we need to split the file
                current_time = datetime.now()
                duration = (current_time - file_start_time).total_seconds()
                
                # Split by duration
                if duration >= self.max_duration_minutes * 60:
                    self._split_video_file(user_id, camera_id, "continuous")
                    file_start_time = current_time
                    frame_count = 0
                
                # Split by file size (approximate check)
                elif frame_count % (self.fps * 60) == 0:  # Check every minute
                    file_size = self._get_current_file_size()
                    if file_size >= self.max_file_size_mb * 1024 * 1024:
                        self._split_video_file(user_id, camera_id, "continuous")
                        file_start_time = current_time
                        frame_count = 0
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in continuous recording worker: {e}")
                break
        
        # Finalize recording
        self._finalize_recording()
    
    def _event_recording_worker(self, user_id: int, camera_id: str, duration_seconds: int):
        """Worker thread for event-triggered recording"""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        frame_count = 0
        
        # Create video file
        self._create_new_video_file(user_id, camera_id, "event_triggered")
        
        # Add pre-roll frames if available (last few seconds from queue)
        pre_roll_frames = []
        temp_queue = queue.Queue()
        
        # Extract last 2 seconds of frames
        while not self.frame_queue.empty() and len(pre_roll_frames) < self.fps * 2:
            try:
                item = self.frame_queue.get_nowait()
                pre_roll_frames.append(item)
                temp_queue.put(item)
            except queue.Empty:
                break
        
        # Put frames back and write pre-roll
        while not temp_queue.empty():
            try:
                item = temp_queue.get_nowait()
                self.frame_queue.put(item, timeout=0.1)
            except queue.Full:
                break
        
        # Write pre-roll frames
        for frame, timestamp in pre_roll_frames:
            if frame.shape[:2] != self.resolution[::-1]:
                frame = cv2.resize(frame, self.resolution)
            self.current_recording['writer'].write(frame)
            frame_count += 1
        
        # Record for specified duration
        while self.recording and datetime.now() < end_time:
            try:
                item = self.frame_queue.get(timeout=1.0)
                if item is None:
                    break
                
                frame, timestamp = item
                
                if frame.shape[:2] != self.resolution[::-1]:
                    frame = cv2.resize(frame, self.resolution)
                
                self.current_recording['writer'].write(frame)
                frame_count += 1
                self.current_recording['frame_count'] = frame_count
                self.current_recording['end_time'] = timestamp
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in event recording worker: {e}")
                break
        
        # Finalize recording
        self._finalize_recording()
    
    def _create_new_video_file(self, user_id: int, camera_id: str, recording_type: str):
        """Create a new video file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{camera_id}_{recording_type}_{timestamp}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        writer = cv2.VideoWriter(
            filepath,
            self.codec,
            self.fps,
            self.resolution
        )
        
        self.current_recording = {
            'filepath': filepath,
            'filename': filename,
            'writer': writer,
            'user_id': user_id,
            'camera_id': camera_id,
            'recording_type': recording_type,
            'start_time': datetime.now(),
            'end_time': None,
            'frame_count': 0,
            'file_size': 0
        }
        
        logger.info(f"Created new video file: {filename}")
    
    def _split_video_file(self, user_id: int, camera_id: str, recording_type: str):
        """Split current video file and create a new one"""
        if self.current_recording:
            # Finalize current file
            self.current_recording['writer'].release()
            self._finalize_recording()
            
            # Create new file
            self._create_new_video_file(user_id, camera_id, recording_type)
    
    def _finalize_recording(self):
        """Finalize current recording and save to database"""
        if not self.current_recording:
            return
        
        try:
            # Get file info
            filepath = self.current_recording['filepath']
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            duration_seconds = 0
            
            if self.current_recording['frame_count'] > 0:
                duration_seconds = self.current_recording['frame_count'] / self.fps
            
            # Create thumbnail
            thumbnail_path = self._create_thumbnail(filepath)
            
            # Save to database
            video_id = self.db.save_video_recording(
                user_id=self.current_recording['user_id'],
                camera_id=self.current_recording['camera_id'],
                file_path=filepath,
                file_size=file_size,
                duration_seconds=int(duration_seconds),
                start_time=self.current_recording['start_time'],
                end_time=self.current_recording['end_time'] or datetime.now(),
                recording_type=self.current_recording['recording_type'],
                thumbnail_path=thumbnail_path
            )
            
            logger.info(f"Finalized recording: {self.current_recording['filename']} (ID: {video_id})")
            
            # Notify event
            self._notify_event("recording_completed", {
                "video_id": video_id,
                "filename": self.current_recording['filename'],
                "duration": duration_seconds,
                "file_size": file_size
            })
            
        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")
        finally:
            self.current_recording = None
    
    def _create_thumbnail(self, video_path: str) -> Optional[str]:
        """Create thumbnail from video"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # Seek to 1 second or middle of video
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_count > 0:
                target_frame = min(int(fps), frame_count // 2)  # 1 second or middle
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Create thumbnail filename
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                thumbnail_path = os.path.join(self.output_dir, "thumbnails", f"{base_name}_thumb.jpg")
                
                # Resize and save thumbnail
                thumbnail = cv2.resize(frame, (320, 240))
                cv2.imwrite(thumbnail_path, thumbnail)
                
                return thumbnail_path
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
        
        return None
    
    def _get_current_file_size(self) -> int:
        """Get current video file size in bytes"""
        if not self.current_recording:
            return 0
        
        filepath = self.current_recording['filepath']
        if os.path.exists(filepath):
            return os.path.getsize(filepath)
        
        return 0
    
    def get_recording_status(self) -> dict:
        """Get current recording status"""
        if not self.recording:
            return {
                "recording": False,
                "type": None,
                "duration": 0,
                "frame_count": 0,
                "file_size": 0
            }
        
        if self.current_recording:
            duration = 0
            if self.current_recording['start_time']:
                end_time = self.current_recording['end_time'] or datetime.now()
                duration = (end_time - self.current_recording['start_time']).total_seconds()
            
            return {
                "recording": True,
                "type": self.current_recording['recording_type'],
                "duration": duration,
                "frame_count": self.current_recording['frame_count'],
                "file_size": self._get_current_file_size(),
                "filename": self.current_recording['filename']
            }
        
        return {"recording": True, "type": "unknown"}
    
    def configure(self, fps: int = None, resolution: tuple = None, 
                  max_file_size_mb: int = None, max_duration_minutes: int = None):
        """Configure recording settings"""
        if fps is not None:
            self.fps = fps
        
        if resolution is not None:
            self.resolution = resolution
        
        if max_file_size_mb is not None:
            self.max_file_size_mb = max_file_size_mb
        
        if max_duration_minutes is not None:
            self.max_duration_minutes = max_duration_minutes
        
        logger.info(f"Recording configuration updated: fps={self.fps}, resolution={self.resolution}, "
                   f"max_file_size={self.max_file_size_mb}MB, max_duration={self.max_duration_minutes}min")
    
    def cleanup_old_recordings(self, days: int = 30):
        """Clean up old recordings (called by cleanup scheduler)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # This would be called from the cleanup scheduler
            # The actual cleanup is handled by the database cleanup methods
            logger.info(f"Cleaning up recordings older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old recordings: {e}")
