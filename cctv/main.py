import os
import yaml
import logging
import time
import threading
from datetime import datetime
import pytz
import cv2

from camera import Camera
from detection import Detector
from anomaly import LoiteringDetector, CrowdDetector, RapidMovementDetector, TheftDetector
from alert import AlertManager
from database import Database
from api import app, system_state, run_api

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def ensure_upload_dirs():
    os.makedirs('uploads/images', exist_ok=True)
    os.makedirs('uploads/videos', exist_ok=True)
    os.makedirs('uploads/thumbnails', exist_ok=True)


def save_detection_frame(frame, event_type, camera_id):
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    safe_camera_id = camera_id.replace(' ', '_')
    filename = f"{safe_camera_id}_{event_type}_{timestamp}.jpg"
    file_path = os.path.join('uploads', 'images', filename)
    cv2.imwrite(file_path, frame)
    return file_path


def build_camera_list(config):
    cameras = []
    if isinstance(config.get('cameras'), list) and config['cameras']:
        for cam_conf in config['cameras']:
            camera_id = cam_conf.get('id') or cam_conf.get('name', 'camera').lower().replace(' ', '_')
            cameras.append({
                'id': camera_id,
                'name': cam_conf.get('name', camera_id),
                'location': cam_conf.get('location', 'Unknown location'),
                'source': cam_conf['source'],
                'width': cam_conf.get('width', config['camera']['width']),
                'height': cam_conf.get('height', config['camera']['height']),
                'fps': cam_conf.get('fps', config['camera']['fps']),
                'display_feed': cam_conf.get('display_feed', config['camera'].get('display_feed', False)),
                'camera': Camera(
                    source=cam_conf['source'],
                    width=cam_conf.get('width', config['camera']['width']),
                    height=cam_conf.get('height', config['camera']['height']),
                    fps=cam_conf.get('fps', config['camera']['fps'])
                )
            })
    else:
        camera_id = config['camera'].get('id', 'camera_1')
        cameras.append({
            'id': camera_id,
            'name': config['camera'].get('name', 'Camera 1'),
            'location': config['camera'].get('location', 'Unknown location'),
            'source': config['camera']['source'],
            'width': config['camera']['width'],
            'height': config['camera']['height'],
            'fps': config['camera']['fps'],
            'display_feed': config['camera'].get('display_feed', False),
            'camera': Camera(
                source=config['camera']['source'],
                width=config['camera']['width'],
                height=config['camera']['height'],
                fps=config['camera']['fps']
            )
        })
    return cameras


