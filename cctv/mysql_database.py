"""
MySQL Database module with fallback support
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import hashlib

logger = logging.getLogger(__name__)

# Try to import mysql-connector-python first, then fallback to PyMySQL
try:
    import mysql.connector
    MYSQL_CONNECTOR = True
    logger.info("Using mysql-connector-python")
except ImportError:
    MYSQL_CONNECTOR = False
    try:
        import pymysql
        logger.info("Using PyMySQL as fallback")
    except ImportError:
        logger.error("Neither mysql-connector-python nor PyMySQL is available")
        raise ImportError("Please install mysql-connector-python or PyMySQL")

class MySQLDatabase:
    def __init__(self, host='localhost', user='root', password='', database='cctv_security'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            if MYSQL_CONNECTOR:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    autocommit=True
                )
            else:
                self.connection = pymysql.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    autocommit=True,
                    cursorclass=pymysql.cursors.DictCursor
                )
            logger.info("✓ MySQL database connected successfully")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        try:
            if MYSQL_CONNECTOR:
                cursor = self.connection.cursor(dictionary=True)
            else:
                cursor = self.connection.cursor()
            
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def execute_non_query(self, query: str, params: tuple = None) -> int:
        try:
            if MYSQL_CONNECTOR:
                cursor = self.connection.cursor()
            else:
                cursor = self.connection.cursor()
            
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            logger.error(f"Non-query execution error: {e}")
            raise
    
    def get_last_insert_id(self) -> int:
        if MYSQL_CONNECTOR:
            return self.connection.insert_id()
        else:
            return self.connection.insert_id()
    
    # User management methods
    def create_user(self, username: str, email: str, password: str, full_name: str, 
                   phone: str = None, role_id: int = 1) -> int:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = """
        INSERT INTO users (username, email, password_hash, full_name, phone, role_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.execute_non_query(query, (username, email, password_hash, full_name, phone, role_id))
        return self.get_last_insert_id()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = """
        SELECT u.*, r.name as role_name, r.permissions
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.username = %s AND u.password_hash = %s AND u.is_active = TRUE
        """
        result = self.execute_query(query, (username, password_hash))
        return result[0] if result else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        query = """
        SELECT u.*, r.name as role_name, r.permissions,
               s.name as subscription_name, us.end_date, us.status,
               DATEDIFF(us.end_date, CURDATE()) as days_remaining
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN user_subscriptions us ON u.id = us.user_id AND us.status = 'active'
        LEFT JOIN subscriptions s ON us.subscription_id = s.id
        WHERE u.id = %s AND u.is_active = TRUE
        """
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None
    
    def get_all_users(self) -> List[Dict]:
        query = """
        SELECT u.*, r.name as role_name,
               s.name as subscription_name, us.end_date, us.status,
               DATEDIFF(us.end_date, CURDATE()) as days_remaining
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN user_subscriptions us ON u.id = us.user_id AND us.status = 'active'
        LEFT JOIN subscriptions s ON us.subscription_id = s.id
        WHERE u.is_active = TRUE
        ORDER BY u.created_at DESC
        """
        return self.execute_query(query)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
        query = f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        params = tuple(kwargs.values()) + (user_id,)
        return self.execute_non_query(query, params) > 0
    
    def delete_user(self, user_id: int) -> bool:
        return self.execute_non_query("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,)) > 0
    
    # Detection events methods
    def log_detection_event(self, user_id: int, event_type: str, confidence: float = None,
                           bbox_coordinates: Dict = None, details: str = None, camera_id: str = None) -> int:
        query = """
        INSERT INTO detection_events (user_id, camera_id, event_type, confidence, bbox_coordinates, details)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (user_id, camera_id, event_type, confidence, 
                 json.dumps(bbox_coordinates) if bbox_coordinates else None, details)
        self.execute_non_query(query, params)
        return self.get_last_insert_id()
    
    def get_detection_events(self, user_id: int, limit: int = 100, event_type: str = None,
                           start_date: str = None, end_date: str = None) -> List[Dict]:
        query = """
        SELECT de.*, ci.file_path as image_path, ci.thumbnail_path
        FROM detection_events de
        LEFT JOIN captured_images ci ON de.id = ci.event_id AND ci.is_deleted = FALSE
        WHERE de.user_id = %s
        """
        params = [user_id]
        
        if event_type:
            query += " AND de.event_type = %s"
            params.append(event_type)
        
        if start_date:
            query += " AND de.timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND de.timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY de.timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def delete_detection_event(self, event_id: int, user_id: int) -> bool:
        # Mark associated images as deleted
        self.execute_non_query(
            "UPDATE captured_images SET is_deleted = TRUE WHERE event_id = %s AND user_id = %s",
            (event_id, user_id)
        )
        # Delete the event
        return self.execute_non_query("DELETE FROM detection_events WHERE id = %s AND user_id = %s", 
                                  (event_id, user_id)) > 0
    
    # Image management methods
    def save_captured_image(self, event_id: int, user_id: int, file_path: str, 
                           file_size: int, thumbnail_path: str = None) -> int:
        query = """
        INSERT INTO captured_images (event_id, user_id, file_path, file_size, thumbnail_path)
        VALUES (%s, %s, %s, %s, %s)
        """
        self.execute_non_query(query, (event_id, user_id, file_path, file_size, thumbnail_path))
        return self.get_last_insert_id()
    
    def get_user_images(self, user_id: int, limit: int = 100) -> List[Dict]:
        query = """
        SELECT ci.*, de.event_type, de.details, de.timestamp as event_timestamp
        FROM captured_images ci
        JOIN detection_events de ON ci.event_id = de.id
        WHERE ci.user_id = %s AND ci.is_deleted = FALSE
        ORDER BY ci.timestamp DESC
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    def cleanup_expired_images(self) -> int:
        # Call the stored procedure
        try:
            result = self.execute_query("CALL CleanupExpiredImages()")
            return result[0]['images_cleaned'] if result else 0
        except Exception as e:
            logger.warning(f"Could not call cleanup procedure: {e}")
            # Fallback: manually delete expired images
            query = """
            UPDATE captured_images 
            SET is_deleted = TRUE 
            WHERE expires_at < NOW() AND is_deleted = FALSE
            """
            return self.execute_non_query(query)
    
    # Video recording methods
    def save_video_recording(self, user_id: int, camera_id: str, file_path: str,
                            file_size: int, duration_seconds: int, start_time: datetime,
                            end_time: datetime, recording_type: str = 'event_triggered',
                            thumbnail_path: str = None) -> int:
        query = """
        INSERT INTO video_recordings 
        (user_id, camera_id, file_path, file_size, duration_seconds, 
         thumbnail_path, start_time, end_time, recording_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (user_id, camera_id, file_path, file_size, duration_seconds,
                 thumbnail_path, start_time, end_time, recording_type)
        self.execute_non_query(query, params)
        return self.get_last_insert_id()
    
    def get_user_videos(self, user_id: int, limit: int = 50) -> List[Dict]:
        query = """
        SELECT * FROM video_recordings
        WHERE user_id = %s AND is_deleted = FALSE
        ORDER BY start_time DESC
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    # Subscription management methods
    def get_subscriptions(self) -> List[Dict]:
        return self.execute_query("SELECT * FROM subscriptions WHERE is_active = TRUE ORDER BY price")
    
    def create_user_subscription(self, user_id: int, subscription_id: int, 
                                start_date: datetime, end_date: datetime) -> int:
        query = """
        INSERT INTO user_subscriptions (user_id, subscription_id, start_date, end_date)
        VALUES (%s, %s, %s, %s)
        """
        self.execute_non_query(query, (user_id, subscription_id, start_date, end_date))
        return self.get_last_insert_id()
    
    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        query = """
        SELECT us.*, s.name as subscription_name, s.features, s.price
        FROM user_subscriptions us
        JOIN subscriptions s ON us.subscription_id = s.id
        WHERE us.user_id = %s AND us.status = 'active'
        ORDER BY us.end_date DESC
        LIMIT 1
        """
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None
    
    def cancel_subscription(self, user_id: int) -> bool:
        return self.execute_non_query(
            "UPDATE user_subscriptions SET status = 'cancelled' WHERE user_id = %s AND status = 'active'",
            (user_id,)
        ) > 0
    
    def get_expiring_subscriptions(self, days: int = 7) -> List[Dict]:
        query = """
        SELECT u.id, u.username, u.email, s.name as subscription_name, us.end_date,
               DATEDIFF(us.end_date, CURDATE()) as days_remaining
        FROM users u
        JOIN user_subscriptions us ON u.id = us.user_id
        JOIN subscriptions s ON us.subscription_id = s.id
        WHERE us.status = 'active' 
        AND DATEDIFF(us.end_date, CURDATE()) BETWEEN 0 AND %s
        ORDER BY us.end_date ASC
        """
        return self.execute_query(query, (days,))
    
    # System logging
    def log_system_action(self, user_id: int, action: str, details: str = None,
                         ip_address: str = None, user_agent: str = None) -> int:
        query = """
        INSERT INTO system_logs (user_id, action, details, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s)
        """
        self.execute_non_query(query, (user_id, action, details, ip_address, user_agent))
        return self.get_last_insert_id()
    
    def get_system_logs(self, limit: int = 100, user_id: int = None) -> List[Dict]:
        query = """
        SELECT sl.*, u.username
        FROM system_logs sl
        LEFT JOIN users u ON sl.user_id = u.id
        """
        params = []
        
        if user_id:
            query += " WHERE sl.user_id = %s"
            params.append(user_id)
        
        query += " ORDER BY sl.timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
