#!/usr/bin/env python3
"""
CCTV Security System Setup Script
Initializes database, creates default admin user, and sets up directories
"""

import os
import sys
import hashlib
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemSetup:
    def __init__(self):
        self.mysql_available = self.check_mysql_availability()
    
    def check_mysql_availability(self):
        """Check if mysql-connector-python is available"""
        try:
            import mysql.connector
            return True
        except ImportError:
            try:
                import pymysql
                logger.info("Using PyMySQL as fallback")
                return True
            except ImportError:
                logger.error("Neither mysql-connector-python nor PyMySQL is available")
                return False
    
    def install_dependencies(self):
        """Install required Python packages"""
        try:
            logger.info("Installing required packages...")
            
            # Install packages one by one to handle failures gracefully
            packages = [
                ('mysql-connector-python', 'PyMySQL'),
                ('PyYAML', None),
                ('ultralytics', None),
                ('opencv-python', 'opencv-python-headless'),
                ('fastapi', None),
                ('uvicorn[standard]', None),
                ('PyJWT', None),
                ('cryptography', None),
                ('schedule', None),
                ('email-validator', None),
                ('pydantic[email]', None)
            ]
            
            for package, fallback in packages:
                try:
                    package_name = package.split('[')[0]  # Get main package name
                    logger.info(f"Installing {package}...")
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    logger.info(f"✓ {package} installed successfully")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to install {package}: {e}")
                    if fallback:
                        logger.info(f"Trying alternative installation method for {package}")
                        try:
                            subprocess.check_call([sys.executable, '-m', 'pip', 'install', fallback])
                            logger.info(f"✓ {fallback} installed as alternative")
                        except:
                            logger.error(f"Failed to install {package}. Please install manually:")
                            logger.error(f"pip install {package}")
                            return False
                    else:
                        logger.error(f"Failed to install {package}. Please install manually:")
                        logger.error(f"pip install {package}")
                        return False
            
            logger.info("✓ All dependencies installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
    
    def load_config(self):
        """Load configuration from config.yaml"""
        try:
            import yaml
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error("config.yaml not found. Please create it first.")
            return None
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None
    
    def connect_to_mysql(self):
        """Connect to MySQL server (without database)"""
        if not self.mysql_available:
            logger.error("MySQL connector not available. Please install mysql-connector-python or PyMySQL")
            return None
            
        try:
            import mysql.connector
            db_config = self.config.get('database', {})
            connection = mysql.connector.connect(
                host=db_config.get('host', 'localhost'),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', '')
            )
            logger.info("✓ Connected to MySQL server")
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            logger.info("Please check your MySQL configuration in config.yaml")
            return None
    
    def create_database(self):
        """Create the database and schema"""
        try:
            # Connect to MySQL server
            self.db_connection = self.connect_to_mysql()
            if not self.db_connection:
                return False
            
            cursor = self.db_connection.cursor()
            
            # Read and execute schema
            with open('database_schema.sql', 'r') as f:
                schema_sql = f.read()
            
            # Split SQL statements and execute
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        cursor.execute(statement)
                        self.db_connection.commit()
                    except Exception as e:
                        logger.warning(f"SQL Warning: {e}")
                        # Continue with other statements
            
            logger.info("✓ Database schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            return False
        finally:
            if self.db_connection:
                self.db_connection.close()
    
    def create_directories(self):
        """Create necessary directories"""
        directories = [
            'uploads',
            'uploads/images',
            'uploads/videos',
            'uploads/thumbnails',
            'uploads/temp',
            'logs',
            'web/static',
            'data'
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"✓ Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
    
    def create_default_admin(self):
        """Create default super admin user"""
        if not self.mysql_available:
            logger.error("Cannot create admin user - MySQL connector not available")
            return False
            
        try:
            # Connect to the database
            db_config = self.config.get('database', {})
            connection = self.connect_to_mysql()
            if not connection:
                return False
            
            # Use the correct database
            cursor = connection.cursor()
            cursor.execute(f"USE {db_config.get('database', 'cctv_security')}")
            
            # Check if super admin already exists
            cursor.execute("SELECT id FROM users WHERE username = 'superadmin'")
            if cursor.fetchone():
                logger.info("✓ Super admin user already exists")
                connection.close()
                return True
            
            # Create super admin user
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
            connection.close()
            
            logger.info("✓ Created default super admin user:")
            logger.info("   Username: superadmin")
            logger.info("   Password: admin123")
            logger.info("   ⚠️  Please change this password after first login!")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")
            return False
    
    def create_sample_subscriptions(self):
        """Create sample subscription plans"""
        if not self.mysql_available:
            logger.error("Cannot create subscriptions - MySQL connector not available")
            return False
            
        try:
            db_config = self.config.get('database', {})
            connection = self.connect_to_mysql()
            if not connection:
                return False
            
            cursor = connection.cursor()
            cursor.execute(f"USE {db_config.get('database', 'cctv_security')}")
            
            # Check if subscriptions already exist
            cursor.execute("SELECT COUNT(*) FROM subscriptions")
            if cursor.fetchone()[0] > 0:
                logger.info("✓ Subscription plans already exist")
                connection.close()
                return True
            
            # Insert subscription plans
            subscriptions = [
                (
                    'Basic',
                    29.99,
                    30,
                    1,
                    10,
                    '{"detection_types": ["person"], "video_recording": false, "alerts": true}'
                ),
                (
                    'Professional',
                    59.99,
                    30,
                    3,
                    50,
                    '{"detection_types": ["person", "vehicle"], "video_recording": true, "alerts": true, "analytics": false}'
                ),
                (
                    'Enterprise',
                    199.99,
                    30,
                    10,
                    500,
                    '{"detection_types": ["person", "vehicle", "weapon"], "video_recording": true, "alerts": true, "analytics": true, "api_access": true}'
                )
            ]
            
            cursor.executemany("""
                INSERT INTO subscriptions (name, price, duration_days, max_cameras, max_storage_gb, features)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, subscriptions)
            
            connection.commit()
            connection.close()
            
            logger.info("✓ Created sample subscription plans")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sample subscriptions: {e}")
            return False
    
    def verify_installation(self):
        """Verify the installation"""
        if not self.mysql_available:
            logger.error("Cannot verify installation - MySQL connector not available")
            return False
            
        try:
            # Check database connection
            db_config = self.config.get('database', {})
            connection = self.connect_to_mysql()
            if not connection:
                return False
            
            cursor = connection.cursor()
            cursor.execute(f"USE {db_config.get('database', 'cctv_security')}")
            
            # Check tables
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = [
                'users', 'roles', 'subscriptions', 'user_subscriptions',
                'detection_events', 'captured_images', 'video_recordings', 'system_logs'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False
            
            # Check admin user
            cursor.execute("SELECT COUNT(*) FROM users WHERE role_id = 3")
            admin_count = cursor.fetchone()[0]
            if admin_count == 0:
                logger.error("No super admin user found")
                return False
            
            connection.close()
            
            # Check directories
            required_dirs = ['uploads/images', 'uploads/videos', 'uploads/thumbnails']
            for directory in required_dirs:
                if not os.path.exists(directory):
                    logger.error(f"Missing directory: {directory}")
                    return False
            
            logger.info("✓ Installation verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying installation: {e}")
            return False
    
    def run_setup(self):
        """Run the complete setup process"""
        logger.info("="*60)
        logger.info("CCTV Security System Setup")
        logger.info("="*60)
        
        # Step 1: Install dependencies
        logger.info("\n🔄 Step 1: Installing dependencies...")
        if not self.install_dependencies():
            logger.error("❌ Failed to install dependencies")
            return False
        
        # Re-check MySQL availability after installation
        self.mysql_available = self.check_mysql_availability()
        if not self.mysql_available:
            logger.error("❌ MySQL connector still not available after installation")
            logger.info("Please install manually:")
            logger.info("pip install mysql-connector-python")
            logger.info("OR: pip install PyMySQL")
            return False
        
        # Step 2: Load configuration
        logger.info("\n🔄 Step 2: Loading configuration...")
        self.config = self.load_config()
        if not self.config:
            return False
        
        # Step 3: Create directories
        logger.info("\n🔄 Step 3: Creating directories...")
        self.create_directories()
        
        # Step 4: Create database schema
        logger.info("\n🔄 Step 4: Creating database schema...")
        if not self.create_database():
            return False
        
        # Step 5: Create default admin user
        logger.info("\n🔄 Step 5: Creating default admin user...")
        if not self.create_default_admin():
            return False
        
        # Step 6: Create sample subscriptions
        logger.info("\n🔄 Step 6: Creating sample subscriptions...")
        if not self.create_sample_subscriptions():
            return False
        
        # Step 7: Verify installation
        logger.info("\n🔄 Step 7: Verifying installation...")
        if not self.verify_installation():
            return False
        
        logger.info("\n" + "="*60)
        logger.info("🎉 Setup completed successfully!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Download YOLOv8 model: python -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\"")
        logger.info("2. Update config.yaml with your settings")
        logger.info("3. Run the system: python integrated_system.py")
        logger.info("4. Access web interface: http://localhost:8000")
        logger.info("\nDefault login:")
        logger.info("Username: superadmin")
        logger.info("Password: admin123")
        logger.info("\n⚠️  Remember to change the default password!")
        
        return True

def main():
    """Main setup function"""
    try:
        setup = SystemSetup()
        success = setup.run_setup()
        
        if success:
            logger.info("\n✅ Setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n❌ Setup failed!")
            logger.info("\nTroubleshooting tips:")
            logger.info("1. Make sure MySQL is running")
            logger.info("2. Check your MySQL credentials in config.yaml")
            logger.info("3. Install dependencies manually: pip install -r requirements.txt")
            logger.info("4. Try alternative MySQL connector: pip install PyMySQL")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nSetup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