def main():
    # Load config
    config = load_config('config.yaml')
    
    logger.info("="*60)
    logger.info("CCTV Security System Starting...")
    logger.info("="*60)
    
    # Initialize components
    cameras = build_camera_list(config)
    detector = Detector(
        model_path=config['detection']['model'],
        conf_threshold=config['detection']['confidence'],
        classes=config['detection']['classes'],
        device=config['detection']['device']
    )
    loitering_detector = LoiteringDetector(
        duration_sec=config['anomaly']['loitering']['duration_sec'],
        iou_threshold=config['anomaly']['loitering']['iou_threshold']
    )
    crowd_detector = CrowdDetector(
        min_persons=config['anomaly']['crowd_detection']['min_persons']
    )
    rapid_movement_detector = RapidMovementDetector(
        movement_threshold=config['anomaly']['rapid_movement']['movement_threshold']
    )
    theft_detector = TheftDetector(sensitivity=0.3)
    
    alert_manager = AlertManager(
        account_sid=config['alert']['twilio']['account_sid'],
        auth_token=config['alert']['twilio']['auth_token'],
        from_number=config['alert']['twilio']['from_number'],
        to_number=config['alert']['twilio']['to_number'],
        voice_message=config['alert']['twilio']['voice_message'],
        sms_message=config['alert']['twilio']['sms_message'],
        testing_mode=config['alert'].get('testing_mode', False)
    )
    db = Database(config['database']['path'])

    # Ensure folder structure exists
    ensure_upload_dirs()

    # Share state with API
    system_state['db'] = db
    system_state['running'] = True
    system_state['alert_manager'] = alert_manager
    system_state['cameras'] = cameras
    system_state['camera'] = cameras[0]['camera'] if cameras else None

    def report_event(event_type, details, frame, cam_info):
        image_path = save_detection_frame(frame, event_type, cam_info['id'])
        alert_manager.send_alert(event_type.replace('_', ' ').upper())
        db.log_event(
            event_type,
            details,
            image_path=image_path,
            camera_id=cam_info['id'],
            camera_name=cam_info['name'],
            camera_location=cam_info['location']
        )

    # Start API in background thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    logger.info("✓ API server started on http://0.0.0.0:8000")

    # Start cameras
    try:
        for cam_info in cameras:
            cam_info['camera'].start()
            logger.info(f"✓ Camera started: {cam_info['id']} ({cam_info['name']} at {cam_info['location']})")
    except RuntimeError as e:
        logger.error(f"Failed to start camera: {e}")
        for cam_info in cameras:
            cam_info['camera'].stop()
        return

    # Cooldown tracking
    last_alert_time = 0
    cooldown_sec = config['alert']['cooldown_seconds']

    # Night mode
    night_enabled = config['anomaly']['night_mode']['enabled']
    night_start = config['anomaly']['night_mode']['start_hour']
    night_end = config['anomaly']['night_mode']['end_hour']
    timezone_str = config['anomaly']['night_mode'].get('timezone', 'UTC')
    tz = pytz.timezone(timezone_str)

    logger.info("Starting main detection loop...")
    logger.info(f"  - Loitering detection: {config['anomaly']['loitering']['enabled']}")
    logger.info(f"  - Crowd detection: {config['anomaly']['crowd_detection']['enabled']}")
    logger.info(f"  - Rapid movement detection: {config['anomaly']['rapid_movement']['enabled']}")
    logger.info(f"  - Theft detection: {config['anomaly']['theft_detection']['enabled']}")
    logger.info(f"  - Alert cooldown: {cooldown_sec}s")
    logger.info("="*60 + "\n")

    # Main loop
    frame_count = 0
    try:
        while system_state['running']:
            current_time = time.time()
            any_frame = False
            for cam_info in cameras:
                frame = cam_info['camera'].get_frame(timeout=0.05)
                if frame is None:
                    continue

                any_frame = True
                frame_count += 1
                detections = detector.detect(frame)
                person_count = sum(1 for cls, conf, bbox in detections if cls == 0)
                camera_label = f"{cam_info['name']} ({cam_info['location']})"

                # Check night mode intrusion
                if night_enabled:
                    now = datetime.now(tz)
                    hour = now.hour
                    is_night = hour >= night_start or hour < night_end
                    if is_night and person_count > 0:
                        if current_time - last_alert_time > cooldown_sec:
                            logger.critical(f"🚨 NIGHT MODE INTRUSION DETECTED on {camera_label}")
                            report_event("night_intrusion", f"{person_count} person(s) detected at night", frame, cam_info)
                            last_alert_time = current_time

                # Loitering detection
                if config['anomaly']['loitering'].get('enabled', True) and person_count > 0:
                    if loitering_detector.update(detections, current_time):
                        if current_time - last_alert_time > cooldown_sec:
                            logger.critical(f"🚨 LOITERING DETECTED on {camera_label}")
                            report_event("loitering", "Suspicious loitering detected", frame, cam_info)
                            last_alert_time = current_time

                # Crowd detection (2+ people)
                if config['anomaly']['crowd_detection'].get('enabled', True):
                    is_crowded, count = crowd_detector.detect(detections)
                    if is_crowded:
                        if current_time - last_alert_time > cooldown_sec:
                            logger.critical(f"🚨 CROWD DETECTED ({count} people) on {camera_label}")
                            report_event("crowd_detected", f"{count} people in same area", frame, cam_info)
                            last_alert_time = current_time

                # Rapid movement detection
                if config['anomaly']['rapid_movement'].get('enabled', True):
                    if rapid_movement_detector.detect(detections):
                        if current_time - last_alert_time > cooldown_sec:
                            logger.critical(f"🚨 RAPID MOVEMENT DETECTED (Possible Robbery) on {camera_label}")
                            report_event("rapid_movement", "Rapid/suspicious movement detected", frame, cam_info)
                            last_alert_time = current_time

                # Theft detection (motion + people)
                if config['anomaly']['theft_detection'].get('enabled', True):
                    if theft_detector.detect(frame, detections):
                        if current_time - last_alert_time > cooldown_sec:
                            logger.critical(f"🚨 SUSPICIOUS ACTIVITY DETECTED (Possible Theft) on {camera_label}")
                            report_event("theft_risk", "Suspicious motion with people detected", frame, cam_info)
                            last_alert_time = current_time

                # Optional: Display live feed with detections (for debugging/testing)
                if cam_info['display_feed']:
                    display_frame = frame.copy()
                    for cls, conf, bbox in detections:
                        x1, y1, x2, y2 = map(int, bbox)
                        color = (0, 0, 255) if cls == 0 else (0, 255, 0)
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(display_frame, f'{conf:.2f}', (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    cv2.putText(display_frame, f'{cam_info["name"]} | Frame: {frame_count} | People: {person_count}',
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, 'Press Q to quit', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    cv2.imshow(f'CCTV Security System - {cam_info["id"]}', display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("User quit signal received")
                        raise KeyboardInterrupt()

            if not any_frame:
                continue

            if frame_count % 100 == 0:
                logger.debug(f"Processed {frame_count} frames - Last alert {int(current_time - last_alert_time)}s ago")

    except KeyboardInterrupt:
        logger.info("Shutting down (Ctrl+C)...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up...")
        system_state['running'] = False
        for cam_info in cameras:
            cam_info['camera'].stop()
        cv2.destroyAllWindows()
        db.conn.close()
        logger.info("="*60)
        logger.info("CCTV Security System Stopped")
        logger.info(f"Total frames processed: {frame_count}")
        logger.info(f"Total events logged: Check events.db for details")
        logger.info("="*60)

if __name__ == "__main__":
    main()