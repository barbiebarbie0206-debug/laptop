"""Build the MySQL dataset SQL file from the current SQLite database.

This reads backend/laptop_allocation.db (users, laptops, interns), enriches the
laptops with realistic spec values, appends a set of sample allocations, and
writes a complete, self-contained MySQL 8 script to scripts/mysql_dataset.sql.

Usage:
    cd backend
    python scripts/build_mysql_dataset.py [path/to/laptop_allocation.db]
"""

import os
import sqlite3
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "laptop_allocation.db")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mysql_dataset.sql")

LAPTOP_SPECS = {
    ("Dell", "Latitude 5520"): ("Intel Core i5-1135G7", "8 GB", "256 GB SSD", "Windows 11 Pro"),
    ("HP", "EliteBook 840 G8"): ("Intel Core i5-1145G7", "16 GB", "512 GB SSD", "Windows 11 Pro"),
    ("Lenovo", "ThinkPad T14"): ("AMD Ryzen 5 PRO 5650U", "8 GB", "256 GB SSD", "Windows 11 Pro"),
    ("Dell", "Inspiron 15"): ("Intel Core i3-1115G4", "8 GB", "1 TB HDD", "Windows 10 Home"),
    ("HP", "Pavilion 15"): ("Intel Core i5-1235U", "8 GB", "512 GB SSD", "Windows 11 Home"),
    ("Lenovo", "IdeaPad Slim 5"): ("AMD Ryzen 5 5500U", "8 GB", "512 GB SSD", "Windows 11 Home"),
    ("Acer", "Aspire 5"): ("Intel Core i3-1115G4", "4 GB", "1 TB HDD", "Windows 10 Home"),
}


def sql_str(value):
    if value is None:
        return "NULL"
    s = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def sql_date(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" " if isinstance(value, datetime) else "")
    return value


def fetch(conn, sql):
    return conn.execute(sql).fetchall()


