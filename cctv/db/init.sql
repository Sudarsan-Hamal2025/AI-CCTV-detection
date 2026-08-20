-- MySQL schema for CCTV demo (minimal)
CREATE DATABASE IF NOT EXISTS cctv_security DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cctv_security;

-- detection events table
CREATE TABLE IF NOT EXISTS detection_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  user_id INT DEFAULT NULL,
  camera_id VARCHAR(128) DEFAULT NULL,
  camera_name VARCHAR(256) DEFAULT NULL,
  camera_location VARCHAR(256) DEFAULT NULL,
  event_type VARCHAR(128) NOT NULL,
  confidence FLOAT DEFAULT NULL,
  bbox_coordinates JSON DEFAULT NULL,
  details TEXT DEFAULT NULL
);

-- captured images associated with events
CREATE TABLE IF NOT EXISTS captured_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  user_id INT DEFAULT NULL,
  file_path VARCHAR(1024) NOT NULL,
  file_size INT DEFAULT NULL,
  thumbnail_path VARCHAR(1024) DEFAULT NULL,
  is_deleted TINYINT(1) DEFAULT 0,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES detection_events(id) ON DELETE CASCADE
);

-- simple users/roles for demo (optional)
CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL,
  permissions JSON DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(128) UNIQUE NOT NULL,
  email VARCHAR(256) DEFAULT NULL,
  password_hash VARCHAR(256) DEFAULT NULL,
  role_id INT DEFAULT 1,
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
