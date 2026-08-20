# CCTV Security System - Usage Examples

This document shows practical examples of how to use the CCTV security system.

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Testing Alerts](#testing-alerts)
3. [API Examples](#api-examples)
4. [Database Queries](#database-queries)
5. [Configuration Examples](#configuration-examples)

---

## Basic Usage

### Start the System

**Terminal 1 - Start Full System:**
```bash
cd d:\xampp\htdocs\cctv
python main.py
```

Expected output:
```
==========================================================
CCTV Security System Starting...
==========================================================
2026-03-23 13:15:30,123 - __main__ - INFO - ✓ Camera started successfully
2026-03-23 13:15:30,456 - __main__ - INFO - ✓ API server started on http://0.0.0.0:8000
2026-03-23 13:15:31,789 - __main__ - INFO - Starting main detection loop...
  - Loitering detection: True
  - Crowd detection: True
  - Rapid movement detection: True
  - Theft detection: True
  - Alert cooldown: 30s
==========================================================
```

### Stop the System
```bash
# Press Ctrl+C in the terminal running main.py
# You'll see:
# Shutting down (Ctrl+C)...
# Cleaning up...
# CCTV Security System Stopped
```

---

## Testing Alerts

### Scenario 1: Loitering Detection

**What to do:**
1. Face the camera
2. Stand still for 8+ seconds
3. Don't move

**Expected result:**
```
2026-03-23 13:15:45,123 - __main__ - CRITICAL - 🚨 LOITERING DETECTED
2026-03-23 13:15:45,124 - alert - WARNING - [ALERT #1] 2026-03-23 13:15:45 - SMS ALERT (Testing Mode)
============================================================
🚨 SMS ALERT SENT (Testing Mode) - Alert #1
============================================================
Timestamp: 2026-03-23 13:15:45
To: +9876543210
Message: Alert: Suspicious activity detected.
============================================================
```

### Scenario 2: Rapid Movement / Running Detection

**What to do:**
1. Move quickly left-right
2. Do jumping jacks
3. Run in place

**Expected result:**
```
2026-03-23 13:16:00,456 - anomaly - WARNING - Rapid movement detected: 156.3 pixels
2026-03-23 13:16:00,457 - __main__ - CRITICAL - 🚨 RAPID MOVEMENT DETECTED (Possible Robbery)
2026-03-23 13:16:00,458 - alert - WARNING - [ALERT #2] 2026-03-23 13:16:00 - VOICE CALL ALERT (Testing Mode)
============================================================
🚨 VOICE CALL ALERT (Testing Mode) - Alert #2
============================================================
Timestamp: 2026-03-23 13:16:00
To: +9876543210
Voice Message: Alert! Suspicious activity detected at your location.
============================================================
```

### Scenario 3: Crowd Detection

**What to do:**
1. Get 3 or more people in front of camera
2. Stand together

**Expected result:**
```
2026-03-23 13:16:15,789 - anomaly - INFO - Crowd detected: 3 people
2026-03-23 13:16:15,790 - __main__ - CRITICAL - 🚨 CROWD DETECTED (3 people)
```

### Scenario 4: Theft / Suspicious Motion

**What to do:**
1. Make quick sudden movements
2. Wave hands rapidly in front of camera
3. Duck and move

**Expected result:**
```
2026-03-23 13:16:30,123 - anomaly - WARNING - Suspicious motion detected: 42.5%
2026-03-23 13:16:30,124 - __main__ - CRITICAL - 🚨 SUSPICIOUS ACTIVITY DETECTED (Possible Theft)
```

---

## API Examples

### 1. Check System Status

**Request:**
```bash
curl http://localhost:8000/status
```

**Response:**
```json
{
  "running": true,
  "timestamp": "2026-03-23T13:15:45.123456"
}
```

### 2. Get All Events

**Request:**
```bash
curl http://localhost:8000/events?limit=5
```

**Response:**
```json
{
  "total": 5,
  "events": [
    {
      "id": 15,
      "timestamp": "2026-03-23T13:16:30.500000",
      "event_type": "theft_risk",
      "details": "Suspicious motion with people detected"
    },
    {
      "id": 14,
      "timestamp": "2026-03-23T13:16:15.400000",
      "event_type": "crowd_detected",
      "details": "3 people in same area"
    },
    {
      "id": 13,
      "timestamp": "2026-03-23T13:16:00.300000",
      "event_type": "rapid_movement",
      "details": "Rapid/suspicious movement detected"
    },
    {
      "id": 12,
      "timestamp": "2026-03-23T13:15:45.200000",
      "event_type": "loitering",
      "details": "Suspicious loitering detected"
    },
    {
      "id": 11,
      "timestamp": "2026-03-23T13:10:20.100000",
      "event_type": "test_alert",
      "details": "Test alert triggered: MANUAL_TEST"
    }
  ]
}
```

### 3. Get Events by Type

**Loitering events:**
```bash
curl http://localhost:8000/events/loitering?limit=10
```

**Crowd events:**
```bash
curl http://localhost:8000/events/crowd_detected?limit=10
```

**Rapid movement events:**
```bash
curl http://localhost:8000/events/rapid_movement?limit=10
```

### 4. Get Event Statistics

**Request:**
```bash
curl http://localhost:8000/events/stats/summary
```

**Response:**
```json
{
  "total_events": 47,
  "by_type": {
    "loitering": 12,
    "crowd_detected": 8,
    "rapid_movement": 15,
    "theft_risk": 9,
    "test_alert": 3
  },
  "timestamp": "2026-03-23T13:20:00.123456"
}
```

### 5. Send Test Alert

**Request:**
```bash
curl -X POST http://localhost:8000/alert/test \
  -H "Content-Type: application/json" \
  -d "{\"event_type\": \"MANUAL_TEST\"}"
```

**Response:**
```json
{
  "status": "alert_sent",
  "event_type": "MANUAL_TEST",
  "timestamp": "2026-03-23T13:21:00.123456",
  "alert_number": 5
}
```

Alert output in main.py terminal:
```
============================================================
🚨 SMS ALERT SENT (Testing Mode) - Alert #5
============================================================
Timestamp: 2026-03-23 13:21:00
To: +9876543210
Message: Alert: Suspicious activity detected.
============================================================
```

### 6. Start/Stop Monitoring

**Stop monitoring:**
```bash
curl -X POST http://localhost:8000/stop
```

Response:
```json
{
  "status": "stopped",
  "timestamp": "2026-03-23T13:25:00.123456"
}
```

**Start monitoring:**
```bash
curl -X POST http://localhost:8000/start
```

Response:
```json
{
  "status": "started",
  "timestamp": "2026-03-23T13:26:00.123456"
}
```

### 7. Health Check

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-23T13:27:00.123456",
  "monitoring": true
}
```

### 8. Access Interactive API Docs

Open in browser:
```
http://localhost:8000/docs
```

This gives you a Swagger UI where you can:
- See all endpoints
- Try requests with "Try it out" button
- See request/response examples
- Read parameter descriptions

---

## Database Queries

### View All Events

**Python:**
```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM events ORDER BY timestamp DESC")
for row in cursor.fetchall():
    print(row)
conn.close()
```

**PowerShell (if sqlite3 installed):**
```powershell
sqlite3 events.db "SELECT * FROM events ORDER BY timestamp DESC;"
```

### Count Events by Type

```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")
conn.close()
```

### Get Events from Last Hour

```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('events.db')
cursor = conn.cursor()
one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
cursor.execute("SELECT * FROM events WHERE timestamp > ? ORDER BY timestamp DESC", (one_hour_ago,))
for row in cursor.fetchall():
    print(row)
conn.close()
```

### Get Most Recent Event

```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 1")
print(cursor.fetchone())
conn.close()
```

### Delete Old Events (Keep Last 1000)

```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("""
    DELETE FROM events WHERE id NOT IN (
        SELECT id FROM events ORDER BY id DESC LIMIT 1000
    )
""")
conn.commit()
print(f"Deleted {cursor.rowcount} old events")
conn.close()
```

---

## Configuration Examples

### Example 1: High Sensitivity (Many Alerts)

**config.yaml:**
```yaml
camera:
  source: 0
  display_feed: true

detection:
  confidence: 0.35        # Lower = more detections

anomaly:
  loitering:
    enabled: true
    duration_sec: 3       # Fast alert
  crowd_detection:
    min_persons: 2        # Alert on 2+ people
  rapid_movement:
    motion_threshold: 50  # Low threshold
  theft_detection:
    enabled: true

alert:
  testing_mode: true
  cooldown_seconds: 15    # Frequent alerts
```

### Example 2: Low Sensitivity (Fewer False Alerts)

**config.yaml:**
```yaml
detection:
  confidence: 0.65        # Higher = fewer detections

anomaly:
  loitering:
    duration_sec: 20      # Slow alert
  crowd_detection:
    min_persons: 5        # Alert on 5+ people
  rapid_movement:
    movement_threshold: 250  # High threshold
  theft_detection:
    enabled: false

alert:
  cooldown_seconds: 120   # Rare alerts
```

### Example 3: IP Camera Setup

**config.yaml:**
```yaml
camera:
  source: "rtsp://admin:password@192.168.1.100:554/stream"
  width: 1920
  height: 1080
  fps: 30

detection:
  device: "cuda"  # Use GPU if available
```

### Example 4: Production with Real Alerts

**config.yaml:**
```yaml
alert:
  testing_mode: false
  twilio:
    account_sid: "AC8f294efee7a3c01f9b5d8f4a0f9c8e7"
    auth_token: "your_secret_token_here"
    from_number: "+18453334444"
    to_number: "+14165551234"
    voice_message: "ALERT! Suspicious activity detected at your store!"
    sms_message: "ALERT: Theft detected! Check CCTV immediately."
  cooldown_seconds: 60
```

---

## Common Use Cases

### Use Case 1: Retail Store Security

```yaml
camera:
  source: "rtsp://store-cam:password@10.0.0.5/stream"
  display_feed: false

anomaly:
  loitering:
    duration_sec: 10
  rapid_movement:
    movement_threshold: 100
  theft_detection:
    enabled: true

alert:
  testing_mode: false
  cooldown_seconds: 30
```

### Use Case 2: Home Security

```yaml
camera:
  source: 0  # Laptop webcam
  display_feed: true

anomaly:
  night_mode:
    enabled: true
    start_hour: 21
    end_hour: 7

alert:
  testing_mode: false
  cooldown_seconds: 60
```

### Use Case 3: Development/Testing

```yaml
camera:
  source: 0
  display_feed: true
  fps: 10

detection:
  confidence: 0.4

alert:
  testing_mode: true
  cooldown_seconds: 5  # Quick testing
```

---

## Tips & Tricks

### Monitor via SSH

```bash
# Run on remote server
ssh user@192.168.1.100
cd cctv
python main.py &
```

### Capture Video for Analysis

```bash
# Set in config.yaml and log all events
# Then analyze events.db later
sqlite3 events.db < analysis.sql
```

### Run Multiple Cameras

```bash
# Terminal 1
config_cam1.yaml: source: "rtsp://cam1..."
python main.py

# Terminal 2
config_cam2.yaml: source: "rtsp://cam2..."
PYTHONPATH=. python -c "from main import main; main()" &
```

### Automated Testing

```bash
# test.sh
#!/bin/bash
python test_system.py
python -c "
import time
from alert import AlertManager
am = AlertManager('x','x','x','x','test','test',testing_mode=True)
am.make_call()
am.send_sms()
"
echo 'Test complete'
```

---

**Last Updated:** March 23, 2026
**Status:** Production Ready
