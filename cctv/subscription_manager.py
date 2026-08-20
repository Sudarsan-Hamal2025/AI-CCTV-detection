import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from mysql_database import MySQLDatabase
import json

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, database: MySQLDatabase):
        self.db = database
    
    def get_available_subscriptions(self) -> List[Dict]:
        """Get all available subscription plans"""
        try:
            return self.db.get_subscriptions()
        except Exception as e:
            logger.error(f"Error getting available subscriptions: {e}")
            return []
    
    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Get current subscription for a user"""
        try:
            return self.db.get_user_subscription(user_id)
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None
    
    def create_subscription(self, user_id: int, subscription_plan_id: int, 
                          duration_days: int = 30, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a new subscription for a user"""
        try:
            if start_date is None:
                start_date = datetime.now().date()
            
            end_date = start_date + timedelta(days=duration_days)
            
            # Check if user already has active subscription
            existing = self.db.get_user_subscription(user_id)
            if existing and existing['status'] == 'active':
                return {
                    'success': False,
                    'message': 'User already has an active subscription'
                }
            
            # Create new subscription
            subscription_id = self.db.create_user_subscription(
                user_id=user_id,
                subscription_id=subscription_plan_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Log the action
            self.db.log_system_action(
                user_id=user_id,
                action='subscription_created',
                details=f"Created subscription ID: {subscription_id}, Plan ID: {subscription_plan_id}"
            )
            
            return {
                'success': True,
                'subscription_id': subscription_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'message': 'Subscription created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return {
                'success': False,
                'message': 'Failed to create subscription'
            }
    
    def renew_subscription(self, user_id: int, duration_days: int = 30) -> Dict[str, Any]:
        """Renew existing subscription"""
        try:
            current = self.db.get_user_subscription(user_id)
            
            if not current:
                return {
                    'success': False,
                    'message': 'No existing subscription found'
                }
            
            # Calculate new end date
            current_end = datetime.strptime(current['end_date'], '%Y-%m-%d').date()
            new_end_date = current_end + timedelta(days=duration_days)
            
            # Update subscription
            success = self.db.execute_non_query(
                "UPDATE user_subscriptions SET end_date = %s, status = 'active' WHERE user_id = %s AND status = 'active'",
                (new_end_date, user_id)
            )
            
            if success:
                self.db.log_system_action(
                    user_id=user_id,
                    action='subscription_renewed',
                    details=f"Subscription renewed until {new_end_date}"
                )
                
                return {
                    'success': True,
                    'new_end_date': new_end_date.isoformat(),
                    'message': 'Subscription renewed successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to renew subscription'
                }
                
        except Exception as e:
            logger.error(f"Error renewing subscription: {e}")
            return {
                'success': False,
                'message': 'Failed to renew subscription'
            }
    
    def cancel_subscription(self, user_id: int, reason: str = None) -> Dict[str, Any]:
        """Cancel user subscription"""
        try:
            success = self.db.cancel_subscription(user_id)
            
            if success:
                self.db.log_system_action(
                    user_id=user_id,
                    action='subscription_cancelled',
                    details=f"Subscription cancelled. Reason: {reason or 'Not specified'}"
                )
                
                return {
                    'success': True,
                    'message': 'Subscription cancelled successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to cancel subscription'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return {
                'success': False,
                'message': 'Failed to cancel subscription'
            }
    
    def upgrade_subscription(self, user_id: int, new_plan_id: int) -> Dict[str, Any]:
        """Upgrade user to a different subscription plan"""
        try:
            current = self.db.get_user_subscription(user_id)
            
            if not current:
                return {
                    'success': False,
                    'message': 'No existing subscription found'
                }
            
            # Get new plan details
            new_plan = self.db.execute_query(
                "SELECT * FROM subscriptions WHERE id = %s AND is_active = TRUE",
                (new_plan_id,)
            )
            
            if not new_plan:
                return {
                    'success': False,
                    'message': 'New subscription plan not found'
                }
            
            new_plan = new_plan[0]
            
            # Calculate prorated amount and new end date
            current_end = datetime.strptime(current['end_date'], '%Y-%m-%d').date()
            days_remaining = (current_end - datetime.now().date()).days
            
            if days_remaining <= 0:
                return {
                    'success': False,
                    'message': 'Current subscription has expired'
                }
            
            # Create new subscription with same end date
            subscription_id = self.db.create_user_subscription(
                user_id=user_id,
                subscription_id=new_plan_id,
                start_date=datetime.now().date(),
                end_date=current_end
            )
            
            # Cancel old subscription
            self.db.cancel_subscription(user_id)
            
            self.db.log_system_action(
                user_id=user_id,
                action='subscription_upgraded',
                details=f"Upgraded to plan {new_plan['name']} (ID: {new_plan_id})"
            )
            
            return {
                'success': True,
                'subscription_id': subscription_id,
                'new_plan': new_plan['name'],
                'message': 'Subscription upgraded successfully'
            }
            
        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            return {
                'success': False,
                'message': 'Failed to upgrade subscription'
            }
    
    def get_subscription_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get usage statistics for user's subscription"""
        try:
            subscription = self.db.get_user_subscription(user_id)
            
            if not subscription:
                return {
                    'has_subscription': False,
                    'message': 'No active subscription'
                }
            
            # Get subscription features
            features = json.loads(subscription['features']) if isinstance(subscription['features'], str) else subscription['features']
            
            # Get current usage
            stats = {
                'has_subscription': True,
                'subscription_name': subscription['subscription_name'],
                'end_date': subscription['end_date'],
                'days_remaining': subscription.get('days_remaining', 0),
                'features': features,
                'usage': {}
            }
            
            # Get storage usage
            images = self.db.get_user_images(user_id, limit=1000)
            videos = self.db.get_user_videos(user_id, limit=1000)
            
            total_storage_mb = sum(img.get('file_size', 0) for img in images) / (1024 * 1024)
            total_storage_mb += sum(vid.get('file_size', 0) for vid in videos) / (1024 * 1024)
            
            stats['usage'] = {
                'images_count': len(images),
                'videos_count': len(videos),
                'storage_used_mb': round(total_storage_mb, 2),
                'storage_limit_mb': features.get('max_storage_gb', 10) * 1024,
                'cameras_used': 1,  # This could be dynamic
                'cameras_limit': features.get('max_cameras', 1)
            }
            
            # Calculate usage percentages
            if stats['usage']['storage_limit_mb'] > 0:
                stats['usage']['storage_percentage'] = round(
                    (stats['usage']['storage_used_mb'] / stats['usage']['storage_limit_mb']) * 100, 2
                )
            else:
                stats['usage']['storage_percentage'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting subscription usage stats: {e}")
            return {
                'has_subscription': False,
                'message': 'Error retrieving subscription information'
            }
    
    def check_subscription_limits(self, user_id: int, action: str, **kwargs) -> Dict[str, Any]:
        """Check if user can perform action based on subscription limits"""
        try:
            stats = self.get_subscription_usage_stats(user_id)
            
            if not stats['has_subscription']:
                return {
                    'allowed': False,
                    'reason': 'No active subscription',
                    'upgrade_required': True
                }
            
            features = stats['features']
            usage = stats['usage']
            
            # Check different action types
            if action == 'upload_image':
                storage_limit = features.get('max_storage_gb', 10) * 1024
                if usage['storage_used_mb'] >= storage_limit:
                    return {
                        'allowed': False,
                        'reason': 'Storage limit exceeded',
                        'upgrade_required': True
                    }
            
            elif action == 'start_recording':
                if not features.get('video_recording', False):
                    return {
                        'allowed': False,
                        'reason': 'Video recording not included in current plan',
                        'upgrade_required': True
                    }
            
            elif action == 'add_camera':
                cameras_limit = features.get('max_cameras', 1)
                if usage['cameras_used'] >= cameras_limit:
                    return {
                        'allowed': False,
                        'reason': 'Camera limit exceeded',
                        'upgrade_required': True
                    }
            
            elif action == 'advanced_detection':
                detection_types = features.get('detection_types', ['person'])
                requested_type = kwargs.get('detection_type', 'person')
                
                if requested_type not in detection_types:
                    return {
                        'allowed': False,
                        'reason': f'Detection type "{requested_type}" not included in current plan',
                        'upgrade_required': True
                    }
            
            return {
                'allowed': True,
                'reason': 'Action allowed'
            }
            
        except Exception as e:
            logger.error(f"Error checking subscription limits: {e}")
            return {
                'allowed': False,
                'reason': 'Error checking subscription limits'
            }
    
    def get_expiring_subscriptions(self, days: int = 7) -> List[Dict]:
        """Get subscriptions expiring within specified days"""
        try:
            return self.db.get_expiring_subscriptions(days)
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []
    
    def get_subscription_revenue(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get subscription revenue statistics (admin only)"""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.now()
            
            # Get revenue data
            revenue_data = self.db.execute_query("""
                SELECT s.name as subscription_name, s.price, COUNT(*) as count,
                       SUM(s.price) as total_revenue
                FROM user_subscriptions us
                JOIN subscriptions s ON us.subscription_id = s.id
                WHERE us.start_date BETWEEN %s AND %s
                GROUP BY s.id, s.name, s.price
                ORDER BY total_revenue DESC
            """, (start_date.date(), end_date.date()))
            
            total_revenue = sum(row['total_revenue'] for row in revenue_data)
            total_subscriptions = sum(row['count'] for row in revenue_data)
            
            return {
                'period': {
                    'start_date': start_date.date().isoformat(),
                    'end_date': end_date.date().isoformat()
                },
                'total_revenue': total_revenue,
                'total_subscriptions': total_subscriptions,
                'by_plan': revenue_data
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription revenue: {e}")
            return {}
    
    def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get comprehensive subscription analytics"""
        try:
            # Get subscription distribution
            distribution = self.db.execute_query("""
                SELECT s.name, COUNT(*) as active_count
                FROM user_subscriptions us
                JOIN subscriptions s ON us.subscription_id = s.id
                WHERE us.status = 'active'
                GROUP BY s.id, s.name
                ORDER BY active_count DESC
            """)
            
            # Get churn rate (subscriptions cancelled in last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            cancelled = self.db.execute_query("""
                SELECT COUNT(*) as cancelled_count
                FROM user_subscriptions
                WHERE status = 'cancelled' 
                AND updated_at >= %s
            """, (thirty_days_ago,))
            
            # Get new subscriptions in last 30 days
            new_subscriptions = self.db.execute_query("""
                SELECT COUNT(*) as new_count
                FROM user_subscriptions
                WHERE start_date >= %s
            """, (thirty_days_ago.date(),))
            
            # Get expiring soon
            expiring_soon = self.get_expiring_subscriptions(7)
            
            return {
                'distribution': distribution,
                'churn_last_30_days': cancelled[0]['cancelled_count'] if cancelled else 0,
                'new_subscriptions_last_30_days': new_subscriptions[0]['new_count'] if new_subscriptions else 0,
                'expiring_next_7_days': len(expiring_soon),
                'total_active_subscriptions': sum(row['active_count'] for row in distribution)
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription analytics: {e}")
            return {}
    
    def send_expiration_notifications(self) -> int:
        """Send notifications for expiring subscriptions"""
        try:
            expiring_soon = self.get_expiring_subscriptions(7)
            notifications_sent = 0
            
            for subscription in expiring_soon:
                days_remaining = subscription['days_remaining']
                
                # Log notification (in real implementation, this would send email/SMS)
                self.db.log_system_action(
                    user_id=subscription['id'],
                    action='expiration_notification_sent',
                    details=f"Subscription expires in {days_remaining} days: {subscription['subscription_name']}"
                )
                
                notifications_sent += 1
                
                logger.info(f"Sent expiration notification to user {subscription['username']}: {days_remaining} days remaining")
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Error sending expiration notifications: {e}")
            return 0
    
    def apply_subscription_features(self, user_id: int) -> Dict[str, Any]:
        """Apply subscription features to user account"""
        try:
            subscription = self.db.get_user_subscription(user_id)
            
            if not subscription:
                return {
                    'success': False,
                    'message': 'No active subscription'
                }
            
            features = json.loads(subscription['features']) if isinstance(subscription['features'], str) else subscription['features']
            
            # Apply features to user account
            # This could include enabling/disabling features based on subscription
            
            return {
                'success': True,
                'features': features,
                'message': 'Subscription features applied'
            }
            
        except Exception as e:
            logger.error(f"Error applying subscription features: {e}")
            return {
                'success': False,
                'message': 'Failed to apply subscription features'
            }