def build():
    if not os.path.exists(DB_PATH):
        sys.exit(f"SQLite database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    users = fetch(conn, "SELECT username, email, hashed_password, full_name, role, is_active FROM users")
    laptops = fetch(
        conn,
        "SELECT laptop_number, brand, model, serial_number, processor, ram, storage, "
        "operating_system, status FROM laptops ORDER BY laptop_number",
    )
    interns = fetch(
        conn,
        "SELECT intern_id, name, email, phone, batch, domain FROM interns ORDER BY intern_id",
    )
    conn.close()

    lines = []
    lines.append("-- =====================================================================")
    lines.append("-- Laptop Allocation Management System - MySQL 8 dataset")
    lines.append("--")
    lines.append("-- Self-contained schema + seed data generated from the application's")
    lines.append("-- SQLAlchemy models and the seeded records in laptop_allocation.db.")
    lines.append("--")
    lines.append("-- Includes:")
    lines.append("--   * users, laptops, interns   (as seeded by backend/app/models/seed.py)")
    lines.append("--   * laptops enriched with processor / RAM / storage / OS values")
    lines.append("--   * a set of sample allocations (ACTIVE / RETURNED / CANCELLED)")
    lines.append("--   * a generated-column UNIQUE key so a laptop can only have ONE active")
    lines.append("--     allocation at a time (MySQL has no partial/filtered indexes)")
    lines.append("--")
    lines.append("-- Load with the mysql client or:  python scripts/load_mysql_dataset.py")
    lines.append("-- =====================================================================")
    lines.append("")

    lines.append("CREATE DATABASE IF NOT EXISTS laptop_allocation")
    lines.append("  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    lines.append("USE laptop_allocation;")
    lines.append("")

    lines.append("SET FOREIGN_KEY_CHECKS = 0;")
    lines.append("DROP TABLE IF EXISTS allocations;")
    lines.append("DROP TABLE IF EXISTS interns;")
    lines.append("DROP TABLE IF EXISTS laptops;")
    lines.append("DROP TABLE IF EXISTS users;")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    lines.append("")

    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- users")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("CREATE TABLE users (")
    lines.append("  id INT NOT NULL AUTO_INCREMENT,")
    lines.append("  username VARCHAR(50) NOT NULL,")
    lines.append("  email VARCHAR(100) NOT NULL,")
    lines.append("  hashed_password VARCHAR(255) NOT NULL,")
    lines.append("  full_name VARCHAR(100) NOT NULL,")
    lines.append("  role ENUM('ADMIN','STAFF') NOT NULL DEFAULT 'STAFF',")
    lines.append("  is_active TINYINT(1) NOT NULL DEFAULT 1,")
    lines.append("  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,")
    lines.append("  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,")
    lines.append("  PRIMARY KEY (id),")
    lines.append("  UNIQUE KEY uq_users_username (username),")
    lines.append("  UNIQUE KEY uq_users_email (email)")
    lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
    lines.append("")

    lines.append("CREATE TABLE laptops (")
    lines.append("  id INT NOT NULL AUTO_INCREMENT,")
    lines.append("  laptop_number VARCHAR(20) NOT NULL,")
    lines.append("  brand VARCHAR(50) NOT NULL,")
    lines.append("  model VARCHAR(100) NOT NULL,")
    lines.append("  serial_number VARCHAR(100) NOT NULL,")
    lines.append("  processor VARCHAR(100) NULL,")
    lines.append("  ram VARCHAR(100) NULL,")
    lines.append("  storage VARCHAR(100) NULL,")
    lines.append("  operating_system VARCHAR(100) NULL,")
    lines.append("  status ENUM('FREE','ALLOCATED','MAINTENANCE','INACTIVE') NOT NULL DEFAULT 'FREE',")
    lines.append("  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,")
    lines.append("  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,")
    lines.append("  PRIMARY KEY (id),")
    lines.append("  UNIQUE KEY uq_laptops_number (laptop_number),")
    lines.append("  UNIQUE KEY uq_laptops_serial (serial_number)")
    lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
    lines.append("")

    lines.append("CREATE TABLE interns (")
    lines.append("  id INT NOT NULL AUTO_INCREMENT,")
    lines.append("  intern_id VARCHAR(20) NOT NULL,")
    lines.append("  name VARCHAR(100) NOT NULL,")
    lines.append("  email VARCHAR(100) NOT NULL,")
    lines.append("  phone VARCHAR(20) NOT NULL,")
    lines.append("  batch ENUM('MORNING','AFTERNOON','FULL_DAY') NOT NULL,")
    lines.append("  domain ENUM('CLOUD','DATA_ANALYTICS','FULL_STACK','AI_ML',")
    lines.append("             'DIGITAL_MARKETING','UI_UX') NOT NULL,")
    lines.append("  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,")
    lines.append("  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,")
    lines.append("  PRIMARY KEY (id),")
    lines.append("  UNIQUE KEY uq_interns_id (intern_id),")
    lines.append("  UNIQUE KEY uq_interns_email (email)")
    lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
    lines.append("")

    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- allocations")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 'active_laptop_key' is a generated column that is NULL for every non-")
    lines.append("-- ACTIVE row, so the UNIQUE key enforces at most one ACTIVE allocation per")
    lines.append("-- laptop while still allowing full allocation history.")
    lines.append("CREATE TABLE allocations (")
    lines.append("  id INT NOT NULL AUTO_INCREMENT,")
    lines.append("  laptop_id INT NOT NULL,")
    lines.append("  intern_id INT NOT NULL,")
    lines.append("  batch VARCHAR(20) NOT NULL,")
    lines.append("  domain VARCHAR(50) NOT NULL,")
    lines.append("  allocation_date DATE NOT NULL,")
    lines.append("  start_time TIME NOT NULL,")
    lines.append("  end_time TIME NOT NULL,")
    lines.append("  status ENUM('ACTIVE','COMPLETED','CANCELLED','RETURNED') NOT NULL DEFAULT 'ACTIVE',")
    lines.append("  returned_at DATETIME NULL,")
    lines.append("  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,")
    lines.append("  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,")
    lines.append("  active_laptop_key BIGINT AS (CASE WHEN `status` = 'ACTIVE'")
    lines.append("    THEN `laptop_id` ELSE NULL END) STORED,")
    lines.append("  PRIMARY KEY (id),")
    lines.append("  UNIQUE KEY uq_allocations_active_laptop (active_laptop_key),")
    lines.append("  KEY idx_allocations_laptop (laptop_id),")
    lines.append("  KEY idx_allocations_intern (intern_id),")
    lines.append("  KEY idx_allocations_status (status),")
    lines.append("  CONSTRAINT fk_allocations_laptop FOREIGN KEY (laptop_id)")
    lines.append("    REFERENCES laptops (id) ON DELETE CASCADE,")
    lines.append("  CONSTRAINT fk_allocations_intern FOREIGN KEY (intern_id)")
    lines.append("    REFERENCES interns (id)")
    lines.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
    lines.append("")

    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- Seed data")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO users (username, email, hashed_password, full_name, role, is_active) VALUES")
    values = ",\n".join(
        f"  ({sql_str(u[0])}, {sql_str(u[1])}, {sql_str(u[2])}, {sql_str(u[3])}, "
        f"{sql_str(u[4])}, {int(u[5])})"
        for u in users
    )
    lines.append(values + ";")
    lines.append("")

    lines.append("INSERT INTO laptops (laptop_number, brand, model, serial_number, processor, ram, storage, operating_system, status) VALUES")
    spec_entries = []
    for lp in laptops:
        number, brand, model, serial, *_ , status = (
            lp[0], lp[1], lp[2], lp[3], lp[4], lp[5], lp[6], lp[7], lp[8]
        )
        spec = LAPTOP_SPECS.get((brand, model)) or (None, None, None, None)
        processor = spec[0] if lp[4] in (None, "") else lp[4]
        ram = spec[1] if lp[5] in (None, "") else lp[5]
        storage = spec[2] if lp[6] in (None, "") else lp[6]
        os_name = spec[3] if lp[7] in (None, "") else lp[7]
        spec_entries.append(
            f"  ({sql_str(number)}, {sql_str(brand)}, {sql_str(model)}, {sql_str(serial)}, "
            f"{sql_str(processor)}, {sql_str(ram)}, {sql_str(storage)}, {sql_str(os_name)}, {sql_str(status)})"
        )
    lines.append(",\n".join(spec_entries) + ";")
    lines.append("")

    lines.append("INSERT INTO interns (intern_id, name, email, phone, batch, domain) VALUES")
    intern_values = ",\n".join(
        f"  ({sql_str(i[0])}, {sql_str(i[1])}, {sql_str(i[2])}, {sql_str(i[3])}, "
        f"{sql_str(i[4])}, {sql_str(i[5])})"
        for i in interns
    )
    lines.append(intern_values + ";")
    lines.append("")

    sample_allocations = [
        (1, 1, "Morning", "Full Stack", date(2026, 9, 1), "09:00:00", "12:00:00", "ACTIVE", None),
        (2, 2, "Morning", "Data Analytics", date(2026, 9, 1), "09:00:00", "12:00:00", "ACTIVE", None),
        (4, 4, "Morning", "AI & ML", date(2026, 9, 1), "09:00:00", "12:00:00", "ACTIVE", None),
        (5, 7, "Afternoon", "Full Stack", date(2026, 9, 2), "14:00:00", "17:00:00", "ACTIVE", None),
        (10, 3, "Afternoon", "Cloud", date(2026, 9, 2), "14:00:00", "17:00:00", "ACTIVE", None),
        (3, 6, "Morning", "Digital Marketing", date(2026, 8, 18), "09:00:00", "12:00:00", "RETURNED", datetime(2026, 8, 29, 18, 0, 0)),
        (6, 5, "Afternoon", "UI/UX", date(2026, 8, 20), "14:00:00", "17:00:00", "RETURNED", datetime(2026, 8, 28, 17, 30, 0)),
        (9, 10, "Morning", "UI/UX", date(2026, 8, 24), "09:00:00", "12:00:00", "RETURNED", datetime(2026, 8, 28, 12, 15, 0)),
        (7, 8, "Morning", "Data Analytics", date(2026, 8, 15), "09:00:00", "12:00:00", "CANCELLED", None),
    ]
    lines.append("INSERT INTO allocations (laptop_id, intern_id, batch, domain, allocation_date, start_time, end_time, status, returned_at) VALUES")
    alloc_values = ",\n".join(
        f"  ({a[0]}, {a[1]}, {sql_str(a[2])}, {sql_str(a[3])}, '{a[4]!s}', "
        f"'{a[5]}', '{a[6]}', {sql_str(a[7])}, {sql_str(a[8])})"
        for a in sample_allocations
    )
    lines.append(alloc_values + ";")
    lines.append("")

    lines.append("-- Laptop statuses kept consistent with the sample allocations above.")
    lines.append("UPDATE laptops SET status = 'ALLOCATED'")
    lines.append("  WHERE id IN (1, 2, 4, 5, 10);")
    lines.append("")

    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- Sanity check: seeded rows present")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("SELECT (SELECT COUNT(*) FROM users)  AS users,")
    lines.append("       (SELECT COUNT(*) FROM laptops) AS laptops,")
    lines.append("       (SELECT COUNT(*) FROM interns) AS interns,")
    lines.append("       (SELECT COUNT(*) FROM allocations) AS allocations;")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"Wrote {OUT_PATH}")
    print(f"  users={len(users)} laptops={len(laptops)} interns={len(interns)} allocations={len(sample_allocations)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        DB_PATH = sys.argv[1]
    build()