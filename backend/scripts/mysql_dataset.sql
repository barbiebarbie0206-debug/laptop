-- =====================================================================
-- Laptop Allocation Management System - MySQL 8 dataset
--
-- Self-contained schema + seed data generated from the application's
-- SQLAlchemy models and the seeded records in laptop_allocation.db.
--
-- Includes:
--   * users, laptops, interns   (as seeded by backend/app/models/seed.py)
--   * laptops enriched with processor / RAM / storage / OS values
--   * a set of sample allocations (ACTIVE / RETURNED / CANCELLED)
--   * a generated-column UNIQUE key so a laptop can only have ONE active
--     allocation at a time (MySQL has no partial/filtered indexes)
--
-- Load with the mysql client or:  python scripts/load_mysql_dataset.py
-- =====================================================================

CREATE DATABASE IF NOT EXISTS laptop_allocation
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE laptop_allocation;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS allocations;
DROP TABLE IF EXISTS interns;
DROP TABLE IF EXISTS laptops;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------
CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  email VARCHAR(100) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  full_name VARCHAR(100) NOT NULL,
  role ENUM('ADMIN','STAFF') NOT NULL DEFAULT 'STAFF',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE laptops (
  id INT NOT NULL AUTO_INCREMENT,
  laptop_number VARCHAR(20) NOT NULL,
  brand VARCHAR(50) NOT NULL,
  model VARCHAR(100) NOT NULL,
  serial_number VARCHAR(100) NOT NULL,
  processor VARCHAR(100) NULL,
  ram VARCHAR(100) NULL,
  storage VARCHAR(100) NULL,
  operating_system VARCHAR(100) NULL,
  status ENUM('FREE','ALLOCATED','MAINTENANCE','INACTIVE') NOT NULL DEFAULT 'FREE',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_laptops_number (laptop_number),
  UNIQUE KEY uq_laptops_serial (serial_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE interns (
  id INT NOT NULL AUTO_INCREMENT,
  intern_id VARCHAR(20) NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  batch ENUM('MORNING','AFTERNOON','FULL_DAY') NOT NULL,
  domain ENUM('CLOUD','DATA_ANALYTICS','FULL_STACK','AI_ML',
             'DIGITAL_MARKETING','UI_UX') NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_interns_id (intern_id),
  UNIQUE KEY uq_interns_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- allocations
-- ---------------------------------------------------------------------
-- 'active_laptop_key' is a generated column that is NULL for every non-
-- ACTIVE row, so the UNIQUE key enforces at most one ACTIVE allocation per
-- laptop while still allowing full allocation history.
CREATE TABLE allocations (
  id INT NOT NULL AUTO_INCREMENT,
  laptop_id INT NOT NULL,
  intern_id INT NOT NULL,
  batch VARCHAR(20) NOT NULL,
  domain VARCHAR(50) NOT NULL,
  allocation_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  status ENUM('ACTIVE','COMPLETED','CANCELLED','RETURNED') NOT NULL DEFAULT 'ACTIVE',
  returned_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  active_laptop_key BIGINT AS (CASE WHEN `status` = 'ACTIVE'
    THEN `laptop_id` ELSE NULL END) STORED,
  PRIMARY KEY (id),
  UNIQUE KEY uq_allocations_active_laptop (active_laptop_key),
  KEY idx_allocations_laptop (laptop_id),
  KEY idx_allocations_intern (intern_id),
  KEY idx_allocations_status (status),
  CONSTRAINT fk_allocations_laptop FOREIGN KEY (laptop_id)
    REFERENCES laptops (id) ON DELETE CASCADE,
  CONSTRAINT fk_allocations_intern FOREIGN KEY (intern_id)
    REFERENCES interns (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- Seed data
-- ---------------------------------------------------------------------
INSERT INTO users (username, email, hashed_password, full_name, role, is_active) VALUES
  ('admin', 'admin@laptopallocation.com', '$2b$12$HyIUCu43ScJHhOmOtH0miOqKldCqAMg3/0Hj8iSwT8OiSyYuE5CPu', 'System Administrator', 'ADMIN', 1);

INSERT INTO laptops (laptop_number, brand, model, serial_number, processor, ram, storage, operating_system, status) VALUES
  ('LP-001', 'Dell', 'Latitude 5520', 'DL-5520-001', 'Intel Core i5-1135G7', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-002', 'Dell', 'Latitude 5520', 'DL-5520-002', 'Intel Core i5-1135G7', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-003', 'HP', 'EliteBook 840 G8', 'HP-840G8-001', 'Intel Core i5-1145G7', '16 GB', '512 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-004', 'HP', 'EliteBook 840 G8', 'HP-840G8-002', 'Intel Core i5-1145G7', '16 GB', '512 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-005', 'Lenovo', 'ThinkPad T14', 'LN-T14-001', 'AMD Ryzen 5 PRO 5650U', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-006', 'Lenovo', 'ThinkPad T14', 'LN-T14-002', 'AMD Ryzen 5 PRO 5650U', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-007', 'Dell', 'Inspiron 15', 'DL-IN15-001', 'Intel Core i3-1115G4', '8 GB', '1 TB HDD', 'Windows 10 Home', 'FREE'),
  ('LP-008', 'HP', 'Pavilion 15', 'HP-PAV15-001', 'Intel Core i5-1235U', '8 GB', '512 GB SSD', 'Windows 11 Home', 'FREE'),
  ('LP-009', 'Lenovo', 'IdeaPad Slim 5', 'LN-IS5-001', 'AMD Ryzen 5 5500U', '8 GB', '512 GB SSD', 'Windows 11 Home', 'FREE'),
  ('LP-010', 'Acer', 'Aspire 5', 'AC-A5-001', 'Intel Core i3-1115G4', '4 GB', '1 TB HDD', 'Windows 10 Home', 'FREE'),
  ('LP-011', 'Dell', 'Latitude 5520', 'DL-5520-003', 'Intel Core i5-1135G7', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-012', 'HP', 'EliteBook 840 G8', 'HP-840G8-003', 'Intel Core i5-1145G7', '16 GB', '512 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-013', 'Lenovo', 'ThinkPad T14', 'LN-T14-003', 'AMD Ryzen 5 PRO 5650U', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-014', 'Acer', 'Aspire 5', 'AC-A5-002', 'Intel Core i3-1115G4', '4 GB', '1 TB HDD', 'Windows 10 Home', 'FREE'),
  ('LP-015', 'Dell', 'Inspiron 15', 'DL-IN15-002', 'Intel Core i3-1115G4', '8 GB', '1 TB HDD', 'Windows 10 Home', 'FREE'),
  ('LP-016', 'HP', 'Pavilion 15', 'HP-PAV15-002', 'Intel Core i5-1235U', '8 GB', '512 GB SSD', 'Windows 11 Home', 'FREE'),
  ('LP-017', 'Lenovo', 'IdeaPad Slim 5', 'LN-IS5-002', 'AMD Ryzen 5 5500U', '8 GB', '512 GB SSD', 'Windows 11 Home', 'FREE'),
  ('LP-018', 'Dell', 'Latitude 5520', 'DL-5520-004', 'Intel Core i5-1135G7', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE'),
  ('LP-019', 'HP', 'EliteBook 840 G8', 'HP-840G8-004', 'Intel Core i5-1145G7', '16 GB', '512 GB SSD', 'Windows 11 Pro', 'MAINTENANCE'),
  ('LP-020', 'Lenovo', 'ThinkPad T14', 'LN-T14-004', 'AMD Ryzen 5 PRO 5650U', '8 GB', '256 GB SSD', 'Windows 11 Pro', 'FREE');

INSERT INTO interns (intern_id, name, email, phone, batch, domain) VALUES
  ('INT-001', 'Aarav Sharma', 'aarav.sharma@interns.com', '9876543201', 'MORNING', 'FULL_STACK'),
  ('INT-002', 'Priya Patel', 'priya.patel@interns.com', '9876543202', 'MORNING', 'DATA_ANALYTICS'),
  ('INT-003', 'Rohan Gupta', 'rohan.gupta@interns.com', '9876543203', 'AFTERNOON', 'CLOUD'),
  ('INT-004', 'Sneha Reddy', 'sneha.reddy@interns.com', '9876543204', 'MORNING', 'AI_ML'),
  ('INT-005', 'Vikram Singh', 'vikram.singh@interns.com', '9876543205', 'AFTERNOON', 'UI_UX'),
  ('INT-006', 'Ananya Nair', 'ananya.nair@interns.com', '9876543206', 'MORNING', 'DIGITAL_MARKETING'),
  ('INT-007', 'Karthik Iyer', 'karthik.iyer@interns.com', '9876543207', 'AFTERNOON', 'FULL_STACK'),
  ('INT-008', 'Meera Joshi', 'meera.joshi@interns.com', '9876543208', 'MORNING', 'DATA_ANALYTICS'),
  ('INT-009', 'Aditya Verma', 'aditya.verma@interns.com', '9876543209', 'AFTERNOON', 'AI_ML'),
  ('INT-010', 'Nisha Das', 'nisha.das@interns.com', '9876543210', 'MORNING', 'UI_UX');

INSERT INTO allocations (laptop_id, intern_id, batch, domain, allocation_date, start_time, end_time, status, returned_at) VALUES
  (1, 1, 'Morning', 'Full Stack', '2026-09-01', '09:00:00', '12:00:00', 'ACTIVE', NULL),
  (2, 2, 'Morning', 'Data Analytics', '2026-09-01', '09:00:00', '12:00:00', 'ACTIVE', NULL),
  (4, 4, 'Morning', 'AI & ML', '2026-09-01', '09:00:00', '12:00:00', 'ACTIVE', NULL),
  (5, 7, 'Afternoon', 'Full Stack', '2026-09-02', '14:00:00', '17:00:00', 'ACTIVE', NULL),
  (10, 3, 'Afternoon', 'Cloud', '2026-09-02', '14:00:00', '17:00:00', 'ACTIVE', NULL),
  (3, 6, 'Morning', 'Digital Marketing', '2026-08-18', '09:00:00', '12:00:00', 'RETURNED', '2026-08-29 18:00:00'),
  (6, 5, 'Afternoon', 'UI/UX', '2026-08-20', '14:00:00', '17:00:00', 'RETURNED', '2026-08-28 17:30:00'),
  (9, 10, 'Morning', 'UI/UX', '2026-08-24', '09:00:00', '12:00:00', 'RETURNED', '2026-08-28 12:15:00'),
  (7, 8, 'Morning', 'Data Analytics', '2026-08-15', '09:00:00', '12:00:00', 'CANCELLED', NULL);

-- Laptop statuses kept consistent with the sample allocations above.
UPDATE laptops SET status = 'ALLOCATED'
  WHERE id IN (1, 2, 4, 5, 10);

-- ---------------------------------------------------------------------
-- Sanity check: seeded rows present
-- ---------------------------------------------------------------------
SELECT (SELECT COUNT(*) FROM users)  AS users,
       (SELECT COUNT(*) FROM laptops) AS laptops,
       (SELECT COUNT(*) FROM interns) AS interns,
       (SELECT COUNT(*) FROM allocations) AS allocations;
