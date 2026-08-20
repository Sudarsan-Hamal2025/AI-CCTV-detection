# CCTV Robbery & Theft Detection System

A real-time video surveillance system that detects robbery, theft, and suspicious activities using AI-powered computer vision and sends instant alerts to the admin.

> Note: Web dashboard/UI has been removed in this simplified distribution; use REST API endpoints only.

## Features

✅ **Real-time Detection**
- YOLOv8 person detection
- Loitering detection (suspicious staying in one place)
- Crowd detection (multiple people)
- Rapid movement detection (running/fleeing)
- Suspicious motion tracking (theft patterns)
- Night mode intrusion detection

✅ **Multiple Alert Methods**
- Voice calls (via Twilio)
- SMS alerts (via Twilio)
- Testing mode for development (console alerts)
- Event logging to database

✅ **REST API**
- Control monitoring system
- View detection events
- Generate test alerts
- System health checks

✅ **Database**
- SQLite for event logging
- Timestamp and event type tracking
- Full event details storage

## Project Structure

```
cctv/
├── main.py              # Main detection loop
├── camera.py            # Camera/video capture handler
├── detection.py         # YOLOv8 object detection
├── anomaly.py           # Suspicious behavior detection
├── alert.py             # Alert notification system
├── api.py               # REST API endpoints
├── database.py          # Event logging
├── config.yaml          # Configuration file
└── events.db            # Event database (created on first run)
```

## Installation

### Prerequisites
- Python 3.8+
- Webcam or IP camera (RTSP stream)

### Setup Steps

1. **Navigate to project directory**
   ```bash
   cd d:\xampp\htdocs\cctv
   ```

2. **Install dependencies** (already done)
   ```bash
   pip install fastapi pydantic uvicorn pytz
   pip install opencv-python ultralytics numpy
   pip install twilio pyyaml
   ```

## Configuration

Edit `config.yaml` to customize the system:

### Camera Settings
```yaml
camera:
  source: 0                    # 0 = webcam, "rtsp://..." for IP camera
  width: 640
  height: 480
  fps: 15
  display_feed: true           # Show video with detections
```

### Detection Settings
```yaml
detection:
  model: "yolov8n.pt"         # nano model for fast detection
  confidence: 0.45            # Lower = detect more (may have false positives)
  classes: [0]                # 0 = person class
  device: "cpu"               # "cuda" for GPU
```

### Anomaly Detection
```yaml
anomaly:
  loitering:
    enabled: true
    duration_sec: 8           # Alert if person stays 8+ seconds
    iou_threshold: 0.5        # Overlap threshold
  
  crowd_detection:
    enabled: true
    min_persons: 3            # Alert if 3+ people detected
  
  rapid_movement:
    enabled: true
    movement_threshold: 100   # Alert if person moves 100+ pixels
  
  theft_detection:
    enabled: true
    alert_on_movement: true   # Alert on suspicious motion
  
  night_mode:
    enabled: false            # Enable for night intrusion detection
    start_hour: 22
    end_hour: 6
    timezone: "UTC"
```

### Alert Settings
```yaml
alert:
  testing_mode: true          # 🔧 Set to true for TESTING (console alerts)
  twilio:
    account_sid: "your_sid"   # Get from Twilio
    auth_token: "your_token"  # Get from Twilio
    from_number: "+1234567890"
    to_number: "+9876543210"
  cooldown_seconds: 30        # Minimum time between alerts
```

## Usage

### 1. **Start the System**

```bash
python main.py
```

You should see:
```
==========================================================
CCTV Security System Starting...
==========================================================
2024-03-23 10:15:30,123 - __main__ - INFO - ✓ Camera started successfully
2024-03-23 10:15:30,456 - __main__ - INFO - ✓ API server started on http://0.0.0.0:8000
2024-03-23 10:15:31,789 - __main__ - INFO - Starting main detection loop...
==========================================================
```

### 2. **Test with Webcam**

The system uses your laptop's front camera (source: 0 in config.yaml).

