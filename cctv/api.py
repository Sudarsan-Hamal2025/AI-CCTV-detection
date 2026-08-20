from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import os
import cv2

app = FastAPI(title="CCTV Security System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep uploads access only (for backwards compatibility)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Dashboard UI has been removed; root path is intentionally not served.
@app.get("/", include_in_schema=False)
def frontend_root_removed():
    raise HTTPException(status_code=404, detail="Dashboard UI removed")

# Global references to be set by main
system_state = {
    "running": False,
    "db": None,
    "alert_manager": None,
    "camera": None,
}

class LoginRequest(BaseModel):
    username: str
    password: str

class TestAlertRequest(BaseModel):
    event_type: str = "TEST_ALERT"

@app.post("/api/auth/login")
def login(request: LoginRequest):
    # Simple local auth for the demo console — credentials come from env vars
    admin_username = os.getenv('DEMO_ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('DEMO_ADMIN_PASSWORD', 'admin')
    if request.username == admin_username and request.password == admin_password:
        return {
            "success": True,
            "token": "demo-token",
            "user": {
                "id": 1,
                "username": "admin",
                "full_name": "Administrator",
                "role_name": "admin",
                "permissions": {"delete_detections": True},
                "days_remaining": 365
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/status")
def api_status():
    return {
        "running": system_state["running"],
        "timestamp": datetime.now().isoformat(),
    }

@app.post("/api/start")
def start_monitoring():
    if system_state["running"]:
        raise HTTPException(status_code=400, detail="Already running")
    system_state["running"] = True
    return {"status": "started", "timestamp": datetime.now().isoformat()}

@app.post("/api/stop")
def stop_monitoring():
    system_state["running"] = False
    return {"status": "stopped", "timestamp": datetime.now().isoformat()}

@app.get("/api/events")
def get_events(limit: int = 100, event_type: str = None):
    if not system_state["db"]:
        raise HTTPException(status_code=500, detail="Database not initialized")
    events = system_state["db"].get_recent_events(limit)
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    return {
        "total": len(events),
        "events": events
    }

@app.get("/api/detections")
def get_detections(limit: int = 100, event_type: str = None):
    return get_events(limit=limit, event_type=event_type)

@app.get("/api/events/recent")
def get_recent_events(limit: int = 10):
    if not system_state["db"]:
        raise HTTPException(status_code=500, detail="Database not initialized")
    events = system_state["db"].get_recent_events(limit)
    return events

# Dashboard stats endpoint removed.
@app.get("/api/camera/feed")
def camera_feed(camera_id: str = None):
    camera = None
    if camera_id:
        cameras = system_state.get("cameras") or []
        camera_info = next((c for c in cameras if c["id"] == camera_id), None)
        if camera_info:
            camera = camera_info["camera"]
    else:
        camera = system_state.get("camera")

    if camera is None:
        raise HTTPException(status_code=503, detail="Camera not initialized")

    def frame_generator():
        while system_state["running"]:
            frame = camera.get_latest_frame()
            if frame is None:
                continue
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    return StreamingResponse(frame_generator(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get("/api/images")
def get_images(limit: int = 50):
    if not system_state["db"]:
        raise HTTPException(status_code=500, detail="Database not initialized")
    events = system_state["db"].get_recent_events(limit)
    return [e for e in events if e.get("image_path")]

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "monitoring": system_state["running"]
    }

@app.post("/api/alert/test")
def test_alert(request: TestAlertRequest):
    if not system_state["alert_manager"]:
        raise HTTPException(status_code=500, detail="Alert manager not initialized")

    am = system_state["alert_manager"]
    if not am.testing_mode:
        raise HTTPException(status_code=403, detail="Test mode disabled")

    am.send_alert(request.event_type)
    if system_state["db"]:
        system_state["db"].log_event("test_alert", f"Test alert: {request.event_type}")
    return {"status": "alert_sent", "event_type": request.event_type, "timestamp": datetime.now().isoformat()}

@app.post("/api/clear-alerts")
def clear_alert_counter():
    if not system_state["alert_manager"]:
        raise HTTPException(status_code=500, detail="Alert manager not initialized")
    old = system_state["alert_manager"].alert_count
    system_state["alert_manager"].alert_count = 0
    return {"message": f"Alert counter reset from {old} to 0", "timestamp": datetime.now().isoformat()}

@app.get("/api/events/stats/summary")
def get_event_summary(limit: int = 1000):
    if not system_state["db"]:
        raise HTTPException(status_code=500, detail="Database not initialized")
    all_events = system_state["db"].get_recent_events(limit)
    summary = {}
    for event in all_events:
        summary[event["event_type"]] = summary.get(event["event_type"], 0) + 1
    return {"total_events": len(all_events), "by_type": summary, "timestamp": datetime.now().isoformat()}


def run_api(host="0.0.0.0", port=8000):
    uvicorn.run(app, host=host, port=port, log_level="info")

