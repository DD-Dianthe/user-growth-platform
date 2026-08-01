"""异常检测模块 —— Z-Score DAU 检测 + Isolation Forest 行为检测"""

import sys, os
# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from backend.app.database import SessionLocal, engine
from datetime import date, timedelta


# ══════════════════════════════════════════════════════════════
#  数据加载
# ══════════════════════════════════════════════════════════════

def load_metrics_df() -> pd.DataFrame:
    """从 daily_metrics 加载全部聚合数据为 DataFrame"""
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT * FROM daily_metrics ORDER BY stat_date"),
            conn,
        )
        df["stat_date"] = pd.to_datetime(df["stat_date"]).dt.date
    return df


# ══════════════════════════════════════════════════════════════
#  1. Z-Score DAU 异常检测
# ══════════════════════════════════════════════════════════════

def detect_dau_anomaly_zscore(window: int = 30) -> list[dict]:
    """
    使用滚动 Z-Score 检测 DAU 异常。

    - 以最近 window 天为窗口计算均值和标准差
    - |z| > 2.5 → warning，|z| > 3.5 → critical
    - 返回异常记录列表，每条对应一个异常日期
    """
    df = load_metrics_df()
    alerts = []

    for i in range(window, len(df)):
        current_row = df.iloc[i]
        past_window = df.iloc[i - window : i]["dau"]

        mean = past_window.mean()
        std = past_window.std()

        if std == 0:
            continue

        dau_val = current_row["dau"]
        z = (dau_val - mean) / std

        severity = "normal"
        if abs(z) > 3.5:
            severity = "critical"
        elif abs(z) > 2.5:
            severity = "warning"

        if severity != "normal":
            alerts.append({
                "alert_date": current_row["stat_date"],
                "method": "zscore",
                "metric_name": "dau",
                "metric_value": float(dau_val),
                "expected_value": float(round(mean, 1)),
                "z_score": float(round(z, 2)),
                "anomaly_score": None,
                "severity": severity,
                "details": {
                    "rolling_mean": float(round(mean, 1)),
                    "rolling_std": float(round(std, 1)),
                    "direction": "spike" if z > 0 else "drop",
                    "window_days": window,
                },
            })

    return alerts


# ══════════════════════════════════════════════════════════════
#  2. Isolation Forest 行为异常检测
# ══════════════════════════════════════════════════════════════

def detect_behavior_anomaly_iforest(contamination: float = 0.05) -> list[dict]:
    """
    使用 Isolation Forest 检测多维度行为异常。

    特征维度：DAU, 登录数, 浏览数, 加购数, 支付事件数, GMV, 支付用户数, 新增用户, 订单数
    - 训练 IsolationForest 模型（contamination=0.05，即预期 5% 异常率）
    - 输出所有异常日期及其异常分数
    """
    df = load_metrics_df()

    feature_cols = [
        "dau", "login_count", "view_count", "cart_count",
        "pay_event_count", "gmv", "pay_users", "new_users", "order_count",
    ]

    X = df[feature_cols].copy()
    X = (X - X.mean()) / X.std()  # 标准化

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    preds = model.fit_predict(X)
    scores = model.decision_function(X)

    # 将分数范围 -0.6 ~ 0.6 映射到 0~1 的异常度
    score_min, score_max = scores.min(), scores.max()
    normalized = (scores - score_min) / (score_max - score_min + 1e-9)

    # 折线展示用：1-normalized 使异常值越高越异常
    anomaly_scores = 1.0 - normalized

    alerts = []
    for i in range(len(df)):
        if preds[i] == -1:  # 异常
            severity = "critical" if anomaly_scores[i] > 0.75 else "warning"
            alerts.append({
                "alert_date": df.iloc[i]["stat_date"],
                "method": "isolation_forest",
                "metric_name": "multi_metric",
                "metric_value": float(df.iloc[i]["dau"]),
                "expected_value": None,
                "z_score": None,
                "anomaly_score": float(round(anomaly_scores[i], 4)),
                "severity": severity,
                "details": {
                    "features": {
                        col: float(df.iloc[i][col]) for col in feature_cols
                    },
                    "contamination": contamination,
                    "n_estimators": 200,
                },
            })

    return alerts


# ══════════════════════════════════════════════════════════════
#  3. 结果持久化
# ══════════════════════════════════════════════════════════════

def save_alerts(alerts: list[dict], clear_old: bool = True):
    """将检测结果写入 anomaly_alerts 表"""
    import json
    db = SessionLocal()
    try:
        if clear_old:
            db.execute(text("DELETE FROM anomaly_alerts"))
            db.commit()

        insert_sql = text("""
            INSERT INTO anomaly_alerts
                (alert_date, method, metric_name, metric_value,
                 expected_value, z_score, anomaly_score, severity, details)
            VALUES
                (:alert_date, :method, :metric_name, :metric_value,
                 :expected_value, :z_score, :anomaly_score, :severity, :details)
        """)

        for a in alerts:
            db.execute(insert_sql, {
                **a,
                "details": json.dumps(a["details"], ensure_ascii=False),
            })

        db.commit()
        return len(alerts)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════
#  4. 一键运行
# ══════════════════════════════════════════════════════════════

def run_all_detection():
    """运行全部异常检测并持久化，返回汇总"""
    print("🔍 运行 Z-Score DAU 异常检测...")
    zscore_alerts = detect_dau_anomaly_zscore()

    print("🔍 运行 Isolation Forest 行为异常检测...")
    iforest_alerts = detect_behavior_anomaly_iforest()

    all_alerts = zscore_alerts + iforest_alerts
    count = save_alerts(all_alerts)

    summary = {
        "total_alerts": count,
        "zscore_count": len(zscore_alerts),
        "iforest_count": len(iforest_alerts),
        "critical": sum(1 for a in all_alerts if a["severity"] == "critical"),
        "warning": sum(1 for a in all_alerts if a["severity"] == "warning"),
    }
    print(f"✅ 保存 {count} 条告警: {summary}")
    return summary


# ══════════════════════════════════════════════════════════════
#  5. 查询接口
# ══════════════════════════════════════════════════════════════

def query_alerts(method: str | None = None, min_severity: str = "warning",
                 limit: int = 50) -> list[dict]:
    """查询已保存的告警记录"""
    import json
    db = SessionLocal()
    try:
        base = ("SELECT alert_date, method, metric_name, metric_value, "
                "expected_value, z_score, anomaly_score, severity, details "
                "FROM anomaly_alerts WHERE 1=1")

        params = {}
        if method:
            base += " AND method = :method"
            params["method"] = method

        if min_severity == "critical":
            base += " AND severity = 'critical'"
        elif min_severity == "warning":
            base += " AND severity IN ('warning', 'critical')"

        base += " ORDER BY alert_date DESC LIMIT :limit"
        params["limit"] = limit

        rows = db.execute(text(base), params).fetchall()

        severity_order = {"critical": 0, "warning": 1, "normal": 2}
        items = []
        for r in rows:
            items.append({
                "alert_date": str(r[0]),
                "method": r[1],
                "metric_name": r[2],
                "metric_value": float(r[3]),
                "expected_value": float(r[4]) if r[4] is not None else None,
                "z_score": float(r[5]) if r[5] is not None else None,
                "anomaly_score": float(r[6]) if r[6] is not None else None,
                "severity": r[7],
                "details": json.loads(r[8]) if r[8] else {},
            })

        # 按严重程度排序（critical 在前）
        items.sort(key=lambda x: severity_order.get(x["severity"], 2))
        return items
    finally:
        db.close()
