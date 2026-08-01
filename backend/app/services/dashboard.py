"""Dashboard 业务逻辑层 —— 聚合查询 & 指标计算"""

from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text

from app.models import User, UserEvent, Order


# ═══════════════════════════════════════════════════════════
#  Dashboard 概览
# ═══════════════════════════════════════════════════════════

def get_dashboard_overview(db: Session, target_date: date | None = None):
    """
    返回单日概览：DAU / 新增 / GMV / 支付用户 / 转化率
    """
    if target_date is None:
        target_date = _latest_event_date(db)
    if target_date is None:
        return None

    day_start = target_date
    day_end = target_date + timedelta(days=1)

    # DAU —— 当天有任何行为事件的去重用户
    dau = (
        db.query(func.count(distinct(UserEvent.user_id)))
        .filter(UserEvent.event_time >= day_start, UserEvent.event_time < day_end)
        .scalar()
    ) or 0

    # 新增用户 —— 当天注册
    new_users = (
        db.query(func.count(distinct(User.user_id)))
        .filter(User.registration_time >= day_start, User.registration_time < day_end)
        .scalar()
    ) or 0

    # GMV —— 当天已支付订单金额总和
    gmv = (
        db.query(func.coalesce(func.sum(Order.amount), 0))
        .filter(
            Order.pay_time >= day_start,
            Order.pay_time < day_end,
            Order.order_status == "已支付",
        )
        .scalar()
    ) or 0

    # 支付用户数
    paying_users = (
        db.query(func.count(distinct(Order.user_id)))
        .filter(
            Order.pay_time >= day_start,
            Order.pay_time < day_end,
            Order.order_status == "已支付",
        )
        .scalar()
    ) or 0

    # 浏览用户数（用于转化率分母）
    viewers = (
        db.query(func.count(distinct(UserEvent.user_id)))
        .filter(
            UserEvent.event_time >= day_start,
            UserEvent.event_time < day_end,
            UserEvent.event_type == "view_product",
        )
        .scalar()
    ) or 0

    conversion_rate = round(paying_users / viewers, 4) if viewers > 0 else 0

    return {
        "date": target_date,
        "overview": {
            "dau": int(dau),
            "new_users": int(new_users),
            "gmv": round(float(gmv), 2),
            "paying_users": int(paying_users),
            "conversion_rate": conversion_rate,
        },
    }


# ═══════════════════════════════════════════════════════════
#  漏斗分析
# ═══════════════════════════════════════════════════════════

def get_funnel(db: Session, start_date: date | None = None, end_date: date | None = None):
    """
    查询指定日期范围内的转化漏斗：
    view_product → add_cart → pay
    """
    if start_date is None:
        start_date = _default_start(db)
    if end_date is None:
        end_date = _latest_event_date(db) or date.today()

    day_end = end_date + timedelta(days=1)

    # 各步骤去重用户数
    viewers = _count_event_users(db, "view_product", start_date, day_end)
    add_carts = _count_event_users(db, "add_cart", start_date, day_end)
    payers = _count_event_users(db, "pay", start_date, day_end)

    steps = [
        {"step": "浏览商品", "count": viewers,  "rate": None},
        {"step": "加入购物车", "count": add_carts, "rate": _rate(add_carts, viewers)},
        {"step": "支付",        "count": payers,    "rate": _rate(payers, add_carts)},
    ]
    overall = round(payers / viewers, 4) if viewers > 0 else 0

    return {"steps": steps, "overall_rate": overall}


# ═══════════════════════════════════════════════════════════
#  留存分析
# ═══════════════════════════════════════════════════════════

def get_retention(db: Session, start_date: date | None = None, end_date: date | None = None):
    """
    按天计算次日留存 & 7 日留存。
    新用户 = 当日注册；留存 = 该批新用户在次日/第 7 天仍有行为。
    """
    if start_date is None:
        start_date = _default_start(db)
    if end_date is None:
        end_date = _latest_event_date(db) or date.today()

    items = []
    current = start_date
    while current <= end_date:
        next_day = current + timedelta(days=1)
        day7 = current + timedelta(days=7)

        # 当日注册 / 有行为用户
        new_users = _count_registered(db, current)

        day1_ret = _retention_for_cohort(db, current, next_day) if new_users > 0 else None
        day7_ret = _retention_for_cohort(db, current, day7) if new_users > 0 else None

        items.append({
            "date": current,
            "new_users": new_users,
            "day1_retention": day1_ret,
            "day7_retention": day7_ret,
        })
        current += timedelta(days=1)

    return {"items": items}


