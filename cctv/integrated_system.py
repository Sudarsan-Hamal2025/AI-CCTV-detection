#!/usr/bin/env python3
"""
Integrated CCTV Security System
Main entry point that combines all components
"""

import yaml
import logging
import time
import threading
import signal
import sys
from datetime import datetime
import pytz
import cv2
import os

# Import existing components
from camera import Camera
from detection import Detector
from anomaly import LoiteringDetector, CrowdDetector, RapidMovementDetector, TheftDetector
from alert import AlertManager

# Import new components
from mysql_database import MySQLDatabase
from auth import AuthenticationManager
from web_api import app as web_app
from video_recorder import VideoRecorder
from cleanup_scheduler import CleanupScheduler
from subscription_manager import SubscriptionManager
from super_admin_features import SuperAdminFeatures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegratedCCTVSystem:
    def __init__(self, config_path='config.yaml'):
        self.config = self.load_config(config_path)
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Initialize core components
        self.camera = None
        self.detector = None
        self.anomaly_detectors = {}
        self.alert_manager = None
        
        # Initialize new components
        self.db = None
        self.auth_manager = None
        self.video_recorder = None
        self.cleanup_scheduler = None
        self.subscription_manager = None
        self.super_admin_features = None
        
        # Threading
        self.detection_thread = None
        self.web_server_thread = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)
    
    def signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def initialize_components(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing system components...")
            
            # Initialize database
            self.db = MySQLDatabase(
                host=self.config.get('database', {}).get('host', 'localhost'),
                user=self.config.get('database', {}).get('user', 'root'),
                password=self.config.get('database', {}).get('password', ''),
                database=self.config.get('database', {}).get('database', 'cctv_security')
            )
            
            # Initialize authentication
            self.auth_manager = AuthenticationManager(
                database=self.db,
                secret_key=self.config.get('security', {}).get('secret_key')
            )
            
            # Initialize camera
            self.camera = Camera(
                source=self.config['camera']['source'],
                width=self.config['camera']['width'],
                height=self.config['camera']['height'],
                fps=self.config['camera']['fps']
            )
            
            # Initialize detection
            self.detector = Detector(
                model_path=self.config['detection']['model'],
                conf_threshold=self.config['detection']['confidence'],
                classes=self.config['detection']['classes'],
                device=self.config['detection']['device']
            )
            
            # Initialize anomaly detectors
            self.anomaly_detectors = {
                'loitering': LoiteringDetector(
                    duration_sec=self.config['anomaly']['loitering']['duration_sec'],
                    iou_threshold=self.config['anomaly']['loitering']['iou_threshold']
                ),
                'crowd': CrowdDetector(
                    min_persons=self.config['anomaly']['crowd_detection']['min_persons']
                ),
                'rapid_movement': RapidMovementDetector(
                    movement_threshold=self.config['anomaly']['rapid_movement']['movement_threshold']
                ),
                'theft': TheftDetector(sensitivity=0.3)
            }
            
            # Initialize alert manager
            # Initialize alert manager (prefer environment variables for credentials)
            account_sid = os.getenv('TWILIO_ACCOUNT_SID') or self.config['alert']['twilio'].get('account_sid', '')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN') or self.config['alert']['twilio'].get('auth_token', '')
            from_number = os.getenv('TWILIO_FROM_NUMBER') or self.config['alert']['twilio'].get('from_number', '')
            to_number = os.getenv('TWILIO_TO_NUMBER') or self.config['alert']['twilio'].get('to_number', '')
            voice_message = self.config['alert']['twilio'].get('voice_message', '')
            sms_message = self.config['alert']['twilio'].get('sms_message', '')

            self.alert_manager = AlertManager(
                account_sid=account_sid,
                auth_token=auth_token,
                from_number=from_number,
                to_number=to_number,
                voice_message=voice_message,
                sms_message=sms_message,
                testing_mode=self.config['alert'].get('testing_mode', False)
            )
            
            # Initialize video recorder
            self.video_recorder = VideoRecorder(
                database=self.db,
                output_dir=self.config.get('video', {}).get('output_dir', 'uploads/videos')
            )
            
            # Configure video recorder
            self.video_recorder.configure(
                fps=self.config.get('video', {}).get('fps', 15),
                resolution=(
                    self.config.get('video', {}).get('width', 640),
                    self.config.get('video', {}).get('height', 480)
                ),
                max_file_size_mb=self.config.get('video', {}).get('max_file_size_mb', 100),
                max_duration_minutes=self.config.get('video', {}).get('max_duration_minutes', 30)
            )
            
            # Initialize cleanup scheduler
            self.cleanup_scheduler = CleanupScheduler(database=self.db)
            
            # Initialize subscription manager
            self.subscription_manager = SubscriptionManager(database=self.db)
            
            # Initialize super admin features
            self.super_admin_features = SuperAdminFeatures(
                database=self.db,
                auth_manager=self.auth_manager,
                subscription_manager=self.subscription_manager,
                cleanup_scheduler=self.cleanup_scheduler
            )
            
            # Setup video recorder callbacks
            self.video_recorder.add_event_callback(self.on_video_event)
            
            logger.info("✓ All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def start_camera(self):
        """Start the camera"""
        try:
            self.camera.start()
            logger.info("✓ Camera started successfully")
        except RuntimeError as e:
            logger.error(f"Failed to start camera: {e}")
            raise
    
    def start_web_server(self):
        """Start the web API server"""
        def run_web_server():
            import uvicorn
            
            # Store references in web_app for access in endpoints
            web_app.state.db = self.db
            web_app.state.auth_manager = self.auth_manager
            web_app.state.video_recorder = self.video_recorder
            web_app.state.subscription_manager = self.subscription_manager
            web_app.state.super_admin_features = self.super_admin_features
            
            uvicorn.run(
                web_app,
                host=self.config.get('web', {}).get('host', '0.0.0.0'),
                port=self.config.get('web', {}).get('port', 8000),
                log_level="info"
            )
        
        self.web_server_thread = threading.Thread(target=run_web_server, daemon=True)
        self.web_server_thread.start()
        logger.info("✓ Web server started on http://0.0.0.0:8000")
    
    def start_cleanup_scheduler(self):
        """Start the cleanup scheduler"""
        self.cleanup_scheduler.start()
        logger.info("✓ Cleanup scheduler started")
    
    def detection_loop(self):
        """Main detection loop"""
        logger.info("Starting detection loop...")
        
        frame_count = 0
        last_alert_time = 0
        cooldown_sec = self.config['alert']['cooldown_seconds']
        
        # Night mode settings
        night_enabled = self.config['anomaly']['night_mode']['enabled']
        night_start = self.config['anomaly']['night_mode']['start_hour']
        night_end = self.config['anomaly']['night_mode']['end_hour']
        timezone_str = self.config['anomaly']['night_mode'].get('timezone', 'UTC')
        tz = pytz.timezone(timezone_str)
        
        # Default user for system events (could be made configurable)
        system_user_id = 1  # Assuming user ID 1 exists
        
        while self.running and not self.shutdown_event.is_set():
            try:
                frame = self.camera.get_frame(timeout=1.0)
                if frame is None:
                    continue
                
                frame_count += 1
                current_time = time.time()
                
                # Add frame to video recorder
                self.video_recorder.add_frame(frame)
                
                # Run detection
                detections = self.detector.detect(frame)
                person_count = sum(1 for cls, conf, bbox in detections if cls == 0)
                
                # Check for system user subscription limits
                subscription_check = self.subscription_manager.check_subscription_limits(
                    system_user_id, 'advanced_detection'
                )
                
                if not subscription_check['allowed']:
                    logger.warning(f"Detection limits reached: {subscription_check['reason']}")
                    time.sleep(5)  # Wait before retrying
                    continue
                
                # Night mode intrusion detection
                if night_enabled and self.config['anomaly']['night_mode'].get('enabled', True):
                    now = datetime.now(tz)
                    hour = now.hour
                    is_night = hour >= night_start or hour < night_end
                    
                    if is_night and person_count > 0:
                        if current_time - last_alert_time > cooldown_sec:
                            self.handle_detection(
                                'night_intrusion',
                                f"{person_count} person(s) detected at night",
                                detections,
                                frame,
                                system_user_id
                            )
                            last_alert_time = current_time
                
                # Loitering detection
                if self.config['anomaly']['loitering'].get('enabled', True) and person_count > 0:
                    if self.anomaly_detectors['loitering'].update(detections, current_time):
                        if current_time - last_alert_time > cooldown_sec:
                            self.handle_detection(
                                'loitering',
                                "Suspicious loitering detected",
                                detections,
                                frame,
                                system_user_id
                            )
                            last_alert_time = current_time
                
                # Crowd detection
                if self.config['anomaly']['crowd_detection'].get('enabled', True):
                    is_crowded, count = self.anomaly_detectors['crowd'].detect(detections)
                    if is_crowded:
                        if current_time - last_alert_time > cooldown_sec:
                            self.handle_detection(
                                'crowd_detected',
                                f"{count} people in same area",
                                detections,
                                frame,
                                system_user_id
                            )
                            last_alert_time = current_time
                
                # Rapid movement detection
                if self.config['anomaly']['rapid_movement'].get('enabled', True):
                    if self.anomaly_detectors['rapid_movement'].detect(detections):
                        if current_time - last_alert_time > cooldown_sec:
                            self.handle_detection(
                                'rapid_movement',
                                "Rapid/suspicious movement detected",
                                detections,
                                frame,
                                system_user_id
                            )
                            last_alert_time = current_time
                
                # Theft detection
                if self.config['anomaly']['theft_detection'].get('enabled', True):
                    if self.anomaly_detectors['theft'].detect(frame, detections):
                        if current_time - last_alert_time > cooldown_sec:
                            self.handle_detection(
                                'theft_risk',
                                "Suspicious motion with people detected",
                                detections,
                                frame,
                                system_user_id
                            )
                            last_alert_time = current_time
                
                # Optional: Display live feed
                if self.config['camera'].get('display_feed', False):
                    self.display_frame_with_detections(frame, detections, person_count, frame_count)
                
                # Log progress every 100 frames
                if frame_count % 100 == 0:
                    logger.debug(f"Processed {frame_count} frames - Last alert {int(current_time - last_alert_time)}s ago")
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                time.sleep(1)  # Prevent rapid error loops
    
    def handle_detection(self, event_type: str, details: str, detections, frame, user_id: int):
        """Handle a detection event"""
        try:
            logger.critical(f"🚨 {event_type.upper()}: {details}")
            
            # Send alert
            alert_message = event_type.replace('_', ' ').upper()
            self.alert_manager.send_alert(alert_message)
            
            # Log to database
            bbox_coordinates = None
            if detections:
                bbox_coordinates = [
                    {
                        'class': cls,
                        'confidence': float(conf),
                        'bbox': [float(x) for x in bbox]
                    }
                    for cls, conf, bbox in detections
                ]
            
            event_id = self.db.log_detection_event(
                user_id=user_id,
                event_type=event_type,
                confidence=max(detections, key=lambda x: x[1])[1] if detections else None,
                bbox_coordinates=bbox_coordinates,
                details=details
            )
            
            # Save detection image
            self.save_detection_image(frame, event_id, user_id)
            
            # Start event recording if configured
            if self.config.get('video', {}).get('record_on_detection', True):
                self.video_recorder.start_event_recording(
                    user_id=user_id,
                    duration_seconds=self.config.get('video', {}).get('event_duration', 30)
                )
            
        except Exception as e:
            logger.error(f"Error handling detection: {e}")
    
    def save_detection_image(self, frame, event_id: int, user_id: int):
        """Save detection image to database and filesystem"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_{event_id}_{user_id}_{timestamp}.jpg"
            filepath = f"uploads/images/{filename}"
            
            # Save image
            cv2.imwrite(filepath, frame)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            # Create thumbnail
            from video_recorder import VideoRecorder  # Import here to avoid circular imports
            recorder = VideoRecorder(self.db)
            thumbnail_path = recorder._create_thumbnail(filepath)
            
            # Save to database
            self.db.save_captured_image(
                event_id=event_id,
                user_id=user_id,
                file_path=filepath,
                file_size=file_size,
                thumbnail_path=thumbnail_path
            )
            
            logger.info(f"Saved detection image: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving detection image: {e}")
    
    def display_frame_with_detections(self, frame, detections, person_count, frame_count):
        """Display frame with detection overlays"""
        display_frame = frame.copy()
        
        for cls, conf, bbox in detections:
            x1, y1, x2, y2 = map(int, bbox)
            color = (0, 0, 255) if cls == 0 else (0, 255, 0)  # Red for person, green for others
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, f'{conf:.2f}', (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Add frame info
        cv2.putText(display_frame, f'Frame: {frame_count} | People: {person_count}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, 'Press Q to quit', (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow('CCTV Security System', display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.shutdown()
    
    def on_video_event(self, event_type: str, data: dict):
        """Handle video recorder events"""
        logger.info(f"Video event: {event_type} - {data}")
        
        # Log video events to database
        try:
            system_user_id = 1  # System user ID
            
            if event_type == "recording_completed":
                self.db.log_system_action(
                    user_id=system_user_id,
                    action='video_recording_completed',
                    details=f"Video ID: {data.get('video_id')}, Duration: {data.get('duration')}s"
                )
            
        except Exception as e:
            logger.error(f"Error logging video event: {e}")
    
    def start(self):
        """Start the integrated system"""
        try:
            logger.info("="*60)
            logger.info("CCTV Security System Starting...")
            logger.info("="*60)
            
            # Initialize components
            self.initialize_components()
            
            # Start camera
            self.start_camera()
            
            # Start web server
            self.start_web_server()
            
            # Start cleanup scheduler
            self.start_cleanup_scheduler()
            
            # Start detection in separate thread
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            logger.info("✓ System fully started and running")
            logger.info(f"  - Web interface: http://localhost:8000")
            logger.info(f"  - Database: {self.db.database}")
            logger.info(f"  - Camera: {self.config['camera']['source']}")
            logger.info("="*60)
            
            # Wait for shutdown
            self.detection_thread.join()
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the system gracefully"""
        logger.info("Shutting down system...")
        
        self.running = False
        self.shutdown_event.set()
        
        # Stop video recording
        if self.video_recorder:
            self.video_recorder.stop_recording()
        
        # Stop camera
        if self.camera:
            self.camera.stop()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        # Stop cleanup scheduler
        if self.cleanup_scheduler:
            self.cleanup_scheduler.stop()
        
        # Close database connection
        if self.db:
            self.db.close()
        
        logger.info("System shutdown complete")
    
    def get_status(self):
        """Get current system status"""
        status = {
            'running': self.running,
            'camera': self.camera.is_running() if self.camera else False,
            'video_recording': self.video_recorder.get_recording_status() if self.video_recorder else {},
            'database_connected': self.db.connection.is_connected() if self.db and self.db.connection else False,
            'uptime': 'Unknown'  # Could track start time
        }
        return status

def main():
    """Main entry point"""
    try:
        # Create necessary directories
        os.makedirs("uploads/images", exist_ok=True)
        os.makedirs("uploads/videos", exist_ok=True)
        os.makedirs("uploads/thumbnails", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Start the integrated system
        system = IntegratedCCTVSystem()
        system.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
    finally:
        logger.info("CCTV Security System stopped")

if __name__ == "__main__":
    main()
