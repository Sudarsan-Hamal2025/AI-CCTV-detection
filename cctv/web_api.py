from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import os
import cv2
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import io
from mysql_database import MySQLDatabase
from auth import AuthenticationManager

# Initialize FastAPI app
app = FastAPI(title="CCTV Security System Web API", version="2.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve only uploads (dashboard frontend removed)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Security
security = HTTPBearer()

# Initialize database and auth
db = MySQLDatabase()
auth_manager = AuthenticationManager(db)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create upload directories
os.makedirs("uploads/images", exist_ok=True)
os.makedirs("uploads/videos", exist_ok=True)
os.makedirs("uploads/thumbnails", exist_ok=True)

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role_id: int = 1

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class SubscriptionCreate(BaseModel):
    user_id: int
    subscription_id: int
    duration_days: int

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check subscription status
    if not auth_manager.is_subscription_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription expired or inactive"
        )
    
    return user

# Permission checking decorator
def require_permission(permission: str):
    def decorator(current_user: Dict[str, Any] = Depends(get_current_user)):
        if not auth_manager.check_permission(current_user['permissions'], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return decorator

def require_role(roles: List[str]):
    def decorator(current_user: Dict[str, Any] = Depends(get_current_user)):
        if not auth_manager.require_role(current_user['role_name'], roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {roles} required"
            )
        return current_user
    return decorator

# Authentication endpoints
@app.post("/api/auth/login")
async def login(request: LoginRequest):
    result = auth_manager.login_user(request.username, request.password)
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result['message']
        )
    return result

@app.post("/api/auth/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    auth_manager.logout_user(current_user['id'])
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

@app.post("/api/auth/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    result = auth_manager.change_password(
        current_user['id'],
        password_data.old_password,
        password_data.new_password
    )
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )
    return result

# Dashboard endpoints removed (not used in stripped-down deployment)