# ═══════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════

def _latest_event_date(db: Session) -> date | None:
    row = db.query(func.max(UserEvent.event_time)).scalar()
    return row.date() if row else None


def _default_start(db: Session) -> date:
    latest = _latest_event_date(db)
    return latest - timedelta(days=29) if latest else date.today() - timedelta(days=29)


def _count_event_users(db: Session, event_type: str, lo, hi) -> int:
    return (
        db.query(func.count(distinct(UserEvent.user_id)))
        .filter(
            UserEvent.event_time >= lo,
            UserEvent.event_time < hi,
            UserEvent.event_type == event_type,
        )
        .scalar()
    ) or 0


def _count_registered(db: Session, d: date) -> int:
    return (
        db.query(func.count(distinct(User.user_id)))
        .filter(User.registration_time >= d, User.registration_time < d + timedelta(days=1))
        .scalar()
    ) or 0


def _retention_for_cohort(db: Session, cohort_date: date, target_date: date) -> float | None:
    """cohort_date 注册的用户中，target_date 仍有行为的比例"""
    cohort_size = _count_registered(db, cohort_date)
    if cohort_size == 0:
        return None
    retained = (
        db.query(func.count(distinct(UserEvent.user_id)))
        .join(User, User.user_id == UserEvent.user_id)
        .filter(
            User.registration_time >= cohort_date,
            User.registration_time < cohort_date + timedelta(days=1),
            UserEvent.event_time >= target_date,
            UserEvent.event_time < target_date + timedelta(days=1),
        )
        .scalar()
    ) or 0
    return round(retained / cohort_size, 4)


# ═══════════════════════════════════════════════════════════
#  趋势数据
# ═══════════════════════════════════════════════════════════

def get_trends(db: Session, start_date: date | None = None, end_date: date | None = None):
    """
    按天返回 DAU 和 GMV 趋势数据（用于折线图/柱状图）。
    """
    if start_date is None:
        start_date = _default_start(db)
    if end_date is None:
        end_date = _latest_event_date(db) or date.today()

    # 直接用 SQL 做一次 Join 聚合，比循环 N 次快得多
    sql = text("""
        SELECT
            d,
            COALESCE(dau, 0) AS dau,
            COALESCE(gmv, 0) AS gmv
        FROM (
            SELECT DATE(e.event_time) AS d, COUNT(DISTINCT e.user_id) AS dau
            FROM user_events e
            WHERE e.event_time >= :lo AND e.event_time < :hi
            GROUP BY DATE(e.event_time)
        ) t1
        LEFT JOIN (
            SELECT DATE(o.pay_time) AS d, COALESCE(SUM(o.amount), 0) AS gmv
            FROM orders o
            WHERE o.pay_time >= :lo AND o.pay_time < :hi
              AND o.order_status = '已支付'
            GROUP BY DATE(o.pay_time)
        ) t2 USING (d)
        ORDER BY d
    """)
    rows = db.execute(sql, {
        "lo": start_date,
        "hi": end_date + timedelta(days=1),
    }).fetchall()

    return {
        "items": [
            {"date": r[0], "dau": int(r[1]), "gmv": round(float(r[2]), 2)}
            for r in rows
        ],
    }


# ═══════════════════════════════════════════════════════════
#  来源分布
# ═══════════════════════════════════════════════════════════

def get_source_distribution(db: Session):
    """用户来源渠道分布（饼图/玫瑰图）"""
    rows = (
        db.query(User.channel, func.count(User.user_id))
        .group_by(User.channel)
        .order_by(func.count(User.user_id).desc())
        .all()
    )
    return {
        "items": [
            {"channel": r[0], "count": int(r[1])}
            for r in rows
        ],
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator > 0 else None
