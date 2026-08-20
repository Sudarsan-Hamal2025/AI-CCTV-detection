# 🚨 CCTV Security System - Quick Start Guide

## ✅ System Status: READY

All components installed and tested successfully! 

```
✓ All packages installed
✓ Webcam detected
✓ Database initialized
✓ All anomaly detectors working
✓ Alert system operational
✓ REST API configured
```

---

## 🚀 Start the System (2 seconds)

```bash
python main.py
```

You'll see:
```
==========================================================
CCTV Security System Starting...
==========================================================
✓ Camera started successfully
✓ API server started on http://0.0.0.0:8000
Starting main detection loop...
  - Loitering detection: True
  - Crowd detection: True
  - Rapid movement detection: True
  - Theft detection: True
  - Alert cooldown: 30s
==========================================================
```

**System is now monitoring your webcam!** 📹

---

## 🧪 Test the System

### Option 1: Test with Webcam (Recommended)
1. Keep main.py running
2. Move in front of your laptop camera
3. Stay still for 8+ seconds → **Loitering Alert** ✅
4. Move rapidly side-to-side → **Rapid Movement Alert** ✅
5. Get 3 people → **Crowd Detection Alert** ✅

### Option 2: Trigger Alert via API
In another terminal:
```bash
curl -X POST http://localhost:8000/alert/test ^
  -H "Content-Type: application/json" ^
  -d "{\"event_type\": \"MANUAL_TEST\"}"
```

You'll see:
```
============================================================
🚨 SMS ALERT SENT (Testing Mode) - Alert #1
============================================================
Timestamp: 2026-03-23 13:08:34
To: +9876543210
Message: Alert: Suspicious activity detected.
============================================================
```

### Option 3: Check Events via API
```bash
curl http://localhost:8000/events?limit=5
curl http://localhost:8000/events/stats/summary
```

---

## 📱 What Gets Detected?

| Detection Type | Trigger | Alert |
|---|---|---|
| **Loitering** | Person stays 8+ seconds in same spot | ⚠️ SMS + Call |
| **Crowd** | 3+ people in frame | ⚠️ SMS + Call |
| **Rapid Movement** | Person moves 100+ pixels per frame | ⚠️ SMS + Call |
| **Suspicious Motion** | High motion + person present | ⚠️ SMS + Call |
| **Night Intrusion** | Person detected at night (disabled) | ⚠️ SMS + Call |

---

## 🎥 Live Feed Visualization (Optional)

Edit `config.yaml`:
```yaml
camera:
  display_feed: true  # Change to true
```

Then run `python main.py` to see:
- Real-time video with detection boxes
- Confidence scores
- Frame counter
- Person count

**Press 'Q' to quit**

---

## 🔌 REST API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/status` | GET | Check if monitoring is running |
| `/start` | POST | Start monitoring |
| `/stop` | POST | Stop monitoring |
| `/events?limit=10` | GET | Get last 10 events |
| `/events/{type}` | GET | Get events by type |
| `/events/stats/summary` | GET | Get statistics |
| `/alert/test` | POST | Send test alert |
| `/health` | GET | Health check |

**Access API docs:**
- Open http://localhost:8000/docs in browser
- Full interactive documentation with "Try it out" buttons

---

## 📊 View Event Database

View recent events:
```bash
python
```

```python
import sqlite3
conn = sqlite3.connect('events.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 20")
for row in cursor.fetchall():
    print(row)
conn.close()
```

Or on Windows PowerShell:
```powershell
sqlite3 events.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;"
```

---

## ⚙️ Customize Detection Sensitivity

Edit `config.yaml` to adjust detection behavior:

### More Sensitive (More Alerts)
```yaml
anomaly:
  loitering:
    duration_sec: 3        # Alert faster (was 8)
  rapid_movement:
    movement_threshold: 50 # Lower threshold
```

### Less Sensitive (Fewer False Alerts)
```yaml
anomaly:
  loitering:
    duration_sec: 15       # Alert slower (was 8)
  rapid_movement:
    movement_threshold: 200 # Higher threshold
  
alert:
  cooldown_seconds: 60    # Less frequent alerts (was 30)
```

---

## 📞 Setup Real Twilio Alerts

To send actual SMS and voice calls:

1. **Get Twilio Account:**
   - Go to https://www.twilio.com
   - Sign up and verify phone number
   - Get `Account SID` and `Auth Token`
   - Get a Twilio phone number

2. **Update config.yaml:**
   ```yaml
   alert:
     testing_mode: false  # ← Change this
     twilio:
       account_sid: "ACxxxxxxxxxxxxx"
       auth_token: "your_token_here"
       from_number: "+1234567890"    # Your Twilio number
       to_number: "+9876543210"      # Admin phone number
   ```

3. **Restart the system**
   ```bash
   python main.py
   ```

---

## 🛑 Stop the System

Press `Ctrl+C` in the terminal running `python main.py`

```
2026-03-23 13:25:45,123 - __main__ - INFO - Shutting down (Ctrl+C)...
2026-03-23 13:25:45,456 - __main__ - INFO - Cleaning up...
==========================================================
CCTV Security System Stopped
Total frames processed: 15234
Total events logged: Check events.db for details
==========================================================
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| "Camera failed to open" | Close other apps using webcam (Zoom, Teams, etc.) |
| "No alerts triggered" | Check camera view, move more dramatically, lower sensitivity |
| "False alerts" | Increase cooldown_seconds and thresholds in config.yaml |
| "API not working" | Check if port 8000 is available |
| "Detection very slow" | Use GPU (`device: "cuda"` in config), lower resolution, use smaller model |

---

## 📂 Project Files

```
cctv/
├── main.py              ← START HERE (python main.py)
├── config.yaml          ← Customize settings here
├── test_system.py       ← Run tests (python test_system.py)
├── README.md            ← Full documentation
├── camera.py            ← Webcam interface
├── detection.py         ← YOLOv8 object detection
├── anomaly.py           ← Suspicious activity detection (loitering, crowd, etc.)
├── alert.py             ← Alert notifications (SMS/Call)
├── api.py               ← REST API endpoints
├── database.py          ← Event logging
└── events.db            ← Event database (auto-created)
```

---

## 🎯 Next Steps

1. ✅ Run `python main.py` and test with webcam
2. ✅ Trigger some alerts to see them work
3. ✅ Check events via API
4. 📱 Get Twilio account and enable real alerts
5. 🎥 Deploy to actual camera (change source in config.yaml)
6. 📊 Monitor events dashboard

---

## 💡 Pro Tips

- **API Documentation:** Open http://localhost:8000/docs while system running
- **View Logs:** Check `surveillance.log` for detailed logs
- **Database:** Events persist in `events.db` even after restart
- **Performance:** Use lower resolution and YOLOv8n for faster processing
- **Reliability:** System runs in background, can be controlled via API

---

## 🆘 Need Help?

1. Check [README.md](README.md) for detailed documentation
2. Run tests: `python test_system.py`
3. Check logs: `tail -f surveillance.log`
4. Test API: http://localhost:8000/docs

---

**System Ready! 🚀** 

Run: `python main.py`
