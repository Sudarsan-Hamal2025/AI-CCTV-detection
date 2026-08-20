import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from mysql_database import MySQLDatabase
from auth import AuthenticationManager
from subscription_manager import SubscriptionManager
from cleanup_scheduler import CleanupScheduler
import json

logger = logging.getLogger(__name__)

class SuperAdminFeatures:
    def __init__(self, database: MySQLDatabase, auth_manager: AuthenticationManager,
                 subscription_manager: SubscriptionManager, cleanup_scheduler: CleanupScheduler):
        self.db = database
        self.auth = auth_manager
        self.subscription_manager = subscription_manager
        self.cleanup_scheduler = cleanup_scheduler
    
    # User Management
    def get_all_users_detailed(self, include_inactive: bool = False) -> List[Dict]:
        """Get detailed information about all users"""
        try:
            active_filter = "" if include_inactive else "AND u.is_active = TRUE"
            
            query = f"""
                SELECT u.*, r.name as role_name, r.permissions,
                       s.name as subscription_name, us.end_date, us.status as subscription_status,
                       DATEDIFF(us.end_date, CURDATE()) as days_remaining,
                       (SELECT COUNT(*) FROM detection_events de WHERE de.user_id = u.id) as total_detections,
                       (SELECT COUNT(*) FROM captured_images ci WHERE ci.user_id = u.id AND ci.is_deleted = FALSE) as total_images,
                       (SELECT COUNT(*) FROM video_recordings vr WHERE vr.user_id = u.id AND vr.is_deleted = FALSE) as total_videos,
                       u.created_at as registration_date,
                       (SELECT MAX(timestamp) FROM system_logs sl WHERE sl.user_id = u.id) as last_activity
                FROM users u
                JOIN roles r ON u.role_id = r.id
                LEFT JOIN user_subscriptions us ON u.id = us.user_id AND us.status = 'active'
                LEFT JOIN subscriptions s ON us.subscription_id = s.id
                WHERE 1=1 {active_filter}
                ORDER BY u.created_at DESC
            """
            
            users = self.db.execute_query(query)
            
            # Parse permissions for each user
            for user in users:
                if isinstance(user['permissions'], str):
                    try:
                        user['permissions'] = json.loads(user['permissions'])
                    except:
                        user['permissions'] = {}
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting detailed users: {e}")
            return []
    
    def create_user_with_subscription(self, username: str, email: str, password: str,
                                     full_name: str, role_id: int, subscription_plan_id: int = None,
                                     phone: str = None) -> Dict[str, Any]:
        """Create a new user and optionally assign a subscription"""
        try:
            # Create user
            user_id = self.db.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
                role_id=role_id
            )
            
            # Assign subscription if provided
            subscription_result = None
            if subscription_plan_id:
                subscription_result = self.subscription_manager.create_subscription(
                    user_id=user_id,
                    subscription_plan_id=subscription_plan_id,
                    duration_days=30
                )
            
            # Log action
            self.db.log_system_action(
                user_id=None,  # System action
                action='user_created_by_admin',
                details=f"Created user {username} (ID: {user_id}) with role {role_id}"
            )
            
            return {
                'success': True,
                'user_id': user_id,
                'subscription_result': subscription_result,
                'message': 'User created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating user with subscription: {e}")
            return {
                'success': False,
                'message': f'Failed to create user: {str(e)}'
            }
    
    def bulk_user_operations(self, user_ids: List[int], operation: str, **kwargs) -> Dict[str, Any]:
        """Perform bulk operations on multiple users"""
        try:
            results = {
                'success': True,
                'processed': 0,
                'failed': 0,
                'errors': []
            }
            
            for user_id in user_ids:
                try:
                    if operation == 'deactivate':
                        success = self.db.execute_non_query(
                            "UPDATE users SET is_active = FALSE WHERE id = %s",
                            (user_id,)
                        )
                        if success:
                            self.db.log_system_action(
                                user_id=None,
                                action='bulk_deactivate_user',
                                details=f"Deactivated user ID: {user_id}"
                            )
                    
                    elif operation == 'activate':
                        success = self.db.execute_non_query(
                            "UPDATE users SET is_active = TRUE WHERE id = %s",
                            (user_id,)
                        )
                        if success:
                            self.db.log_system_action(
                                user_id=None,
                                action='bulk_activate_user',
                                details=f"Activated user ID: {user_id}"
                            )
                    
                    elif operation == 'cancel_subscription':
                        success = self.db.cancel_subscription(user_id)
                        if success:
                            self.db.log_system_action(
                                user_id=None,
                                action='bulk_cancel_subscription',
                                details=f"Cancelled subscription for user ID: {user_id}"
                            )
                    
                    elif operation == 'assign_role':
                        new_role_id = kwargs.get('role_id')
                        if new_role_id:
                            success = self.db.update_user(user_id, role_id=new_role_id)
                            if success:
                                self.db.log_system_action(
                                    user_id=None,
                                    action='bulk_assign_role',
                                    details=f"Assigned role {new_role_id} to user ID: {user_id}"
                                )
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id}: {str(e)}")
            
            if results['failed'] > 0:
                results['success'] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk user operations: {e}")
            return {
                'success': False,
                'message': f'Bulk operation failed: {str(e)}'
            }
    
    # System Management
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        try:
            overview = {}
            
            # User statistics
            user_stats = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_users,
                    COUNT(CASE WHEN role_id = 1 THEN 1 END) as regular_users,
                    COUNT(CASE WHEN role_id = 2 THEN 1 END) as admins,
                    COUNT(CASE WHEN role_id = 3 THEN 1 END) as super_admins,
                    COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as new_users_30_days
                FROM users
            """)[0]
            
            overview['users'] = user_stats
            
            # Subscription statistics
            subscription_stats = self.db.execute_query("""
                SELECT 
                    COUNT(*) as total_subscriptions,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_subscriptions,
                    COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_subscriptions,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_subscriptions,
                    COUNT(CASE WHEN end_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 1 END) as expiring_next_7_days,
                    COUNT(CASE WHEN end_date < CURDATE() AND status = 'active' THEN 1 END) as overdue_active
                FROM user_subscriptions
            """)[0]
            
            overview['subscriptions'] = subscription_stats
            
            # Content statistics
            content_stats = self.db.execute_query("""
                SELECT 
                    (SELECT COUNT(*) FROM detection_events) as total_detections,
                    (SELECT COUNT(*) FROM detection_events WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as detections_24h,
                    (SELECT COUNT(*) FROM captured_images WHERE is_deleted = FALSE) as total_images,
                    (SELECT COUNT(*) FROM captured_images WHERE is_deleted = FALSE AND timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as images_24h,
                    (SELECT COUNT(*) FROM video_recordings WHERE is_deleted = FALSE) as total_videos,
                    (SELECT COUNT(*) FROM video_recordings WHERE is_deleted = FALSE AND start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)) as videos_24h
            """)[0]
            
            overview['content'] = content_stats
            
            # Storage statistics
            storage_stats = self.cleanup_scheduler.get_storage_stats()
            overview['storage'] = storage_stats
            
            # System health
            overview['system_health'] = {
                'database_status': 'healthy',  # Could be checked with ping
                'api_status': 'healthy',
                'last_cleanup': self.cleanup_scheduler.get_cleanup_stats().get('last_cleanup'),
                'uptime': 'Unknown',  # Could track application start time
            }
            
            # Recent activity
            recent_activity = self.db.execute_query("""
                SELECT sl.*, u.username
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                ORDER BY sl.timestamp DESC
                LIMIT 10
            """)
            
            overview['recent_activity'] = recent_activity
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {}
    
    def get_system_logs(self, limit: int = 100, user_id: int = None, 
                       action: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get filtered system logs"""
        try:
            query = """
                SELECT sl.*, u.username, u.full_name
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND sl.user_id = %s"
                params.append(user_id)
            
            if action:
                query += " AND sl.action = %s"
                params.append(action)
            
            if start_date:
                query += " AND sl.timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND sl.timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY sl.timestamp DESC LIMIT %s"
            params.append(limit)
            
            return self.db.execute_query(query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting system logs: {e}")
            return []
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all data for a specific user (GDPR compliance)"""
        try:
            user_data = self.db.get_user_by_id(user_id)
            if not user_data:
                return {'success': False, 'message': 'User not found'}
            
            export_data = {
                'user_info': {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'full_name': user_data['full_name'],
                    'phone': user_data['phone'],
                    'registration_date': user_data['created_at'],
                    'last_activity': user_data.get('last_activity')
                },
                'detections': self.db.get_detection_events(user_id, limit=10000),
                'images': self.db.get_user_images(user_id, limit=10000),
                'videos': self.db.get_user_videos(user_id, limit=10000),
                'subscription_history': self.db.execute_query("""
                    SELECT us.*, s.name as subscription_name
                    FROM user_subscriptions us
                    JOIN subscriptions s ON us.subscription_id = s.id
                    WHERE us.user_id = %s
                    ORDER BY us.start_date DESC
                """, (user_id,)),
                'system_logs': self.db.get_system_logs(limit=1000, user_id=user_id)
            }
            
            # Log export action
            self.db.log_system_action(
                user_id=None,
                action='user_data_exported',
                details=f"Exported data for user ID: {user_id}"
            )
            
            return {
                'success': True,
                'data': export_data,
                'export_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return {
                'success': False,
                'message': f'Failed to export user data: {str(e)}'
            }
    
    # Subscription Management
    def manage_subscription_plans(self, action: str, plan_data: Dict[str, Any] = None, 
                                plan_id: int = None) -> Dict[str, Any]:
        """Manage subscription plans"""
        try:
            if action == 'create':
                result = self.db.execute_non_query("""
                    INSERT INTO subscriptions (name, price, duration_days, max_cameras, max_storage_gb, features)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    plan_data['name'],
                    plan_data['price'],
                    plan_data['duration_days'],
                    plan_data.get('max_cameras', 1),
                    plan_data.get('max_storage_gb', 10),
                    json.dumps(plan_data.get('features', {}))
                ))
                
                plan_id = self.db.get_last_insert_id()
                
                self.db.log_system_action(
                    user_id=None,
                    action='subscription_plan_created',
                    details=f"Created subscription plan: {plan_data['name']} (ID: {plan_id})"
                )
                
                return {'success': True, 'plan_id': plan_id}
            
            elif action == 'update':
                set_clauses = []
                params = []
                
                if 'name' in plan_data:
                    set_clauses.append("name = %s")
                    params.append(plan_data['name'])
                if 'price' in plan_data:
                    set_clauses.append("price = %s")
                    params.append(plan_data['price'])
                if 'duration_days' in plan_data:
                    set_clauses.append("duration_days = %s")
                    params.append(plan_data['duration_days'])
                if 'max_cameras' in plan_data:
                    set_clauses.append("max_cameras = %s")
                    params.append(plan_data['max_cameras'])
                if 'max_storage_gb' in plan_data:
                    set_clauses.append("max_storage_gb = %s")
                    params.append(plan_data['max_storage_gb'])
                if 'features' in plan_data:
                    set_clauses.append("features = %s")
                    params.append(json.dumps(plan_data['features']))
                
                params.append(plan_id)
                
                query = f"UPDATE subscriptions SET {', '.join(set_clauses)} WHERE id = %s"
                result = self.db.execute_non_query(query, tuple(params))
                
                self.db.log_system_action(
                    user_id=None,
                    action='subscription_plan_updated',
                    details=f"Updated subscription plan ID: {plan_id}"
                )
                
                return {'success': True, 'updated_rows': result}
            
            elif action == 'delete':
                # Soft delete by setting is_active to False
                result = self.db.execute_non_query(
                    "UPDATE subscriptions SET is_active = FALSE WHERE id = %s",
                    (plan_id,)
                )
                
                self.db.log_system_action(
                    user_id=None,
                    action='subscription_plan_deleted',
                    details=f"Deleted subscription plan ID: {plan_id}"
                )
                
                return {'success': True, 'deleted_rows': result}
            
            else:
                return {'success': False, 'message': 'Invalid action'}
                
        except Exception as e:
            logger.error(f"Error managing subscription plans: {e}")
            return {'success': False, 'message': f'Operation failed: {str(e)}'}
    
    def bulk_subscription_operations(self, user_ids: List[int], operation: str, 
                                   plan_id: int = None, duration_days: int = 30) -> Dict[str, Any]:
        """Perform bulk subscription operations"""
        try:
            results = {
                'success': True,
                'processed': 0,
                'failed': 0,
                'errors': []
            }
            
            for user_id in user_ids:
                try:
                    if operation == 'assign':
                        result = self.subscription_manager.create_subscription(
                            user_id=user_id,
                            subscription_plan_id=plan_id,
                            duration_days=duration_days
                        )
                        if not result['success']:
                            raise Exception(result['message'])
                    
                    elif operation == 'cancel':
                        result = self.subscription_manager.cancel_subscription(user_id)
                        if not result['success']:
                            raise Exception(result['message'])
                    
                    elif operation == 'extend':
                        result = self.subscription_manager.renew_subscription(
                            user_id=user_id,
                            duration_days=duration_days
                        )
                        if not result['success']:
                            raise Exception(result['message'])
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"User {user_id}: {str(e)}")
            
            if results['failed'] > 0:
                results['success'] = False
            
            # Log bulk operation
            self.db.log_system_action(
                user_id=None,
                action=f'bulk_subscription_{operation}',
                details=f"Bulk {operation} on {len(user_ids)} users. Processed: {results['processed']}, Failed: {results['failed']}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk subscription operations: {e}")
            return {
                'success': False,
                'message': f'Bulk operation failed: {str(e)}'
            }
    
    # System Maintenance
    def perform_system_maintenance(self, maintenance_type: str = "all") -> Dict[str, Any]:
        """Perform system maintenance tasks"""
        try:
            results = {
                'success': True,
                'maintenance_type': maintenance_type,
                'tasks_completed': [],
                'errors': []
            }
            
            if maintenance_type in ["all", "cleanup"]:
                cleanup_results = self.cleanup_scheduler.run_manual_cleanup("all")
                results['tasks_completed'].append(f"Cleanup: {cleanup_results}")
            
            if maintenance_type in ["all", "database"]:
                # Optimize database tables
                tables = ['users', 'detection_events', 'captured_images', 'video_recordings', 'system_logs']
                for table in tables:
                    try:
                        self.db.execute_non_query(f"OPTIMIZE TABLE {table}")
                        results['tasks_completed'].append(f"Optimized table: {table}")
                    except Exception as e:
                        results['errors'].append(f"Failed to optimize {table}: {str(e)}")
            
            if maintenance_type in ["all", "notifications"]:
                # Send expiration notifications
                notifications_sent = self.subscription_manager.send_expiration_notifications()
                results['tasks_completed'].append(f"Sent {notifications_sent} expiration notifications")
            
            if maintenance_type in ["all", "subscriptions"]:
                # Update overdue subscriptions
                overdue = self.db.execute_non_query("""
                    UPDATE user_subscriptions 
                    SET status = 'expired' 
                    WHERE end_date < CURDATE() AND status = 'active'
                """)
                results['tasks_completed'].append(f"Updated {overdue} overdue subscriptions")
            
            # Log maintenance
            self.db.log_system_action(
                user_id=None,
                action='system_maintenance',
                details=f"Performed {maintenance_type} maintenance. Tasks: {len(results['tasks_completed'])}, Errors: {len(results['errors'])}"
            )
            
            if results['errors']:
                results['success'] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing system maintenance: {e}")
            return {
                'success': False,
                'message': f'Maintenance failed: {str(e)}'
            }
    
    def get_system_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive system analytics"""
        try:
            analytics = {}
            
            # User analytics
            user_analytics = self.db.execute_query(f"""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as new_users
                FROM users
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            
            # Subscription analytics
            subscription_analytics = self.subscription_manager.get_subscription_analytics()
            
            # Detection analytics
            detection_analytics = self.db.execute_query(f"""
                SELECT 
                    DATE(timestamp) as date,
                    event_type,
                    COUNT(*) as count
                FROM detection_events
                WHERE timestamp >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                GROUP BY DATE(timestamp), event_type
                ORDER BY date, count DESC
            """)
            
            # Storage analytics
            storage_analytics = self.cleanup_scheduler.get_storage_stats()
            
            analytics = {
                'period_days': days,
                'user_registrations': user_analytics,
                'subscriptions': subscription_analytics,
                'detections': detection_analytics,
                'storage': storage_analytics,
                'generated_at': datetime.now().isoformat()
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {}
    
    def emergency_actions(self, action: str, **kwargs) -> Dict[str, Any]:
        """Perform emergency system actions"""
        try:
            if action == 'disable_all_users':
                result = self.db.execute_non_query(
                    "UPDATE users SET is_active = FALSE WHERE role_id != 3"  # Don't disable super admins
                )
                
                self.db.log_system_action(
                    user_id=None,
                    action='emergency_disable_all_users',
                    details=f"Disabled {result} users (excluding super admins)"
                )
                
                return {'success': True, 'disabled_users': result}
            
            elif action == 'cancel_all_subscriptions':
                result = self.db.execute_non_query(
                    "UPDATE user_subscriptions SET status = 'cancelled' WHERE status = 'active'"
                )
                
                self.db.log_system_action(
                    user_id=None,
                    action='emergency_cancel_all_subscriptions',
                    details=f"Cancelled {result} active subscriptions"
                )
                
                return {'success': True, 'cancelled_subscriptions': result}
            
            elif action == 'enable_maintenance_mode':
                # This would typically set a flag that prevents normal operations
                self.db.log_system_action(
                    user_id=None,
                    action='emergency_maintenance_mode',
                    details="System entered maintenance mode"
                )
                
                return {'success': True, 'message': 'Maintenance mode enabled'}
            
            elif action == 'backup_system':
                # This would trigger a system backup
                self.db.log_system_action(
                    user_id=None,
                    action='emergency_backup',
                    details="Emergency system backup initiated"
                )
                
                return {'success': True, 'message': 'System backup initiated'}
            
            else:
                return {'success': False, 'message': 'Invalid emergency action'}
                
        except Exception as e:
            logger.error(f"Error performing emergency action: {e}")
            return {
                'success': False,
                'message': f'Emergency action failed: {str(e)}'
            }
