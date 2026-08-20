import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from mysql_database import MySQLDatabase

logger = logging.getLogger(__name__)

class AuthenticationManager:
    def __init__(self, database: MySQLDatabase, secret_key: str = None):
        self.db = database
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_expiry_hours = 24
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == hashed_password
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role_name'],
            'permissions': user_data['permissions'],
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        try:
            user = self.db.authenticate_user(username, password)
            if user:
                # Log successful login
                self.db.log_system_action(
                    user_id=user['id'],
                    action='login',
                    details='Successful login'
                )
                return user
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def login_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Login user and return token with user data"""
        user = self.authenticate_user(username, password)
        if user:
            token = self.generate_token(user)
            return {
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'role_name': user['role_name'],
                    'permissions': user['permissions'] if isinstance(user['permissions'], dict) else eval(user['permissions']),
                    'subscription_name': user.get('subscription_name'),
                    'days_remaining': user.get('days_remaining')
                }
            }
        else:
            return {
                'success': False,
                'message': 'Invalid username or password'
            }
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current user from token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        try:
            user = self.db.get_user_by_id(payload['user_id'])
            if user:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'role_name': user['role_name'],
                    'permissions': user['permissions'] if isinstance(user['permissions'], dict) else eval(user['permissions']),
                    'subscription_name': user.get('subscription_name'),
                    'days_remaining': user.get('days_remaining')
                }
            return None
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None
    
    def check_permission(self, user_permissions: Dict[str, bool], required_permission: str) -> bool:
        """Check if user has required permission"""
        return user_permissions.get(required_permission, False)
    
    def require_role(self, user_role: str, required_roles: list) -> bool:
        """Check if user has required role"""
        return user_role in required_roles
    
    def logout_user(self, user_id: int) -> bool:
        """Logout user (log the action)"""
        try:
            self.db.log_system_action(
                user_id=user_id,
                action='logout',
                details='User logged out'
            )
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password"""
        try:
            # Get current user data
            user = self.db.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'message': 'User not found'}
            
            # Verify old password
            if not self.verify_password(old_password, user['password_hash']):
                return {'success': False, 'message': 'Current password is incorrect'}
            
            # Update password
            new_password_hash = self.hash_password(new_password)
            success = self.db.update_user(user_id, password_hash=new_password_hash)
            
            if success:
                self.db.log_system_action(
                    user_id=user_id,
                    action='password_change',
                    details='Password changed successfully'
                )
                return {'success': True, 'message': 'Password changed successfully'}
            else:
                return {'success': False, 'message': 'Failed to update password'}
        
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return {'success': False, 'message': 'An error occurred while changing password'}
    
    def reset_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """Reset user password (admin function)"""
        try:
            new_password_hash = self.hash_password(new_password)
            success = self.db.update_user(user_id, password_hash=new_password_hash)
            
            if success:
                self.db.log_system_action(
                    user_id=user_id,
                    action='password_reset',
                    details='Password was reset by administrator'
                )
                return {'success': True, 'message': 'Password reset successfully'}
            else:
                return {'success': False, 'message': 'Failed to reset password'}
        
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return {'success': False, 'message': 'An error occurred while resetting password'}
    
    def create_user_session(self, user_id: int, session_data: Dict[str, Any]) -> str:
        """Create user session (optional: for session-based tracking)"""
        session_token = secrets.token_urlsafe(32)
        try:
            # This could be extended to store sessions in database
            self.db.log_system_action(
                user_id=user_id,
                action='session_created',
                details=f'Session created: {session_token[:8]}...'
            )
            return session_token
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return session_token
    
    def is_subscription_active(self, user_data: Dict[str, Any]) -> bool:
        """Check if user subscription is active"""
        days_remaining = user_data.get('days_remaining')
        if days_remaining is None:
            return False  # No subscription
        return days_remaining > 0
    
    def get_user_from_request(self, request_headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract user from request headers"""
        auth_header = request_headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        return self.get_current_user(token)