**Test scenarios:**
1. **Move in front of camera** → Should detect person
2. **Stay still for 8+ seconds** → Loitering alert
3. **Move rapidly/suddenly** → Rapid movement alert
4. **Get 3+ people in frame** → Crowd detection alert
5. **Quick side-to-side motion** → Theft detection alert

When testing alerts in Testing Mode, you'll see:
```
============================================================
🚨 SMS ALERT SENT (Testing Mode) - Alert #1
============================================================
Timestamp: 2024-03-23 10:15:45
To: +9876543210
Message: Alert: Suspicious activity detected.
============================================================
```

### 3. **Use the REST API**

#### Check Status
```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "running": true,
  "timestamp": "2024-03-23T10:15:50.123456"
}
```

#### View Events
```bash
curl http://localhost:8000/events?limit=10
```

#### Get Event Statistics
```bash
curl http://localhost:8000/events/stats/summary
```

#### Send Test Alert
```bash
curl -X POST http://localhost:8000/alert/test \
  -H "Content-Type: application/json" \
  -d '{"event_type": "MANUAL_TEST"}'
```

#### Stop Monitoring
```bash
curl -X POST http://localhost:8000/stop
```

#### Start Monitoring
```bash
curl -X POST http://localhost:8000/start
```

### 4. **View Live Feed** (Optional)

Set `display_feed: true` in config.yaml to see real-time video with:
- Detection boxes around people
- Confidence scores
- Frame count and person count
- Press 'Q' to quit

## Setting Up Real Twilio Alerts

To use real SMS and voice calls:

1. **Get Twilio Account:**
   - Sign up at https://www.twilio.com
   - Verify phone number
   - Get Account SID and Auth Token

2. **Update config.yaml:**
   ```yaml
   alert:
     testing_mode: false        # Disable testing mode
     twilio:
       account_sid: "ACxxxxxxxxxxxxxxxxxxxxx"
       auth_token: "your_actual_token"
       from_number: "+1234567890"  # Your Twilio number
       to_number: "+9876543210"    # Admin phone number
   ```

3. **Restart the system**

## Database

Events are logged to `events.db` with:
- **timestamp**: When event occurred
- **event_type**: Type of suspicious activity
- **details**: Additional information

Query events:
```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 20")
for row in cursor.fetchall():
    print(row)
```

## Troubleshooting

### Camera not opening
- Check if webcam is in use by another application
- Try: `python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"`
- Use IP camera RTSP URL if webcam unavailable

### Missing detections
- Increase confidence threshold in config.yaml (lower = more detections)
- Ensure good lighting
- Try YOLOv8s or YOLOv8m for better accuracy (slower)

### Frequent false alerts
- Increase cooldown_seconds
- Adjust movement_threshold (increase = less sensitive)
- Increase loitering duration_sec

### API not accessible
- Check if port 8000 is available
- Update API endpoint in code if using different port

## Performance Tips

- Use `device: "cuda"` if GPU available (much faster)
- Lower resolution (480p) for faster processing
- Use YOLOv8n model (nano) for CPU systems
- Increase cooldown_seconds to reduce load

## Files Modified & Created

| File | Status | Description |
|------|--------|-------------|
| config.yaml | ✏️ Updated | Added webcam config, testing mode, new detectors |
| main.py | ✏️ Updated | Complete detection loop with all anomalies |
| anomaly.py | ✏️ Updated | Added Crowd, RapidMovement, Theft detectors |
| alert.py | ✏️ Updated | Added testing mode, better logging |
| api.py | ✏️ Updated | More endpoints, event filtering |
| camera.py | ✓ Complete | Camera module working |
| detection.py | ✓ Complete | YOLOv8 detection working |
| database.py | ✓ Complete | Event logging working |

## Next Steps

1. ✅ Test with webcam locally
2. 📱 Get Twilio account and test real alerts
3. 🎥 Deploy with IP camera
4. 📊 Monitor events via API/Database
5. 🔧 Adjust thresholds based on your space
6. 🚀 Deploy to production server

## Support

For issues or questions:
1. Check the logs in surveillance.log
2. Enable verbose logging in config.yaml
3. Check database events: `sqlite3 events.db`
4. Review API responses for status

---

**System Ready for Testing! 🎥🚨**

Start with: `python main.py`
