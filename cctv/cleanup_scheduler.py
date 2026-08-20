import threading
import time
import logging
import schedule
from datetime import datetime, timedelta
from mysql_database import MySQLDatabase
import os
import glob

logger = logging.getLogger(__name__)

class CleanupScheduler:
    def __init__(self, database: MySQLDatabase):
        self.db = database
        self.running = False
        self.scheduler_thread = None
        
    def start(self):
        """Start the cleanup scheduler"""
        if self.running:
            logger.warning("Cleanup scheduler is already running")
            return
            
        self.running = True
        
        # Schedule cleanup tasks
        schedule.every().day.at("02:00").do(self.daily_cleanup)  # Daily at 2 AM
        schedule.every().hour.do(self.hourly_cleanup)  # Every hour
        schedule.every().sunday.at("03:00").do(self.weekly_cleanup)  # Weekly on Sunday at 3 AM
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Cleanup scheduler started")
    
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Cleanup scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def daily_cleanup(self):
        """Perform daily cleanup tasks"""
        logger.info("Starting daily cleanup tasks")
        
        try:
            # Clean up expired images
            images_cleaned = self.cleanup_expired_images()
            logger.info(f"Cleaned up {images_cleaned} expired images")
            
            # Clean up old logs (older than 90 days)
            logs_cleaned = self.cleanup_old_logs(days=90)
            logger.info(f"Cleaned up {logs_cleaned} old log entries")
            
            # Clean up temporary files
            temp_files_cleaned = self.cleanup_temp_files()
            logger.info(f"Cleaned up {temp_files_cleaned} temporary files")
            
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")
    
    def hourly_cleanup(self):
        """Perform hourly cleanup tasks"""
        try:
            # Check for subscription expirations
            self.check_subscription_expirations()
            
            # Clean up failed uploads
            self.cleanup_failed_uploads()
            
        except Exception as e:
            logger.error(f"Error in hourly cleanup: {e}")
    
    def weekly_cleanup(self):
        """Perform weekly cleanup tasks"""
        logger.info("Starting weekly cleanup tasks")
        
        try:
            # Clean up old videos (older than 60 days)
            videos_cleaned = self.cleanup_old_videos(days=60)
            logger.info(f"Cleaned up {videos_cleaned} old videos")
            
            # Optimize database
            self.optimize_database()
            
        except Exception as e:
            logger.error(f"Error in weekly cleanup: {e}")
    
    def cleanup_expired_images(self) -> int:
        """Clean up images older than 30 days"""
        try:
            images_cleaned = self.db.cleanup_expired_images()
            
            # Also clean up physical files
            expired_images = self.db.execute_query("""
                SELECT file_path, thumbnail_path 
                FROM captured_images 
                WHERE expires_at < NOW() AND is_deleted = TRUE
            """)
            
            files_deleted = 0
            for image in expired_images:
                try:
                    if image['file_path'] and os.path.exists(image['file_path']):
                        os.remove(image['file_path'])
                        files_deleted += 1
                    
                    if image['thumbnail_path'] and os.path.exists(image['thumbnail_path']):
                        os.remove(image['thumbnail_path'])
                        files_deleted += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to delete file {image['file_path']}: {e}")
            
            logger.info(f"Deleted {files_deleted} physical image files")
            return images_cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up expired images: {e}")
            return 0
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """Clean up system logs older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = self.db.execute_non_query(
                "DELETE FROM system_logs WHERE timestamp < %s",
                (cutoff_date,)
            )
            return result
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            return 0
    
    def cleanup_temp_files(self) -> int:
        """Clean up temporary files"""
        try:
            temp_patterns = [
                "uploads/temp/*.tmp",
                "uploads/temp/*.temp",
                "uploads/thumbnails/temp_*",
                "*.tmp"
            ]
            
            files_deleted = 0
            for pattern in temp_patterns:
                for file_path in glob.glob(pattern):
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
            return files_deleted
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return 0
    
    def cleanup_old_videos(self, days: int = 60) -> int:
        """Clean up videos older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get old videos
            old_videos = self.db.execute_query("""
                SELECT id, file_path, thumbnail_path 
                FROM video_recordings 
                WHERE start_time < %s AND is_deleted = FALSE
            """, (cutoff_date,))
            
            videos_deleted = 0
            files_deleted = 0
            
            for video in old_videos:
                try:
                    # Delete physical files
                    if video['file_path'] and os.path.exists(video['file_path']):
                        os.remove(video['file_path'])
                        files_deleted += 1
                    
                    if video['thumbnail_path'] and os.path.exists(video['thumbnail_path']):
                        os.remove(video['thumbnail_path'])
                        files_deleted += 1
                    
                    # Mark as deleted in database
                    self.db.execute_non_query(
                        "UPDATE video_recordings SET is_deleted = TRUE WHERE id = %s",
                        (video['id'],)
                    )
                    videos_deleted += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to delete video {video['file_path']}: {e}")
            
            logger.info(f"Deleted {videos_deleted} video records and {files_deleted} physical files")
            return videos_deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old videos: {e}")
            return 0
    
    def cleanup_failed_uploads(self):
        """Clean up failed upload files"""
        try:
            # Find files in upload directories that aren't in database
            upload_dirs = ["uploads/images", "uploads/videos", "uploads/thumbnails"]
            
            for upload_dir in upload_dirs:
                if not os.path.exists(upload_dir):
                    continue
                
                for file_path in glob.glob(os.path.join(upload_dir, "*")):
                    if os.path.isfile(file_path):
                        filename = os.path.basename(file_path)
                        
                        # Check if file exists in database
                        in_db = False
                        
                        if "images" in upload_dir:
                            result = self.db.execute_query(
                                "SELECT COUNT(*) as count FROM captured_images WHERE file_path LIKE %s",
                                (f"%{filename}",)
                            )
                            in_db = result[0]['count'] > 0
                        
                        elif "videos" in upload_dir:
                            result = self.db.execute_query(
                                "SELECT COUNT(*) as count FROM video_recordings WHERE file_path LIKE %s",
                                (f"%{filename}",)
                            )
                            in_db = result[0]['count'] > 0
                        
                        # If not in database and older than 1 hour, delete it
                        if not in_db:
                            file_age = time.time() - os.path.getctime(file_path)
                            if file_age > 3600:  # 1 hour
                                try:
                                    os.remove(file_path)
                                    logger.info(f"Deleted orphaned file: {file_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete orphaned file {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error cleaning up failed uploads: {e}")
    
    def check_subscription_expirations(self):
        """Check for subscription expirations and send notifications"""
        try:
            # Get subscriptions expiring in next 7 days
            expiring_soon = self.db.get_expiring_subscriptions(days=7)
            
            for subscription in expiring_soon:
                days_remaining = subscription['days_remaining']
                
                if days_remaining <= 0:
                    # Subscription expired
                    self.db.execute_non_query(
                        "UPDATE user_subscriptions SET status = 'expired' WHERE user_id = %s",
                        (subscription['id'],)
                    )
                    
                    self.db.log_system_action(
                        user_id=subscription['id'],
                        action='subscription_expired',
                        details=f"Subscription expired: {subscription['subscription_name']}"
                    )
                    
                    logger.warning(f"Subscription expired for user {subscription['username']}")
                
                elif days_remaining <= 3:
                    # Expiring soon - send notification
                    self.db.log_system_action(
                        user_id=subscription['id'],
                        action='subscription_expiring_soon',
                        details=f"Subscription expires in {days_remaining} days: {subscription['subscription_name']}"
                    )
                    
                    logger.info(f"Subscription expiring soon for user {subscription['username']}: {days_remaining} days")
            
        except Exception as e:
            logger.error(f"Error checking subscription expirations: {e}")
    
    def optimize_database(self):
        """Optimize database tables"""
        try:
            tables = ['users', 'detection_events', 'captured_images', 'video_recordings', 'system_logs']
            
            for table in tables:
                try:
                    self.db.execute_non_query(f"OPTIMIZE TABLE {table}")
                    logger.info(f"Optimized table: {table}")
                except Exception as e:
                    logger.warning(f"Failed to optimize table {table}: {e}")
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
    
    def get_cleanup_stats(self) -> dict:
        """Get cleanup statistics"""
        try:
            # Get storage usage
            total_images = self.db.execute_query("SELECT COUNT(*) as count FROM captured_images WHERE is_deleted = FALSE")[0]['count']
            total_videos = self.db.execute_query("SELECT COUNT(*) as count FROM video_recordings WHERE is_deleted = FALSE")[0]['count']
            total_events = self.db.execute_query("SELECT COUNT(*) as count FROM detection_events")[0]['count']
            
            # Get expiring images count
            expiring_images = self.db.execute_query("""
                SELECT COUNT(*) as count 
                FROM captured_images 
                WHERE expires_at BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
                AND is_deleted = FALSE
            """)[0]['count']
            
            # Get storage size (approximate)
            storage_stats = self.get_storage_stats()
            
            return {
                'total_images': total_images,
                'total_videos': total_videos,
                'total_events': total_events,
                'expiring_images': expiring_images,
                'storage_stats': storage_stats,
                'last_cleanup': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup stats: {e}")
            return {}
    
    def get_storage_stats(self) -> dict:
        """Get storage usage statistics"""
        try:
            dirs = {
                'images': 'uploads/images',
                'videos': 'uploads/videos',
                'thumbnails': 'uploads/thumbnails'
            }
            
            stats = {}
            total_size = 0
            
            for name, path in dirs.items():
                if os.path.exists(path):
                    size = 0
                    count = 0
                    
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                size += os.path.getsize(file_path)
                                count += 1
                    
                    stats[name] = {
                        'size_bytes': size,
                        'size_mb': round(size / (1024 * 1024), 2),
                        'file_count': count
                    }
                    total_size += size
                else:
                    stats[name] = {
                        'size_bytes': 0,
                        'size_mb': 0,
                        'file_count': 0
                    }
            
            stats['total'] = {
                'size_bytes': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'size_gb': round(total_size / (1024 * 1024 * 1024), 2)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    def run_manual_cleanup(self, cleanup_type: str = "all") -> dict:
        """Run manual cleanup"""
        results = {
            'images_cleaned': 0,
            'videos_cleaned': 0,
            'logs_cleaned': 0,
            'temp_files_cleaned': 0
        }
        
        try:
            if cleanup_type in ["all", "images"]:
                results['images_cleaned'] = self.cleanup_expired_images()
            
            if cleanup_type in ["all", "videos"]:
                results['videos_cleaned'] = self.cleanup_old_videos()
            
            if cleanup_type in ["all", "logs"]:
                results['logs_cleaned'] = self.cleanup_old_logs()
            
            if cleanup_type in ["all", "temp"]:
                results['temp_files_cleaned'] = self.cleanup_temp_files()
            
            logger.info(f"Manual cleanup completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}")
        
        return results
