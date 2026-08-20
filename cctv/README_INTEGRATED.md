# CCTV Security System - Complete Web Dashboard

A comprehensive CCTV monitoring system with web-based dashboard, role-based access control, and subscription management.

## 🚀 Features

### Core Functionality
- **Real-time Detection**: Person, vehicle, and anomaly detection using YOLOv8
- **Multiple Detection Types**: Night intrusion, loitering, crowd detection, rapid movement, theft risk
- **Video Recording**: Continuous and event-triggered recording with automatic thumbnail generation
- **Image Capture**: Automatic image capture on detection events with 30-day auto-cleanup
- **Alert System**: SMS and voice alerts via Twilio integration

### Web Dashboard
- **Role-Based Access Control**: User, Admin, and Super Admin roles
- **Real-time Dashboard**: Live camera feed, detection statistics, recent events
- **Image Gallery**: View and manage captured detection images
- **Video Gallery**: Browse and playback recorded videos
- **Responsive Design**: Works on desktop, tablet, and mobile devices

### User Management
- **User Roles**:
  - **User**: View detections and images
  - **Admin**: Edit/delete detections, view subscription info
  - **Super Admin**: Full system control, user management, subscription management

### Subscription System
- **Tiered Plans**: Basic, Professional, Enterprise
- **Feature Limits**: Camera count, storage space, detection types
- **Automated Management**: Expiration notifications, renewal reminders
- **Payment Integration Ready**: Structure for payment gateway integration

### System Administration
- **User Management**: Create, edit, delete users with role assignment
- **Subscription Management**: Create plans, assign subscriptions, track revenue
- **System Monitoring**: Storage usage, system logs, performance metrics
- **Maintenance Tools**: Automated cleanup, database optimization, backup tools

## 📋 System Requirements

### Hardware Requirements
- **CPU**: Intel i5 or equivalent (recommended: i7 or higher)
- **RAM**: 8GB minimum (recommended: 16GB or higher)
- **Storage**: 100GB minimum SSD (recommended: 500GB+ for video storage)
- **Camera**: USB webcam or IP camera with RTSP support

### Software Requirements
- **Operating System**: Windows 10/11, Linux (Ubuntu 18.04+), or macOS 10.14+
- **Python**: 3.8 or higher
- **MySQL**: 5.7 or higher / 8.0+ recommended
- **Web Browser**: Chrome 90+, Firefox 88+, Safari 14+

## 🛠️ Installation

### 1. Clone/Download the System
```bash
# If using git
git clone <repository-url>
cd cctv

# Or download and extract the files
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install MySQL Server
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# Windows
# Download and install MySQL Community Server from https://dev.mysql.com/downloads/mysql/

# macOS
brew install mysql
```

### 4. Configure Database
```bash
# Start MySQL service
sudo systemctl start mysql  # Linux
brew services start mysql    # macOS

# Create database user (optional)
mysql -u root -p
CREATE USER 'cctv_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON *.* TO 'cctv_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Run Setup Script
```bash
python setup.py
```

This will:
- Create the database schema
- Set up required directories
- Create default admin user
- Create sample subscription plans

### 6. Download YOLOv8 Model
```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 7. Configure System
Edit `config.yaml` to match your setup:
```yaml
# Database configuration
database:
  host: localhost
  user: root
  password: your_mysql_password
  database: cctv_security

# Camera configuration
camera:
  source: 0  # Use 0 for webcam, or rtsp://... for IP camera
  width: 640
  height: 480
  fps: 15

# Alert configuration (Twilio)
alert:
  testing_mode: true  # Set to false for real alerts
  twilio:
    account_sid: your_account_sid
    auth_token: your_auth_token
    from_number: your_twilio_number
    to_number: your_phone_number
```

## 🚀 Running the System

### Method 1: Integrated System (Recommended)
```bash
python integrated_system.py
```

This starts:
- Detection engine
- Web server (port 8000)
- Cleanup scheduler
- Video recording

### Method 2: Web Server Only
```bash
python web_api.py
```

### Method 3: Legacy System
```bash
python main.py
```

## 🌐 Web Interface

### Access the Dashboard
1. Open your web browser
2. Go to `http://localhost:8000`
3. Login with default credentials:
   - Username: `superadmin`
   - Password: `admin123`

### First Steps
1. **Change Default Password**: Go to Profile → Change Password
2. **Create Users**: Admin Panel → Users → Add New User
3. **Configure Camera**: Update camera settings in config.yaml
4. **Test Detection**: Trigger a detection to verify the system works

## 📊 User Roles and Permissions

### User
- ✅ View dashboard and statistics
- ✅ View detection events
- ✅ View captured images
- ✅ View recorded videos
- ❌ Edit/delete detections
- ❌ Manage users
- ❌ Access admin panel

### Admin
- ✅ All User permissions
- ✅ Edit/delete detection events
- ✅ View subscription information
- ✅ Manage user subscriptions
- ❌ Delete users
- ❌ Access system administration

### Super Admin
- ✅ All Admin permissions
- ✅ Create/edit/delete users
- ✅ Manage subscription plans
- ✅ View system logs
- ✅ Perform system maintenance
- ✅ Emergency system controls

## 💾 Storage Management

### Automatic Cleanup
- **Images**: Deleted after 30 days
- **Videos**: Deleted after 60 days (configurable)
- **Logs**: Deleted after 90 days
- **Temp Files**: Cleaned hourly

