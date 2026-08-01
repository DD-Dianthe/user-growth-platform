"""Export MySQL to compact SQLite (no large text columns)."""
import sqlite3
import pymysql
import os
from decimal import Decimal
from datetime import date, datetime

MYSQL_CFG = {"host": "127.0.0.1", "port": 3307, "user": "root", "password": "root123", "database": "user_growth"}
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "data", "user_growth.db")

DDL = {
    "users": 'CREATE TABLE "users" (user_id INTEGER NOT NULL, age INTEGER NOT NULL, gender VARCHAR(4) NOT NULL, city VARCHAR(30) NOT NULL, device_type VARCHAR(10) NOT NULL, registration_time DATETIME NOT NULL, channel VARCHAR(30) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)',
    "user_events": 'CREATE TABLE "user_events" (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, event_type VARCHAR(20) NOT NULL, event_time DATETIME NOT NULL, event_date DATE NOT NULL, session_id VARCHAR(50) NOT NULL, page_url VARCHAR(200) NOT NULL, duration_ms INTEGER NOT NULL)',
    "orders": 'CREATE TABLE "orders" (order_id INTEGER NOT NULL, user_id INTEGER NOT NULL, amount REAL NOT NULL, product_category VARCHAR(30) NOT NULL, order_status VARCHAR(10) NOT NULL, is_first_order INTEGER NOT NULL, pay_time DATETIME NOT NULL, pay_date DATE NOT NULL, created_at DATETIME NOT NULL)',
    "daily_metrics": 'CREATE TABLE "daily_metrics" (id INTEGER PRIMARY KEY, stat_date DATE NOT NULL, dau INTEGER NOT NULL, new_users INTEGER NOT NULL, login_count INTEGER NOT NULL, view_count INTEGER NOT NULL, cart_count INTEGER NOT NULL, pay_event_count INTEGER NOT NULL, gmv REAL NOT NULL, pay_users INTEGER NOT NULL, order_count INTEGER NOT NULL, first_order_count INTEGER NOT NULL, avg_order_amount REAL NOT NULL, created_at DATETIME NOT NULL)',
    "anomaly_alerts": 'CREATE TABLE "anomaly_alerts" (id INTEGER PRIMARY KEY, alert_date DATE NOT NULL, detect_time DATETIME NOT NULL, method VARCHAR(32) NOT NULL, metric_name VARCHAR(32) NOT NULL, metric_value REAL NOT NULL, expected_value REAL, z_score REAL, anomaly_score REAL, severity VARCHAR(16) NOT NULL)',
    "churn_predictions": 'CREATE TABLE "churn_predictions" (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, churn_probability REAL NOT NULL, predicted_churn INTEGER NOT NULL, is_high_risk INTEGER NOT NULL, created_at DATETIME NOT NULL)',
    "user_segments": 'CREATE TABLE "user_segments" (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, login_count INTEGER NOT NULL, view_count INTEGER NOT NULL, purchase_count INTEGER NOT NULL, total_amount REAL NOT NULL, days_since_last_active INTEGER NOT NULL, cluster_id INTEGER NOT NULL, segment VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL)',
}

# Only keep essential indexes
INDEXES = [
    ("user_events", "user_id"), ("user_events", "event_date"), ("user_events", "event_type"),
    ("orders", "user_id"), ("orders", "pay_date"),
    ("churn_predictions", "user_id"), ("churn_predictions", "is_high_risk"),
    ("user_segments", "user_id"), ("user_segments", "segment"),
    ("anomaly_alerts", "alert_date"), ("anomaly_alerts", "severity"),
]

def to_sqlite(val):
    if isinstance(val, Decimal): return float(val)
    if isinstance(val, (date, datetime)): return str(val)
    return val


def main():
    mysql_conn = pymysql.connect(**MYSQL_CFG)
    if os.path.exists(SQLITE_PATH): os.remove(SQLITE_PATH)
    db = sqlite3.connect(SQLITE_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")

    for table, ddl in DDL.items():
        db.execute(f'DROP TABLE IF EXISTS "{table}"')
        db.execute(ddl)

    for table in DDL:
        print(f"  {table}...", end=" ", flush=True)
        mc = mysql_conn.cursor()

        # Limit rows for demo deployment
        limits = {
            "users": "LIMIT 20000",
            "user_events": "LIMIT 200000",
            "orders": "LIMIT 60000",
        }

        if table == "user_events":
            mc.execute(f"SELECT id, user_id, event_type, event_time, event_date, session_id, page_url, duration_ms FROM user_events {limits.get(table, '')}")
        elif table == "anomaly_alerts":
            mc.execute(f"SELECT id, alert_date, detect_time, method, metric_name, metric_value, expected_value, z_score, anomaly_score, severity FROM anomaly_alerts {limits.get(table, '')}")
        elif table == "churn_predictions":
            mc.execute(f"SELECT id, user_id, churn_probability, predicted_churn, is_high_risk, created_at FROM churn_predictions {limits.get(table, '')}")
        elif table == "user_segments":
            mc.execute(f"SELECT id, user_id, login_count, view_count, purchase_count, total_amount, days_since_last_active, cluster_id, segment, created_at FROM user_segments {limits.get(table, '')}")
        else:
            mc.execute(f"SELECT * FROM {table} {limits.get(table, '')}")

        rows = mc.fetchall()
        cols = [d[0] for d in mc.description]
        mc.close()

        placeholders = ",".join(["?"] * len(cols))
        col_names = ",".join(f'"{c}"' for c in cols)

        for i in range(0, len(rows), 5000):
            clean = [tuple(to_sqlite(v) for v in row) for row in rows[i:i+5000]]
            db.executemany(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})', clean)

        db.commit()
        print(f"{len(rows):,} rows")

    for tbl, col in INDEXES:
        db.execute(f'CREATE INDEX IF NOT EXISTS "idx_{tbl}_{col}" ON "{tbl}"("{col}")')
    db.commit()

    # Stats
    total = 0
    for table in DDL:
        cnt = db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        total += cnt
        print(f"  {table:25s} {cnt:>10,} rows")
    print(f"  {'TOTAL':25s} {total:>10,} rows")

    db.close()
    mysql_conn.close()

    size_mb = os.path.getsize(SQLITE_PATH) / 1024 / 1024
    print(f"\n  File: {size_mb:.1f} MB -> {SQLITE_PATH}")


if __name__ == "__main__":
    main()
