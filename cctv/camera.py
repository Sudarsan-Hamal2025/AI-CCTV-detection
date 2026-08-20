import cv2
import threading
import queue
import time
import logging

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self, source, width=640, height=480, fps=15):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.running = False
        self.frame_queue = queue.Queue(maxsize=10)
        self.latest_frame = None
        self.thread = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera source: {self.source}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Camera started: {self.source}")

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to grab frame")
                time.sleep(0.1)
                continue
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()  # drop old frame
                except queue.Empty:
                    pass
            self.frame_queue.put(frame)
            self.latest_frame = frame
            time.sleep(1.0 / self.fps)

    def get_frame(self, timeout=1.0):
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_latest_frame(self):
        return self.latest_frame

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        logger.info("Camera stopped")