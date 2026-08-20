import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                details TEXT,
                image_path TEXT,
                camera_id TEXT,
                camera_name TEXT,
                camera_location TEXT
            )
        ''')

        # Migration support: add columns if missing from old schema
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'image_path' not in columns:
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN image_path TEXT")
            except Exception:
                pass
        if 'camera_id' not in columns:
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN camera_id TEXT")
            except Exception:
                pass
        if 'camera_name' not in columns:
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN camera_name TEXT")
            except Exception:
                pass
        if 'camera_location' not in columns:
            try:
                cursor.execute("ALTER TABLE events ADD COLUMN camera_location TEXT")
            except Exception:
                pass

        self.conn.commit()

    def log_event(self, event_type, details, image_path=None,
                  camera_id=None, camera_name=None, camera_location=None):
        timestamp = datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO events (timestamp, event_type, details, image_path, camera_id, camera_name, camera_location) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, event_type, details, image_path, camera_id, camera_name, camera_location)
        )
        self.conn.commit()
        logger.info(f"Event logged: {event_type} - {details} (image={image_path}, camera={camera_id})")

    def get_recent_events(self, limit=100):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [{
            "id": r[0],
            "timestamp": r[1],
            "event_type": r[2],
            "details": r[3],
            "image_path": r[4] if len(r) > 4 else None,
            "camera_id": r[5] if len(r) > 5 else None,
            "camera_name": r[6] if len(r) > 6 else None,
            "camera_location": r[7] if len(r) > 7 else None
        } for r in rows]