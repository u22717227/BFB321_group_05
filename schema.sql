-- Eyabantu Taxi Program - MySQL Schema

-- Reset command: running this file drops and recreates the database.
DROP DATABASE IF EXISTS eyabantu;
CREATE DATABASE eyabantu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE eyabantu;

CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('commuter', 'driver', 'association')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS routes (
    route_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stops (
    stop_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    route_id INT,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    distance_to_cbd_km DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_stop_route (name, route_id),
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS taxi_positions (
    position_id INT PRIMARY KEY AUTO_INCREMENT,
    stop_id INT,
    driver_id INT,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    seats_available INT DEFAULT 15,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS demand_reports (
    report_id INT PRIMARY KEY AUTO_INCREMENT,
    stop_id INT,
    waiting_passengers INT NOT NULL DEFAULT 0 CHECK (waiting_passengers >= 0),
    reported_by INT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS problem_reports (
    problem_id INT PRIMARY KEY AUTO_INCREMENT,
    stop_id INT,
    problem_type VARCHAR(255) NOT NULL,
    description TEXT,
    reported_by INT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS verification_reports (
    verification_id INT PRIMARY KEY AUTO_INCREMENT,
    stop_id INT,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('stop_confirm', 'safe_pickup', 'safety_rating')),
    safety_rating INT CHECK (safety_rating BETWEEN 1 AND 5),
    reported_by INT,
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_taxi_stop ON taxi_positions(stop_id, is_active);
CREATE INDEX idx_demand_stop ON demand_reports(stop_id, reported_at);
CREATE INDEX idx_problems_stop ON problem_reports(stop_id, status);
