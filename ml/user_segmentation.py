"""用户画像分析 —— KMeans 聚类分群

算法流程:
1. 从 MySQL 提取 5 维用户特征 (登录/浏览/购买/金额/最近活跃)
2. StandardScaler 标准化
3. KMeans k=4 聚类
4. 依据聚类中心自动映射至高价值/潜力/普通/流失用户
5. 结果写入 user_segments 表
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sqlalchemy import text
from backend.app.database import engine, SessionLocal
from datetime import datetime

# ══════════════════════════════════════════════════════════════
#  Section 1: 特征提取
# ══════════════════════════════════════════════════════════════

def extract_features() -> pd.DataFrame:
    """从 MySQL 提取全部用户的 5 维行为特征"""
    sql = text("""
        SELECT
            u.user_id,
            COALESCE(login.login_count, 0)       AS login_count,
            COALESCE(view_count.view_count, 0)    AS view_count,
            COALESCE(pay.purchase_count, 0)       AS purchase_count,
            COALESCE(pay.total_amount, 0)         AS total_amount,
            DATEDIFF(
                (SELECT MAX(event_time) FROM user_events),
                COALESCE(last_active.last_active_time, u.registration_time)
            )                                      AS days_since_last_active
        FROM users u
        LEFT JOIN (
            -- 登录次数
            SELECT user_id, COUNT(*) AS login_count
            FROM user_events
            WHERE event_type = 'login'
            GROUP BY user_id
        ) login ON u.user_id = login.user_id
        LEFT JOIN (
            -- 浏览商品次数
            SELECT user_id, COUNT(*) AS view_count
            FROM user_events
            WHERE event_type = 'view_product'
            GROUP BY user_id
        ) view_count ON u.user_id = view_count.user_id
        LEFT JOIN (
            -- 购买次数 & 消费总额
            SELECT user_id, COUNT(*) AS purchase_count, SUM(amount) AS total_amount
            FROM orders
            WHERE order_status IN ('已支付', '退款')
            GROUP BY user_id
        ) pay ON u.user_id = pay.user_id
        LEFT JOIN (
            -- 最近活跃时间（事件或订单中取最后）
            SELECT
                user_id,
                MAX(last_ts) AS last_active_time
            FROM (
                SELECT user_id, MAX(event_time) AS last_ts
                FROM user_events
                GROUP BY user_id
                UNION ALL
                SELECT user_id, MAX(pay_time) AS last_ts
                FROM orders
                GROUP BY user_id
            ) combined
            GROUP BY user_id
        ) last_active ON u.user_id = last_active.user_id
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    # 确保数值类型
    for col in ["login_count", "view_count", "purchase_count", "total_amount", "days_since_last_active"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    print(f"[特征提取] {len(df)} 位用户, 特征维度={df.shape[1]-1}")
    return df


# ══════════════════════════════════════════════════════════════
#  Section 2: KMeans 聚类
# ══════════════════════════════════════════════════════════════

def run_kmeans(df: pd.DataFrame) -> tuple[pd.DataFrame, KMeans, StandardScaler]:
    """标准化 → KMeans → 映射类别标签"""
    feature_cols = [
        "login_count", "view_count", "purchase_count",
        "total_amount", "days_since_last_active",
    ]
    X = df[feature_cols].values

    # ── 缩放 ──
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── 聚类 k=4 ──
    kmeans = KMeans(n_clusters=4, random_state=42, n_init="auto", max_iter=300)
    labels = kmeans.fit_predict(X_scaled)

    # ── 自动映射: 按综合得分排序 ──
    # 得分 = 前4个特征越高越好, days_since_last_active 越低越好
    centers = kmeans.cluster_centers_
    score = (centers[:, 0] + centers[:, 1] + centers[:, 2] + centers[:, 3]) - centers[:, 4]
    # 排名: 得分最高的 → 高价值, 第二 → 潜力, 第三 → 普通, 最低 → 流失
    ranked = np.argsort(-score)  # 降序
    segment_names = ["高价值用户", "潜力用户", "普通用户", "流失用户"]
    label_map = {ranked[i]: segment_names[i] for i in range(4)}

    df["cluster_id"] = labels
    df["segment"] = df["cluster_id"].map(label_map)

    # ── 保存标准化特征 JSON ──
    df["feature_json"] = [
        json.dumps({k: round(float(v), 4) for k, v in zip(feature_cols, row)})
        for row in X_scaled
    ]

    # ── 打印分群统计 ──
    print(f"\n[聚类结果] k=4, 迭代次数={kmeans.n_iter_}")
    for seg in segment_names:
        sub = df[df["segment"] == seg]
        print(f"\n  {seg} ({len(sub)}人):")
        for col in feature_cols:
            print(f"    {col}: avg={sub[col].mean():.1f},  med={sub[col].median():.1f}")

    return df, kmeans, scaler


# ══════════════════════════════════════════════════════════════
#  Section 3: 结果入库
# ══════════════════════════════════════════════════════════════

def save_to_db(df: pd.DataFrame):
    """写入 user_segments 表（先清空再写入）"""
    session = SessionLocal()
    try:
        # 清空旧数据
        session.execute(text("TRUNCATE TABLE user_segments"))
        session.commit()

        # 批量插入
        records = []
        for _, row in df.iterrows():
            records.append({
                "user_id": int(row["user_id"]),
                "login_count": int(row["login_count"]),
                "view_count": int(row["view_count"]),
                "purchase_count": int(row["purchase_count"]),
                "total_amount": float(row["total_amount"]),
                "days_since_last_active": int(row["days_since_last_active"]),
                "cluster_id": int(row["cluster_id"]),
                "segment": str(row["segment"]),
                "feature_json": str(row["feature_json"]),
                "created_at": datetime.now(),
            })

        session.execute(
            text("""
                INSERT INTO user_segments
                    (user_id, login_count, view_count, purchase_count, total_amount,
                     days_since_last_active, cluster_id, segment, feature_json, created_at)
                VALUES
                    (:user_id, :login_count, :view_count, :purchase_count, :total_amount,
                     :days_since_last_active, :cluster_id, :segment, :feature_json, :created_at)
            """),
            records,
        )
        session.commit()
        print(f"\n[入库] {len(records)} 条记录写入 user_segments")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════
#  Section 4: 主入口
# ══════════════════════════════════════════════════════════════

def run() -> dict:
    """执行完整聚类流水线, 返回概览统计"""
    print("=" * 60)
    print("  用户画像分析 — KMeans 聚类")
    print("=" * 60)

    df = extract_features()
    df, kmeans, scaler = run_kmeans(df)
    save_to_db(df)

    # 构建返回概览
    overview = []
    for seg in ["高价值用户", "潜力用户", "普通用户", "流失用户"]:
        sub = df[df["segment"] == seg]
        overview.append({
            "segment": seg,
            "count": int(len(sub)),
            "avg_login": round(float(sub["login_count"].mean()), 1),
            "avg_view": round(float(sub["view_count"].mean()), 1),
            "avg_purchase": round(float(sub["purchase_count"].mean()), 1),
            "avg_amount": round(float(sub["total_amount"].mean()), 2),
            "avg_days_inactive": round(float(sub["days_since_last_active"].mean()), 1),
        })

    total = len(df)
    return {
        "total_users": total,
        "clusters": 4,
        "iterations": int(kmeans.n_iter_),
        "inertia": round(float(kmeans.inertia_), 0),
        "segments": overview,
    }


if __name__ == "__main__":
    result = run()
    print(f"\n[Done] {result['total_users']} 用户分群完成")
