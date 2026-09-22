"""Load the MySQL dataset (scripts/mysql_dataset.sql) into a MySQL server.

Connection is resolved from (first match wins):
  1. the DATABASE_URL environment variable (mysql+pymysql://...)
  2. --host/--port/--user/--password/--database command-line arguments
  3. defaults: root / localhost:3306 / laptop_allocation

Usage:
    python scripts/load_mysql_dataset.py
    python scripts/load_mysql_dataset.py --host 127.0.0.1 --port 3306 \\
        --user root --password yourpassword --database laptop_allocation

Or set the app's DATABASE_URL and run:
    python scripts/load_mysql_dataset.py
"""

import argparse
import os
import sys

try:
    import pymysql
    from pymysql.constants import CLIENT
except ImportError:
    sys.exit("PyMySQL is not installed. Run: pip install -r requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))
SQL_PATH = os.path.join(HERE, "mysql_dataset.sql")


def parse_url(url):
    prefix = "mysql+pymysql://"
    if not url.startswith(prefix):
        return None
    rest = url[len(prefix):].split("?")[0]
    auth, sep, host_db = rest.partition("@")
    if not sep:
        return None
    host, _, database = host_db.partition("/")
    hostname, _, port_s = host.partition(":")
    user, _, password = auth.partition(":")
    return (
        hostname or "localhost",
        int(port_s) if port_s else 3306,
        user,
        password or None,
        database or "laptop_allocation",
    )


def main():
    parser = argparse.ArgumentParser(description="Load the MySQL dataset")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default=None)
    parser.add_argument("--database", default="laptop_allocation")
    args = parser.parse_args()

    host, port, user, password, database = (
        args.host, args.port, args.user, args.password, args.database
    )
    url = os.environ.get("DATABASE_URL", "")
    if url and url.startswith("mysql"):
        parsed = parse_url(url)
        if parsed:
            host, port, user, password, database = parsed
            print(f"Using connection from DATABASE_URL: {user}@{host}:{port}/{database}")

    if not os.path.exists(SQL_PATH):
        sys.exit(f"Dataset file not found: {SQL_PATH}")

    with open(SQL_PATH, encoding="utf-8") as fh:
        script = fh.read()

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset="utf8mb4",
            client_flag=CLIENT.MULTI_STATEMENTS,
            autocommit=True,
        )
    except pymysql.MySQLError as exc:
        sys.exit(f"Could not connect to MySQL at {host}:{port} ({exc})")

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(f"USE `{database}`")
            cursor.execute(script)
            while cursor.nextset():
                pass
            cursor.execute(
                "SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM laptops), "
                "(SELECT COUNT(*) FROM interns), (SELECT COUNT(*) FROM allocations)"
            )
            row = cursor.fetchone()
            print(f"Dataset loaded into MySQL `{database}`:")
            print(f"  users={row[0]} laptops={row[1]} interns={row[2]} allocations={row[3]}")
    except pymysql.MySQLError as exc:
        sys.exit(f"Failed to load dataset: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()