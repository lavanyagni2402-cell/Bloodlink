-- Run once as the MySQL root user:
--     mysql -u root -p < sql/setup.sql
-- Creates the database and a dedicated user that Django, the CGI page and the scripts use.

CREATE DATABASE IF NOT EXISTS bloodlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'bloodlink'@'localhost' IDENTIFIED BY 'bloodlink123';
GRANT ALL PRIVILEGES ON bloodlink.* TO 'bloodlink'@'localhost';
-- Django's test runner creates a separate test database
GRANT ALL PRIVILEGES ON test_bloodlink.* TO 'bloodlink'@'localhost';
FLUSH PRIVILEGES;
