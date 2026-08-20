import time
from collections import deque
import logging
import math

logger = logging.getLogger(__name__)


class LoiteringDetector:
    def __init__(self, duration_sec=10, iou_threshold=0.5, max_history=100):
        self.duration_sec = duration_sec
        self.iou_threshold = iou_threshold
        self.history = deque(maxlen=max_history)  # (bbox, timestamp)

    def update(self, detections, current_time):
        """
        Update with current frame's detections.
        Returns True if loitering detected.
        """
        # For simplicity, assume we track the first person detection.
        person_bbox = None
        for cls, conf, bbox in detections:
            if cls == 0:  # person
                person_bbox = bbox
                break

        if person_bbox is None:
            # No person; clear history
            self.history.clear()
            return False

        # Check if this bbox overlaps significantly with any recent bbox
        matched = False
        for hist_bbox, _ in self.history:
            if self._iou(person_bbox, hist_bbox) >= self.iou_threshold:
                matched = True
                break

        if matched:
            # Person is still in the same area
            self.history.append((person_bbox, current_time))
        else:
            # New location, start new history
            self.history.clear()
            self.history.append((person_bbox, current_time))

        # Check if any entry's timestamp is older than duration_sec
        if len(self.history) > 0:
            oldest = min(t for _, t in self.history)
            if current_time - oldest >= self.duration_sec:
                logger.info("Loitering detected!")
                return True
        return False

    def _iou(self, bbox1, bbox2):
        """Compute IoU between two bounding boxes (x1,y1,x2,y2)"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0


class CrowdDetector:
    """Detects when 2 or more people are present in the frame"""
    
    def __init__(self, min_persons=2):
        self.min_persons = min_persons

    def detect(self, detections):
        """
        Returns True if 2 or more people detected (>= min_persons)
        """
        person_count = sum(1 for cls, conf, bbox in detections if cls == 0)
        if person_count >= self.min_persons:
            logger.info(f"Crowd detected: {person_count} people")
            return True, person_count
        return False, person_count


class RapidMovementDetector:
    """Detects rapid/suspicious movement patterns"""
    
    def __init__(self, movement_threshold=100, history_size=5):
        self.movement_threshold = movement_threshold
        self.history = deque(maxlen=history_size)  # stores bbox centers

    def get_center(self, bbox):
        """Get center point of bounding box"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def detect(self, detections):
        """
        Returns True if rapid movement detected
        """
        person_bboxes = [bbox for cls, conf, bbox in detections if cls == 0]
        
        if not person_bboxes:
            self.history.clear()
            return False

        current_center = self.get_center(person_bboxes[0])
        
        if len(self.history) > 0:
            prev_center = self.history[-1]
            distance = math.sqrt(
                (current_center[0] - prev_center[0]) ** 2 + 
                (current_center[1] - prev_center[1]) ** 2
            )
            
            if distance > self.movement_threshold:
                logger.warning(f"Rapid movement detected: {distance:.1f} pixels")
                return True

        self.history.append(current_center)
        return False


class TheftDetector:
    """Detects potential theft behaviors based on motion and frame changes"""
    
    def __init__(self, sensitivity=0.3):
        self.sensitivity = sensitivity
        self.prev_frame = None
        self.motion_history = deque(maxlen=10)

    def detect_motion(self, frame):
        """
        Detects motion by comparing consecutive frames
        Returns motion percentage (0-1)
        """
        import cv2
        import numpy as np
        
        if self.prev_frame is None:
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return 0.0

        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Compute absolute difference
        diff = cv2.absdiff(self.prev_frame, current_gray)
        motion_pixels = np.count_nonzero(diff > 30)
        total_pixels = diff.shape[0] * diff.shape[1]
        motion_percentage = motion_pixels / total_pixels
        
        self.prev_frame = current_gray
        self.motion_history.append(motion_percentage)
        
        return motion_percentage

    def detect(self, frame, detections):
        """
        Returns True if suspicious activity detected
        Combines motion detection and presence of people
        """
        motion = self.detect_motion(frame)
        person_count = sum(1 for cls, conf, bbox in detections if cls == 0)
        
        # If high motion + person present = suspicious
        if motion > self.sensitivity and person_count > 0:
            logger.warning(f"Suspicious motion detected: {motion:.1%}")
            return True
        
        return False