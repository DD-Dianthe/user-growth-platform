#!/usr/bin/env python
"""
Mock 数据导入 MySQL 脚本
=======================
从 data/mock/ 目录读取 CSV，批量写入 MySQL 数据库。

用法：
  python import_to_mysql.py                     # 使用 .env 中的配置
  python import_to_mysql.py --host 127.0.0.1 --port 3306 --user root --password xxx --database user_growth

数据映射：
  users.csv       → users 表         (100,000 行)
  user_events.csv → user_events 表   (1,000,000 行)
  orders.csv      → orders 表        (300,000 行)
"""

import os
import sys
import time
import argparse
import pandas as pd
import pymysql
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 自动加载 .env 文件（项目根目录和 backend 目录）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT, "backend", ".env"))
load_dotenv(os.path.join(ROOT, ".env"))

# ── 配置 ─────────────────────────────────────────────
MOCK_DIR = os.path.join(ROOT, "data", "mock")
BATCH_SIZE = 5000      # 每批插入行数
DDL_FILE = os.path.join(ROOT, "database", "migrations", "001_init_tables.sql")


def get_db_config(args) -> dict:
    """获取数据库配置：命令行参数 > 环境变量 > 默认值"""
    return {
        "host": args.host or os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(args.port or os.getenv("MYSQL_PORT", "3306")),
        "user": args.user or os.getenv("MYSQL_USER", "root"),
        "password": args.password or os.getenv("MYSQL_PASSWORD", ""),
        "database": args.database or os.getenv("MYSQL_DATABASE", "user_growth"),
        "charset": "utf8mb4",
    }


def build_engine(cfg: dict):
    """构建 SQLAlchemy 引擎（mysql+pymysql 驱动）"""
    url = (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        f"?charset={cfg['charset']}"
    )
    return create_engine(url, echo=False, pool_size=5, pool_recycle=3600)


def run_ddl(engine, ddl_file: str):
    """执行建表 SQL（跳过 CREATE DATABASE / USE 语句）"""
    with open(ddl_file, "r", encoding="utf-8") as f:
        sql = f.read()

    # 按分号拆分，过滤空语句和数据库操作语句
    statements = []
    for s in sql.split(";"):
        s = s.strip()
        if not s:
            continue
        upper = s.upper()
        if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
            continue
        statements.append(s)

    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                # 表已存在则跳过
                if "already exists" in str(e).lower() or "Duplicate" in str(e):
                    continue
                print(f"  ⚠️  SQL 执行警告: {str(e)[:100]}")
        # 先禁用外键检查加速导入
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    print("  ✅ 建表完成，外键检查已临时禁用（导入后恢复）")


def import_csv(engine, table_name: str, csv_path: str, dtype_map: dict = None,
               parse_dates: list = None, transform_cols: dict = None):
    """通用 CSV → MySQL 批量导入"""
    print(f"\n📥 导入 {table_name} ...")

    t0 = time.time()
    reader = pd.read_csv(csv_path, chunksize=BATCH_SIZE, dtype=dtype_map,
                         parse_dates=parse_dates)

    total_rows = 0
    chunk_count = 0

    for chunk in reader:
        # 应用列变换：fn 接收整个 DataFrame，返回新列
        if transform_cols:
            for col, fn in transform_cols.items():
                chunk[col] = fn(chunk)

        chunk.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=BATCH_SIZE,
        )
        total_rows += len(chunk)
        chunk_count += 1
        if chunk_count % 20 == 0:
            elapsed = time.time() - t0
            rps = total_rows / elapsed if elapsed > 0 else 0
            print(f"    已导入 {total_rows:>10,} 行 | 速度 {rps:>8,.0f} 行/秒")

    elapsed = time.time() - t0
    rps = total_rows / elapsed if elapsed > 0 else 0
    file_size = os.path.getsize(csv_path) / 1024 / 1024
    print(f"  ✅ {table_name} 导入完成: {total_rows:,} 行 | {elapsed:.1f}s | {file_size:.1f}MB | {rps:,.0f} 行/秒")
    return total_rows


def main():
    parser = argparse.ArgumentParser(description="Mock 数据 → MySQL 导入工具")
    parser.add_argument("--host", help="MySQL 主机地址")
    parser.add_argument("--port", type=int, help="MySQL 端口")
    parser.add_argument("--user", help="MySQL 用户名")
    parser.add_argument("--password", help="MySQL 密码")
    parser.add_argument("--database", help="数据库名")
    parser.add_argument("--skip-ddl", action="store_true", help="跳过建表步骤")
    args = parser.parse_args()

    cfg = get_db_config(args)
    print("=" * 60)
    print("📦 Mock 数据 → MySQL 导入工具")
    print("=" * 60)
    print(f"  目标: {cfg['host']}:{cfg['port']}/{cfg['database']}")
    print(f"  用户: {cfg['user']}")
    print(f"  批次: {BATCH_SIZE:,} 行/批")
    print()

    # 测试连接
    print("🔗 测试数据库连接...")
    try:
        # 先连接不指定数据库来创建数据库
        conn = pymysql.connect(
            host=cfg["host"], port=cfg["port"],
            user=cfg["user"], password=cfg["password"],
            charset=cfg["charset"]
        )
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()
        print("  ✅ 数据库已就绪")
    except pymysql.err.OperationalError as e:
        print(f"  ❌ 连接失败: {e}")
        print("\n  💡 请检查 MySQL 是否启动，以及连接参数是否正确。")
        print("     示例: python import_to_mysql.py --host 127.0.0.1 --user root --password yourpass")
        return

    engine = build_engine(cfg)

    # 执行建表
    if not args.skip_ddl:
        print("\n📐 执行建表 DDL ...")
        run_ddl(engine, DDL_FILE)

    # ── 导入三张表 ──
    total_start = time.time()

    # 1. users
    import_csv(
        engine, "users",
        os.path.join(MOCK_DIR, "users.csv"),
        dtype_map={"user_id": int, "age": int, "gender": str, "city": str,
                   "device_type": str, "channel": str},
        parse_dates=["registration_time"],
    )

    # 2. user_events —— 大表，额外生成 event_date 冗余列
    import_csv(
        engine, "user_events",
        os.path.join(MOCK_DIR, "user_events.csv"),
        dtype_map={"user_id": int, "event_type": str, "session_id": str,
                   "page_url": str, "duration_ms": int},
        parse_dates=["event_time"],
        transform_cols={"event_date": lambda df: pd.to_datetime(df["event_time"]).dt.date},
    )

    # 3. orders
    import_csv(
        engine, "orders",
        os.path.join(MOCK_DIR, "orders.csv"),
        dtype_map={"order_id": int, "user_id": int, "product_category": str,
                   "order_status": str, "is_first_order": bool},
        parse_dates=["pay_time"],
        transform_cols={"pay_date": lambda df: pd.to_datetime(df["pay_time"]).dt.date},
    )

    # ── 恢复外键检查 ──
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    # ── 验证行数 ──
    print("\n" + "=" * 60)
    print("📊 导入结果验证")
    print("=" * 60)
    expected = {"users": 100000, "user_events": 1000000, "orders": 300000}
    with engine.connect() as conn:
        for table, exp in expected.items():
            row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            actual = row[0]
            ok = "✅" if actual >= exp else "❌"
            print(f"  {ok} {table:>15s}: {actual:>10,}  (预期 {exp:,})")

    total_elapsed = time.time() - total_start
    print(f"\n  ⏱️  总耗时: {total_elapsed:.1f} 秒")
    print("  ✅ 数据导入全部完成！")


if __name__ == "__main__":
    main()
