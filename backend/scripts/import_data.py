"""CSV → SQLite 数据导入脚本 —— 使用 pandas.to_sql 自动处理类型转换"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.database import engine, init_db

CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mock")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")


def main():
    # 删旧库重建
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()

    # ── 用户表 ──
    print("[1/3] 导入 users...", end=" ", flush=True)
    t0 = time.time()
    df = pd.read_csv(
        f"{CSV_DIR}/users.csv",
        parse_dates=["registration_time"],
    )
    df.to_sql("users", engine, if_exists="append", index=False)
    print(f"{len(df):,} 条 | {time.time()-t0:.1f}s")

    # ── 行为事件 ──
    print("[2/3] 导入 user_events...", end=" ", flush=True)
    t0 = time.time()
    for i, chunk in enumerate(pd.read_csv(
        f"{CSV_DIR}/user_events.csv",
        parse_dates=["event_time"],
        chunksize=100_000,
    )):
        chunk.to_sql("user_events", engine, if_exists="append", index=False)
        print(f"\r[2/3] 导入 user_events... {(i+1)*100000:>8,}", end=" ", flush=True)
    print(f"| {time.time()-t0:.1f}s")

    # ── 订单 ──
    print("[3/3] 导入 orders...", end=" ", flush=True)
    t0 = time.time()
    df = pd.read_csv(
        f"{CSV_DIR}/orders.csv",
        parse_dates=["pay_time"],
    )
    df["is_first_order"] = df["is_first_order"].astype(bool)
    df.to_sql("orders", engine, if_exists="append", index=False)
    print(f"{len(df):,} 条 | {time.time()-t0:.1f}s")

    print("✅ 导入完成")


if __name__ == "__main__":
    main()
