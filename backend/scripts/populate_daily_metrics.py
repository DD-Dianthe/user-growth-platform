"""按天聚合 raw data 写入 daily_metrics 预聚合表 —— 一次性脚本"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine

SQL = """
INSERT INTO daily_metrics (stat_date, dau, new_users,
    login_count, view_count, cart_count, pay_event_count,
    gmv, pay_users, order_count, first_order_count, avg_order_amount)

SELECT
    d.full_date,
    COALESCE(e.dau, 0),
    COALESCE(u.new_users, 0),
    COALESCE(e.login_cnt, 0),
    COALESCE(e.view_cnt, 0),
    COALESCE(e.cart_cnt, 0),
    COALESCE(e.pay_cnt, 0),
    COALESCE(o.gmv, 0),
    COALESCE(o.pay_users, 0),
    COALESCE(o.order_cnt, 0),
    COALESCE(o.first_cnt, 0),
    COALESCE(o.avg_amt, 0)

FROM (
    -- 日期序列：从最早事件日到最新
    SELECT DISTINCT DATE(event_time) AS full_date FROM user_events
    UNION
    SELECT DISTINCT DATE(pay_time) FROM orders
    UNION
    SELECT DISTINCT DATE(registration_time) FROM users
) d

LEFT JOIN (
    SELECT DATE(event_time) AS dt,
           COUNT(DISTINCT user_id) AS dau,
           SUM(CASE WHEN event_type = 'login' THEN 1 ELSE 0 END) AS login_cnt,
           SUM(CASE WHEN event_type = 'view_product' THEN 1 ELSE 0 END) AS view_cnt,
           SUM(CASE WHEN event_type = 'add_cart' THEN 1 ELSE 0 END) AS cart_cnt,
           SUM(CASE WHEN event_type = 'pay' THEN 1 ELSE 0 END) AS pay_cnt
    FROM user_events
    GROUP BY DATE(event_time)
) e ON d.full_date = e.dt

LEFT JOIN (
    SELECT DATE(registration_time) AS dt, COUNT(*) AS new_users
    FROM users
    GROUP BY DATE(registration_time)
) u ON d.full_date = u.dt

LEFT JOIN (
    SELECT DATE(pay_time) AS dt,
           COALESCE(SUM(amount), 0) AS gmv,
           COUNT(DISTINCT user_id) AS pay_users,
           COUNT(*) AS order_cnt,
           SUM(CASE WHEN is_first_order = 1 THEN 1 ELSE 0 END) AS first_cnt,
           COALESCE(ROUND(AVG(amount), 2), 0) AS avg_amt
    FROM orders
    WHERE order_status = '已支付'
    GROUP BY DATE(pay_time)
) o ON d.full_date = o.dt

ON DUPLICATE KEY UPDATE
    dau = VALUES(dau),
    new_users = VALUES(new_users),
    login_count = VALUES(login_count),
    view_count = VALUES(view_count),
    cart_count = VALUES(cart_count),
    pay_event_count = VALUES(pay_event_count),
    gmv = VALUES(gmv),
    pay_users = VALUES(pay_users),
    order_count = VALUES(order_count),
    first_order_count = VALUES(first_order_count),
    avg_order_amount = VALUES(avg_order_amount)
"""

def main():
    with engine.begin() as conn:
        result = conn.execute(text(SQL))
        conn.commit()
        print(f"✅ daily_metrics 写入完成")

    # 验证
    with SessionLocal() as db:
        total = db.execute(text("SELECT COUNT(*) FROM daily_metrics")).scalar()
        date_range = db.execute(
            text("SELECT MIN(stat_date), MAX(stat_date) FROM daily_metrics")
        ).fetchone()
        sample = db.execute(
            text("SELECT * FROM daily_metrics ORDER BY stat_date DESC LIMIT 3")
        ).fetchall()

        print(f"  总行数: {total}")
        print(f"  日期范围: {date_range[0]} ~ {date_range[1]}")
        print(f"  最近 3 天样例:")
        for r in sample:
            print(f"    {r}")

if __name__ == "__main__":
    main()
