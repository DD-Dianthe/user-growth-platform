#!/usr/bin/env python
"""
MariaDB 一键初始化 & 启动脚本
=============================
在 backend/.env 中填写 MYSQL_PASSWORD 后运行此脚本。

功能：
  1. 解压 MariaDB 到 ~/.workbuddy/binaries/mysql/mariadb/
  2. 初始化 data 目录 + 设置 root 密码
  3. 启动 mariadbd 并创建 user_growth 数据库
  4. 执行建表 DDL
  5. 导入模拟数据
"""

import os
import sys
import time
import shutil
import zipfile
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "binaries", "mysql")
MARIA_DIR = os.path.join(BIN_DIR, "mariadb")
ZIP_FILE = os.path.join(BIN_DIR, "mariadb.zip")
MOCK_DIR = os.path.join(ROOT, "data", "mock")
DDL_FILE = os.path.join(ROOT, "database", "migrations", "001_init_tables.sql")

# 从 .env 读取密码
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "backend", ".env"))
PASSWORD = os.getenv("MYSQL_PASSWORD", "root123")
PORT = int(os.getenv("MYSQL_PORT", "3306"))


def run(cmd, **kwargs):
    """运行命令并打印输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    if result.returncode != 0 and kwargs.get("check", True):
        print(f"  ❌ 命令失败: {cmd}\n  {result.stderr[:200]}")
    return result


def find_extracted_dir():
    """找到解压后的目录名"""
    for name in os.listdir(BIN_DIR):
        full = os.path.join(BIN_DIR, name)
        if os.path.isdir(full) and "mariadb" in name.lower():
            return full
    return None


def step_extract():
    """解压 MariaDB"""
    if os.path.exists(MARIA_DIR):
        print("  ✅ MariaDB 目录已存在，跳过解压")
        return

    # 寻找 ZIP 文件
    zip_path = ZIP_FILE
    if not os.path.exists(zip_path):
        extracted = find_extracted_dir()
        if extracted:
            os.rename(extracted, MARIA_DIR)
            print(f"  ✅ 已重命名 {os.path.basename(extracted)} → mariadb")
            return
        print("  ❌ 未找到 mariadb.zip，请先下载")
        sys.exit(1)

    print(f"  📦 解压 {os.path.basename(zip_path)} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(BIN_DIR)

    extracted = find_extracted_dir()
    if extracted and extracted != MARIA_DIR:
        os.rename(extracted, MARIA_DIR)
        print(f"  ✅ 解压完成 → {MARIA_DIR}")


def step_init():
    """初始化数据目录"""
    data_dir = os.path.join(MARIA_DIR, "data")
    if os.path.exists(data_dir):
        print("  ✅ data 目录已初始化，跳过")
        return

    os.makedirs(data_dir, exist_ok=True)
    exe = os.path.join(MARIA_DIR, "bin", "mariadb-install-db.exe")
    if not os.path.exists(exe):
        exe = os.path.join(MARIA_DIR, "bin", "mysql_install_db.exe")

    print(f"  🔧 初始化 data 目录 (密码: {PASSWORD}) ...")
    result = run(f'"{exe}" --datadir="{data_dir}" --password={PASSWORD}', cwd=MARIA_DIR)
    print(f"  {result.stdout.strip()[-200:]}")


def step_start():
    """启动 MariaDB"""
    exe = os.path.join(MARIA_DIR, "bin", "mariadbd.exe")
    if not os.path.exists(exe):
        exe = os.path.join(MARIA_DIR, "bin", "mysqld.exe")

    # 检查是否已启动
    try:
        import socket
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        print(f"  ✅ MariaDB 已在 {PORT} 端口运行")
        return
    except:
        pass

    print(f"  🚀 启动 MariaDB ...")
    subprocess.Popen(
        [exe, f"--datadir={os.path.join(MARIA_DIR, 'data')}", f"--port={PORT}"],
        cwd=MARIA_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    print(f"  ✅ MariaDB 已启动 (端口 {PORT})")


def step_create_db():
    """创建数据库 + 执行 DDL"""
    import pymysql

    print("  📐 创建数据库 + 执行 DDL ...")
    conn = pymysql.connect(
        host="127.0.0.1", port=PORT, user="root", password=PASSWORD,
    )
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS user_growth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.select_db("user_growth")

    with open(DDL_FILE, "r", encoding="utf-8") as f:
        for stmt in f.read().split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.upper().startswith(("CREATE DATABASE", "USE ")):
                continue
            try:
                cur.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    pass

    conn.commit()
    conn.close()
    print("  ✅ 数据库 + 表结构就绪")


def step_import_data(batch_size=5000):
    """批量导入 CSV 数据"""
    import pandas as pd
    from sqlalchemy import create_engine

    engine = create_engine(
        f"mysql+pymysql://root:{PASSWORD}@127.0.0.1:{PORT}/user_growth?charset=utf8mb4"
    )
    engine.execute("SET FOREIGN_KEY_CHECKS = 0")

    tables = {
        "users": ("users.csv", {"user_id": int, "age": int, "gender": str, "city": str,
                                  "device_type": str, "channel": str}, ["registration_time"], {}),
        "user_events": ("user_events.csv", {"user_id": int, "event_type": str, "session_id": str,
                                              "page_url": str, "duration_ms": int}, ["event_time"],
                         {"event_date": lambda c: pd.to_datetime(c).dt.date}),
        "orders": ("orders.csv", {"order_id": int, "user_id": int, "product_category": str,
                                    "order_status": str, "is_first_order": bool}, ["pay_time"],
                     {"pay_date": lambda c: pd.to_datetime(c).dt.date}),
    }

    for table, (csv_file, dtypes, dates, transforms) in tables.items():
        path = os.path.join(MOCK_DIR, csv_file)
        if not os.path.exists(path):
            print(f"  ⚠️  {csv_file} 不存在，跳过")
            continue

        print(f"  📥 导入 {table} ({os.path.getsize(path)/1024/1024:.0f}MB)...")
        t0 = time.time()
        total = 0
        for chunk in pd.read_csv(path, chunksize=batch_size, dtype=dtypes, parse_dates=dates):
            for col, fn in transforms.items():
                if col in chunk.columns:
                    chunk[col] = fn(chunk[col])
            chunk.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=batch_size)
            total += len(chunk)
        elapsed = time.time() - t0
        print(f"    {total:,} 行 | {elapsed:.1f}s")

    engine.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("  ✅ 数据导入完成")


def main():
    print("=" * 60)
    print("🔧 MariaDB 一键初始化 & 数据导入")
    print("=" * 60)
    print()

    os.chdir(ROOT)
    step_extract()
    step_init()
    step_start()
    step_create_db()

    # 检查是否已导入数据
    import pymysql
    conn = pymysql.connect(host="127.0.0.1", port=PORT, user="root", password=PASSWORD, database="user_growth")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()

    if count > 0:
        print(f"  ✅ 数据已存在 (users: {count:,} 行)，跳过导入")
    else:
        step_import_data()

    print()
    print("=" * 60)
    print("✅ 全部就绪！")
    print(f"   数据库: user_growth @ 127.0.0.1:{PORT}")
    print(f"   用户: root / {PASSWORD}")
    print(f"   启动后端: cd backend && uvicorn app.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
