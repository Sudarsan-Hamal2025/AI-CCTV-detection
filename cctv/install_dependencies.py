#!/usr/bin/env python3
"""
Dependency Installation Script for CCTV Security System
Handles installation of required packages with fallbacks
"""

import subprocess
import sys
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_package(package_name, fallback_name=None):
    """Install a package with optional fallback"""
    try:
        logger.info(f"Installing {package_name}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
        logger.info(f"✓ {package_name} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to install {package_name}: {e}")
        if fallback_name:
            logger.info(f"Trying fallback: {fallback_name}")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', fallback_name])
                logger.info(f"✓ {fallback_name} installed as fallback")
                return True
            except subprocess.CalledProcessError:
                logger.error(f"Failed to install both {package_name} and {fallback_name}")
                return False
        else:
            logger.error(f"Failed to install {package_name}")
            return False

def check_package(package_name):
    """Check if a package is installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    """Main installation function"""
    logger.info("="*60)
    logger.info("CCTV Security System - Dependency Installer")
    logger.info("="*60)
    
    # List of packages to install with fallbacks
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
        ('PyYAML', None),
        ('python-dotenv', None),
        ('Pillow', None),
        ('numpy', None),
        ('pandas', None),
        ('tqdm', None)
    ]
    
    success_count = 0
    total_packages = len(packages)
    
    for i, (package, fallback) in enumerate(packages, 1):
        logger.info(f"[{i}/{total_packages}] Processing {package}...")
        
        # Check if already installed
        main_package_name = package.split('[')[0]  # Get main package name
        if check_package(main_package_name):
            logger.info(f"✓ {package_name} already installed")
            success_count += 1
            continue
        
        # Try to install
        if install_package(package, fallback):
            success_count += 1
        else:
            logger.error(f"❌ Failed to install {package}")
    
    logger.info("="*60)
    logger.info(f"Installation Summary: {success_count}/{total_packages} packages successful")
    logger.info("="*60)
    
    if success_count == total_packages:
        logger.info("✅ All dependencies installed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python setup.py")
        logger.info("2. Run: python integrated_system.py")
        return True
    else:
        logger.error(f"❌ {total_packages - success_count} packages failed to install")
        logger.info("\nTroubleshooting:")
        logger.info("1. Make sure you have internet connection")
        logger.info("2. Try installing manually: pip install -r requirements.txt")
        logger.info("3. For MySQL issues, try: pip install PyMySQL")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nInstallation error: {e}")
        sys.exit(1)