# Detection endpoints
@app.get("/api/detections")
async def get_detections(
    limit: int = 100,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        detections = db.get_detection_events(
            current_user['id'],
            limit=limit,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date
        )
        return detections
    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get detections")

@app.get("/api/detections/recent")
async def get_recent_detections(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        detections = db.get_detection_events(current_user['id'], limit=limit)
        return detections
    except Exception as e:
        logger.error(f"Error getting recent detections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent detections")

@app.delete("/api/detections/{detection_id}")
async def delete_detection(
    detection_id: int,
    current_user: Dict[str, Any] = Depends(require_permission("delete_detections"))
):
    try:
        success = db.delete_detection_event(detection_id, current_user['id'])
        if not success:
            raise HTTPException(status_code=404, detail="Detection not found")
        return {"message": "Detection deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting detection: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete detection")

# Image endpoints
@app.get("/api/images")
async def get_images(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        images = db.get_user_images(current_user['id'], limit=limit)
        return images
    except Exception as e:
        logger.error(f"Error getting images: {e}")
        raise HTTPException(status_code=500, detail="Failed to get images")

@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    event_id: Optional[int] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Save uploaded image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{current_user['id']}_{timestamp}_{file.filename}"
        file_path = f"uploads/images/{filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create thumbnail
        thumbnail_path = await create_thumbnail(file_path, f"uploads/thumbnails/thumb_{filename}")
        
        # Save to database
        if event_id:
            db.save_captured_image(
                event_id=event_id,
                user_id=current_user['id'],
                file_path=file_path,
                file_size=len(content),
                thumbnail_path=thumbnail_path
            )
        
        return {
            "message": "Image uploaded successfully",
            "file_path": file_path,
            "thumbnail_path": thumbnail_path
        }
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

# Video endpoints
@app.get("/api/videos")
async def get_videos(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        videos = db.get_user_videos(current_user['id'], limit=limit)
        return videos
    except Exception as e:
        logger.error(f"Error getting videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to get videos")

# User management endpoints (Admin/Super Admin only)
@app.get("/api/users")
async def get_users(
    current_user: Dict[str, Any] = Depends(require_permission("manage_users"))
):
    try:
        users = db.get_all_users()
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@app.post("/api/users")
async def create_user(
    user_data: UserCreate,
    current_user: Dict[str, Any] = Depends(require_permission("manage_users"))
):
    try:
        user_id = db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone,
            role_id=user_data.role_id
        )
        
        db.log_system_action(
            user_id=current_user['id'],
            action='user_created',
            details=f"Created user: {user_data.username}"
        )
        
        return {"message": "User created successfully", "user_id": user_id}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.put("/api/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(require_permission("manage_users"))
):
    try:
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        success = db.update_user(user_id, **update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.log_system_action(
            user_id=current_user['id'],
            action='user_updated',
            details=f"Updated user ID: {user_id}"
        )
        
        return {"message": "User updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_role(["super_admin"]))
):
    try:
        success = db.delete_user(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.log_system_action(
            user_id=current_user['id'],
            action='user_deleted',
            details=f"Deleted user ID: {user_id}"
        )
        
        return {"message": "User deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

# Subscription endpoints
@app.get("/api/subscriptions")
async def get_subscriptions(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        subscriptions = db.get_subscriptions()
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscriptions")

@app.post("/api/subscriptions/assign")
async def assign_subscription(
    subscription_data: SubscriptionCreate,
    current_user: Dict[str, Any] = Depends(require_permission("manage_subscriptions"))
):
    try:
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=subscription_data.duration_days)
        
        subscription_id = db.create_user_subscription(
            user_id=subscription_data.user_id,
            subscription_id=subscription_data.subscription_id,
            start_date=start_date,
            end_date=end_date
        )
        
        db.log_system_action(
            user_id=current_user['id'],
            action='subscription_assigned',
            details=f"Assigned subscription to user ID: {subscription_data.user_id}"
        )
        
        return {"message": "Subscription assigned successfully", "subscription_id": subscription_id}
    except Exception as e:
        logger.error(f"Error assigning subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign subscription")

@app.delete("/api/subscriptions/{user_id}")
async def cancel_subscription(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_permission("cancel_subscription"))
):
    try:
        success = db.cancel_subscription(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        db.log_system_action(
            user_id=current_user['id'],
            action='subscription_cancelled',
            details=f"Cancelled subscription for user ID: {user_id}"
        )
        
        return {"message": "Subscription cancelled successfully"}
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

# Camera feed endpoint
@app.get("/api/camera/feed")
async def get_camera_feed():
    # This would integrate with the main camera system
    # For now, return a placeholder or test image
    placeholder_path = "web/static/camera-placeholder.jpg"
    if not os.path.exists(placeholder_path):
        logger.warning(f"Camera placeholder not found: {placeholder_path}")
        raise HTTPException(status_code=404, detail="Placeholder image not found")
    return FileResponse(placeholder_path, media_type="image/jpeg")

# System endpoints (Super Admin only)
@app.get("/api/system/logs")
async def get_system_logs(
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(require_role(["super_admin"]))
):
    try:
        logs = db.get_system_logs(limit=limit)
        return logs
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system logs")

@app.post("/api/system/cleanup")
async def cleanup_expired_images(
    current_user: Dict[str, Any] = Depends(require_role(["super_admin"]))
):
    try:
        images_cleaned = db.cleanup_expired_images()
        
        db.log_system_action(
            user_id=current_user['id'],
            action='cleanup_performed',
            details=f"Cleaned up {images_cleaned} expired images"
        )
        
        return {"message": f"Cleaned up {images_cleaned} expired images"}
    except Exception as e:
        logger.error(f"Error performing cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform cleanup")

# Helper functions
async def create_thumbnail(image_path: str, thumbnail_path: str, size=(200, 200)):
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        height, width = img.shape[:2]
        aspect_ratio = width / height
        
        if aspect_ratio > 1:
            new_width = size[0]
            new_height = int(size[0] / aspect_ratio)
        else:
            new_height = size[1]
            new_width = int(size[1] * aspect_ratio)
        
        resized = cv2.resize(img, (new_width, new_height))
        cv2.imwrite(thumbnail_path, resized)
        
        return thumbnail_path
    except Exception as e:
        logger.error(f"Error creating thumbnail: {e}")
        return None

# Web interface removed; dashboard migration means root no longer serves UI.
@app.get("/")
async def root_removed():
    raise HTTPException(status_code=404, detail="UI removed")

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
