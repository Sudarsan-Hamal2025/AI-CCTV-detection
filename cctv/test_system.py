#!/usr/bin/env python3
"""
Quick testing script for CCTV system
Tests all components without needing a camera
"""

import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required packages are installed"""
    print("\n" + "="*60)
    print("Testing Imports...")
    print("="*60)
    
    packages = {
        'yaml': 'PyYAML',
        'cv2': 'OpenCV',
        'ultralytics': 'YOLOv8',
        'numpy': 'NumPy',
        'twilio': 'Twilio',
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'pytz': 'Pytz'
    }
    
    all_good = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name:20} OK")
        except ImportError:
            print(f"✗ {name:20} MISSING")
            all_good = False
    
    return all_good

def test_config():
    """Test if config file is valid"""
    print("\n" + "="*60)
    print("Testing Config File...")
    print("="*60)
    
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✓ config.yaml loaded successfully")
        
        # Check required keys
        required = ['camera', 'detection', 'anomaly', 'alert', 'database']
        for key in required:
            if key in config:
                print(f"  ✓ {key}: configured")
            else:
                print(f"  ✗ {key}: MISSING")
                return False
        
        # Show settings
        print(f"\n  Camera source: {config['camera']['source']}")
        print(f"  Resolution: {config['camera']['width']}x{config['camera']['height']}")
        print(f"  Detection model: {config['detection']['model']}")
        print(f"  Testing mode: {config['alert'].get('testing_mode', False)}")
        print(f"  Cooldown: {config['alert']['cooldown_seconds']}s")
        
        return True
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False

def test_database():
    """Test database functionality"""
    print("\n" + "="*60)
    print("Testing Database...")
    print("="*60)
    
    try:
        from database import Database
        db = Database('test_events.db')
        print("✓ Database initialized")
        
        # Test logging
        db.log_event('test_event', 'Testing database functionality')
        print("✓ Event logged successfully")
        
        # Test retrieval
        events = db.get_recent_events(1)
        if events:
            print(f"✓ Event retrieved: {events[0]}")
        
        db.conn.close()
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_camera():
    """Test camera availability"""
    print("\n" + "="*60)
    print("Testing Camera...")
    print("="*60)
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("✓ Webcam found and opened")
            ret, frame = cap.read()
            if ret:
                print(f"✓ Frame captured: {frame.shape}")
            cap.release()
            return True
        else:
            print("✗ Could not open webcam (may be in use)")
            print("  Try: Check if another app is using the camera")
            return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def test_anomaly_detectors():
    """Test anomaly detection classes"""
    print("\n" + "="*60)
    print("Testing Anomaly Detectors...")
    print("="*60)
    
    try:
        from anomaly import LoiteringDetector, CrowdDetector, RapidMovementDetector, TheftDetector
        import time
        
        # Test LoiteringDetector
        loiter = LoiteringDetector(duration_sec=1)
        detections = [(0, 0.9, (100, 100, 200, 200))]  # person at 100-200 coords
        assert not loiter.update(detections, time.time()), "Should not detect loitering immediately"
        print("✓ LoiteringDetector OK")
        
        # Test CrowdDetector
        crowd = CrowdDetector(min_persons=2)
        is_crowded, count = crowd.detect([(0, 0.9, (10, 10, 50, 50)), (0, 0.85, (100, 100, 150, 150))])
        assert is_crowded and count == 2, "Should detect 2 people as crowd"
        print("✓ CrowdDetector OK")
        
        # Test RapidMovementDetector
        rapid = RapidMovementDetector(movement_threshold=10)
        assert not rapid.detect([(0, 0.9, (100, 100, 200, 200))]), "First detection should not trigger"
        assert rapid.detect([(0, 0.9, (150, 150, 250, 250))]), "Large movement should trigger"
        print("✓ RapidMovementDetector OK")
        
        # Test TheftDetector
        theft = TheftDetector()
        print("✓ TheftDetector OK (needs actual frame for full test)")
        
        return True
    except Exception as e:
        print(f"✗ Anomaly detector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alert_system():
    """Test alert manager"""
    print("\n" + "="*60)
    print("Testing Alert System...")
    print("="*60)
    
    try:
        from alert import AlertManager
        
        # Test with testing_mode=True
        alert = AlertManager(
            account_sid='test',
            auth_token='test',
            from_number='+1234567890',
            to_number='+9876543210',
            voice_message='Test alert',
            sms_message='Test SMS',
            testing_mode=True
        )
        
        print("✓ AlertManager initialized in testing mode")
        print("\nSending test alerts...")
        alert.send_sms()
        alert.make_call()
        print(f"✓ Alert system working (sent {alert.alert_count} alerts)")
        
        return True
    except Exception as e:
        print(f"✗ Alert system test failed: {e}")
        return False

def test_api():
    """Test API endpoints"""
    print("\n" + "="*60)
    print("Testing API...")
    print("="*60)
    
    try:
        from api import app
        print("✓ API module imported successfully")
        print(f"✓ FastAPI app created: {app.title}")
        print(f"✓ Routes available: {len(app.routes)} endpoints")
        
        # List all routes
        print("\n  Available endpoints:")
        for route in app.routes:
            if hasattr(route, 'path'):
                print(f"    - {route.path}")
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  CCTV Security System - Component Test".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    results = {
        "Imports": test_imports(),
        "Config": test_config(),
        "Database": test_database(),
        "Camera": test_camera(),
        "Anomaly Detectors": test_anomaly_detectors(),
        "Alert System": test_alert_system(),
        "API": test_api(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:25} {status}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All systems ready! You can start the main system with:")
        print("  python main.py")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
