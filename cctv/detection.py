from ultralytics import YOLO
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Detector:
    def __init__(self, model_path, conf_threshold=0.5, classes=None, device='cpu'):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.classes = classes  # list of class IDs to filter
        self.device = device

    def detect(self, frame):
        """
        Run detection on a frame.
        Returns list of detections: each is (class_id, confidence, bbox)
        bbox: (x1, y1, x2, y2) normalized to 0-1? We'll keep absolute for simplicity.
        """
        results = self.model(frame, conf=self.conf_threshold, classes=self.classes, device=self.device)
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append((cls, conf, (x1, y1, x2, y2)))
        return detections