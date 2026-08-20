#!/usr/bin/env python3
"""
Check and fix authentication credentials
"""

import logging
import sys
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import database modules
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
        sys.exit(1)

def check_credentials():
    """Check and potentially fix credentials"""
    try:
        # Load config
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        db_config = config.get('database', {})
        
        # Connect to MySQL
        if MYSQL_CONNECTOR:
            connection = mysql.connector.connect(
                host=db_config.get('host', 'localhost'),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'cctv_security')
            )
        else:
            connection = pymysql.connect(
                host=db_config.get('host', 'localhost'),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', 'cctv_security')
            )
        
        cursor = connection.cursor()
        cursor.execute(f"USE {db_config.get('database', 'cctv_security')}")
        
        # Check if superadmin exists
        cursor.execute("SELECT * FROM users WHERE username = 'superadmin'")
        result = cursor.fetchone()
        
        if result:
            logger.info("✓ Super admin user found in database")
            logger.info(f"  ID: {result[0]}")
            logger.info(f"  Username: {result[1]}")
            logger.info(f"  Email: {result[2]}")
            logger.info(f"  Password Hash: {result[3]}")
            
            # Test password verification
            test_password = "admin123"
            test_hash = hashlib.sha256(test_password.encode()).hexdigest()
            is_valid = test_hash == result[3]
            
            if is_valid:
                logger.info("✓ Password verification test passed")
            else:
                logger.error("❌ Password verification test failed")
                logger.info("  Expected hash: " + test_hash)
                logger.info("  Actual hash: " + result[3])
                
                # Fix the password
                logger.info("Fixing password hash in database...")
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = 'superadmin'",
                    (test_hash,)
                )
                connection.commit()
                logger.info("✓ Password hash fixed")
        else:
            logger.error("❌ Super admin user not found in database")
            
            # Create super admin user
            logger.info("Creating super admin user...")
            default_password = "admin123"
            password_hash = hashlib.sha256(default_password.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, role_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                'superadmin',
                'admin@cctv.com',
                password_hash,
                'Super Administrator',
                3  # Super admin role ID
            ))
            connection.commit()
            logger.info("✓ Created super admin user")
            logger.info("  Username: superadmin")
            logger.info("  Password: admin123")
            logger.info("  ⚠️  Please change this password after first login!")
        
        connection.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking credentials: {e}")
        return False

def main():
    """Main function"""
    logger.info("Checking authentication credentials...")
    
    if check_credentials():
        logger.info("✅ Credentials check completed successfully!")
        logger.info("\nLogin credentials:")
        logger.info("Username: superadmin")
        logger.info("Password: admin123")
        logger.info("\nYou can now:")
        logger.info("1. Run: python integrated_system.py")
        logger.info("2. Access: http://localhost:8000")
        logger.info("3. Login with the above credentials")
    else:
        logger.error("❌ Credentials check failed!")
        logger.info("\nTroubleshooting:")
        logger.info("1. Make sure MySQL is running")
        logger.info("2. Check config.yaml database settings")
        logger.info("3. Try: python check_credentials.py")

if __name__ == "__main__":
    main()
