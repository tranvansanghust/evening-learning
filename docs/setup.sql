-- Evening Learning - MySQL Setup Script
-- Run this script to create database and user

-- Create database
CREATE DATABASE IF NOT EXISTS evening_learning
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS 'evening_user'@'localhost' IDENTIFIED BY 'evening_password_123';

-- Grant privileges
GRANT ALL PRIVILEGES ON evening_learning.* TO 'evening_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify
SELECT "✅ Database 'evening_learning' and user 'evening_user' created successfully!" AS Status;