### Manual Cleanup
```python
# Via web interface
Admin Panel → System → Cleanup

# Via API
POST /api/system/cleanup

# Via code
from cleanup_scheduler import CleanupScheduler
scheduler = CleanupScheduler(db)
scheduler.run_manual_cleanup("all")
```

## 🔧 Configuration Options

### Detection Settings
```yaml
detection:
  model: "yolov8n.pt"  # Model file
  confidence: 0.45     # Detection confidence threshold
  classes: [0]         # COCO classes to detect (0 = person)
  device: "cpu"        # "cuda" for GPU acceleration

anomaly:
  loitering:
    enabled: true
    duration_sec: 60    # Seconds to consider loitering
  crowd_detection:
    enabled: true
    min_persons: 2      # Alert if 2+ people detected
  rapid_movement:
    enabled: false
    movement_threshold: 100
  theft_detection:
    enabled: false
```

### Video Recording
```yaml
video:
  output_dir: "uploads/videos"
  fps: 15
  width: 640
  height: 480
  max_file_size_mb: 100
  max_duration_minutes: 30
  record_on_detection: true
  event_duration: 30
```

### Subscription Plans
```yaml
subscriptions:
  basic:
    price: 29.99
    duration_days: 30
    max_cameras: 1
    max_storage_gb: 10
    features:
      detection_types: ["person"]
      video_recording: false
      alerts: true
```

## 📱 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/change-password` - Change password

### Detections
- `GET /api/detections` - Get detection events
- `GET /api/detections/recent` - Get recent detections
- `DELETE /api/detections/{id}` - Delete detection

### Images & Videos
- `GET /api/images` - Get captured images
- `POST /api/images/upload` - Upload image
- `GET /api/videos` - Get recorded videos

### User Management (Admin+)
- `GET /api/users` - Get all users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Subscriptions (Admin+)
- `GET /api/subscriptions` - Get subscription plans
- `POST /api/subscriptions/assign` - Assign subscription
- `DELETE /api/subscriptions/{user_id}` - Cancel subscription

### System (Super Admin)
- `GET /api/system/logs` - Get system logs
- `POST /api/system/cleanup` - Perform cleanup

## 🔍 Troubleshooting

### Common Issues

#### Camera Not Working
```bash
# Check camera devices
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"

# For IP cameras, test RTSP URL
ffplay rtsp://username:password@ip:port/stream
```

#### Database Connection Error
```bash
# Check MySQL service
sudo systemctl status mysql

# Test connection
mysql -h localhost -u root -p

# Check database exists
mysql -u root -p -e "SHOW DATABASES;"
```

#### Model Not Found
```bash
# Download YOLOv8 model
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Check model file
ls -la yolov8n.pt
```

#### Web Server Not Accessible
```bash
# Check port 8000 is free
netstat -tulpn | grep 8000

# Test locally
curl http://localhost:8000

# Check firewall settings
sudo ufw status
```

### Performance Optimization

#### GPU Acceleration
```yaml
detection:
  device: "cuda"  # Enable GPU
```

#### Reduce Resolution/FPS
```yaml
camera:
  width: 320      # Reduce from 640
  height: 240     # Reduce from 480
  fps: 10         # Reduce from 15
```

#### Optimize Database
```sql
-- Add indexes for better performance
CREATE INDEX idx_events_user_timestamp ON detection_events(user_id, timestamp);
CREATE INDEX idx_images_user_timestamp ON captured_images(user_id, timestamp);
```

## 📈 Monitoring and Analytics

### System Metrics
- User registrations and activity
- Detection event statistics
- Storage usage trends
- Subscription revenue

### Accessing Analytics
1. Login as Super Admin
2. Go to Admin Panel → Analytics
3. View charts and reports

### API for Custom Analytics
```python
# Get system overview
from super_admin_features import SuperAdminFeatures
admin = SuperAdminFeatures(db, auth, sub_manager, cleanup)
overview = admin.get_system_overview()

# Get analytics
analytics = admin.get_system_analytics(days=30)
```

## 🔒 Security Considerations

### Default Passwords
- Change the default super admin password immediately
- Use strong passwords for all users
- Enable password complexity requirements

### Network Security
- Use HTTPS in production (SSL/TLS)
- Configure firewall rules
- Limit database access to localhost

### Data Protection
- Regular backups of database
- Encrypt sensitive data
- Implement GDPR compliance features

## 📞 Support

### Documentation
- Check this README file
- Review inline code comments
- Check API documentation at `/docs` (when running)

### Common Questions
- **Q: Can I use multiple cameras?**
  A: Yes, upgrade to Professional or Enterprise plan for multiple cameras

- **Q: How do I add custom detection types?**
  A: Modify the detection classes in config.yaml and retrain YOLO model

- **Q: Can I integrate with other systems?**
  A: Yes, use the REST API or extend the system with custom modules

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Roadmap

### Upcoming Features
- [ ] Mobile app (iOS/Android)
- [ ] Cloud storage integration
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Facial recognition
- [ ] License plate recognition
- [ ] Integration with home automation systems
- [ ] WebRTC live streaming
- [ ] AI-powered behavior analysis

### Version History
- **v2.0.0** - Complete web dashboard with subscription system
- **v1.0.0** - Basic detection and alert system

---

**Built with ❤️ using Python, FastAPI, OpenCV, and YOLOv8**
