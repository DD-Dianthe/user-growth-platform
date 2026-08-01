"""用户流失预测 —— XGBoost 二分类

业务定义: 连续30天没有登录 → 流失 (churn=1)

算法流程:
1. 从 MySQL 提取用户行为特征 (注册天数/登录/浏览/购买/金额/最近活跃)
2. 构造训练标签: days_since_last_active > 30 → churned=1
3. Train/test split 70/30
4. XGBoost 训练 + 评估 (Accuracy/Precision/Recall/AUC)
5. 全量预测并写入 churn_predictions 表
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    roc_auc_score, classification_report, confusion_matrix
)
from xgboost import XGBClassifier
from sqlalchemy import text
from backend.app.database import engine, SessionLocal

# ── 模型保存路径 ──
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "churn_model.json")

# 流失阈值: 30天
CHURN_DAYS = 30

# ══════════════════════════════════════════════════════════════
#  Section 1: 特征提取 + 标签构造
# ══════════════════════════════════════════════════════════════

def extract_features() -> pd.DataFrame:
    """从 MySQL 提取全部用户的 RFM 特征 + 流失标签"""
    sql = text("""
        WITH user_stats AS (
            -- 行为统计 (以最新事件时间为参考)
            SELECT
                u.user_id,
                DATEDIFF(CURDATE(), DATE(u.registration_time)) AS tenure_days,
                COUNT(DISTINCT CASE WHEN e.event_type = 'login' THEN e.id END) AS login_count,
                COUNT(DISTINCT CASE WHEN e.event_type = 'view_product' THEN e.id END) AS view_count,
                COUNT(DISTINCT CASE WHEN e.event_type = 'add_cart' THEN e.id END) AS add_cart_count,
                DATEDIFF(CURDATE(), DATE(COALESCE(MAX(e.event_time), u.registration_time))) AS days_since_last_active,
                COALESCE(AVG(CASE WHEN e.duration_ms > 0 THEN e.duration_ms END), 0) AS avg_duration_ms
            FROM users u
            LEFT JOIN user_events e ON u.user_id = e.user_id
            GROUP BY u.user_id, u.registration_time
        ),
        order_stats AS (
            SELECT
                user_id,
                COUNT(o.order_id) AS purchase_count,
                COALESCE(SUM(o.amount), 0) AS total_amount,
                COALESCE(AVG(o.amount), 0) AS avg_order_amount,
                CASE
                    WHEN COUNT(o.order_id) > 0
                    THEN DATEDIFF(CURDATE(), DATE(MIN(o.pay_time)))
                    ELSE 9999
                END AS days_since_first_order,
                CASE
                    WHEN COUNT(o.order_id) > 0
                    THEN CAST(COUNT(o.order_id) AS FLOAT) / NULLIF(DATEDIFF(CURDATE(), DATE(MIN(o.pay_time))), 0)
                    ELSE 0
                END AS purchase_frequency
            FROM orders o
            WHERE o.order_status = 'completed'
            GROUP BY o.user_id
        )
        SELECT
            us.user_id,
            us.tenure_days,
            us.login_count,
            us.view_count,
            us.add_cart_count,
            us.days_since_last_active,
            us.avg_duration_ms,
            COALESCE(os.purchase_count, 0) AS purchase_count,
            COALESCE(os.total_amount, 0) AS total_amount,
            COALESCE(os.avg_order_amount, 0) AS avg_order_amount,
            COALESCE(os.days_since_first_order, 9999) AS days_since_first_order,
            COALESCE(os.purchase_frequency, 0) AS purchase_frequency,
            -- ★ 标签: 30天无登录 = 流失
            CASE WHEN us.days_since_last_active > :churn_days THEN 1 ELSE 0 END AS churned
        FROM user_stats us
        LEFT JOIN order_stats os ON us.user_id = os.user_id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"churn_days": CHURN_DAYS})
    return df


# ══════════════════════════════════════════════════════════════
#  Section 2: 特征工程 (衍生特征 + 标准化)
# ══════════════════════════════════════════════════════════════

def engineer_features(df: pd.DataFrame) -> tuple:
    """特征工程: 衍生比率特征 + 标准化, 返回 (X, 特征列名列表)"""

    # 衍生特征
    df["login_rate"] = df["login_count"] / (df["tenure_days"] + 1)              # 日均登录率
    df["view_rate"] = df["view_count"] / (df["tenure_days"] + 1)                # 日均浏览率
    df["cart_rate"] = df["add_cart_count"] / (df["view_count"] + 1)             # 浏览→加购转化
    df["purchase_rate"] = df["purchase_count"] / (df["login_count"] + 1)        # 登录→购买转化
    df["buyer_flag"] = (df["purchase_count"] > 0).astype(int)                   # 是否购买过

    # 金额归一化 (log 变换, 避免极端值)
    df["log_total_amount"] = np.log1p(df["total_amount"])
    df["log_avg_order_amount"] = np.log1p(df["avg_order_amount"])
    df["log_avg_duration"] = np.log1p(df["avg_duration_ms"])

    # ── 最终特征集 (原始 + 衍生) ──
    feature_cols = [
        "tenure_days",           # 注册天数 → 用户生命长度
        "login_count",           # 登录次数 → 活跃度
        "view_count",            # 浏览次数 → 兴趣度
        "add_cart_count",        # 加购次数 → 购买意向
        "days_since_last_active",# 最近活跃 → 流失核心信号
        "purchase_count",        # 购买次数 → 忠诚度
        "total_amount",          # 总消费 → 价值
        "avg_order_amount",      # 客单价
        "purchase_frequency",    # 购买频率
        # 衍生特征
        "login_rate",
        "view_rate",
        "cart_rate",
        "purchase_rate",
        "buyer_flag",
        "log_total_amount",
        "log_avg_order_amount",
        "log_avg_duration",
    ]

    X = df[feature_cols].copy().fillna(0)
    feature_names = list(X.columns)

    return X, df["churned"].values, feature_names


# ══════════════════════════════════════════════════════════════
#  Section 3: XGBoost 训练 + 评估
# ══════════════════════════════════════════════════════════════

def train_and_evaluate(X, y, feature_names) -> dict:
    """训练 XGBoost 模型并返回评估指标"""

    # Train/test split (imbalanced → stratify)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # 计算正样本权重 (处理类别不平衡)
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1

    print(f"\n训练集: {len(X_train)} | 测试集: {len(X_test)}")
    print(f"流失比例: train={n_pos}/{len(y_train)} ({n_pos/len(y_train)*100:.1f}%)")
    print(f"scale_pos_weight = {scale_pos_weight:.1f}")

    # ── XGBoost 模型 ──
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        gamma=0.1,
        reg_alpha=0.5,
        reg_lambda=1.0,
        random_state=42,
        eval_metric="logloss",
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── 预测 + 评估 ──
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "auc": round(roc_auc_score(y_test, y_proba), 4),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "churn_rate_train": round(n_pos / len(y_train), 4),
    }

    # ── 混淆矩阵 ──
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    metrics["confusion_matrix"] = {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)}

    # ── 特征重要性 ──
    importance = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    metrics["top_features"] = [
        {"feature": f, "importance": float(round(v, 4))} for f, v in importance[:10]
    ]

    # 5-fold CV
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="roc_auc",
    )
    metrics["cv_auc_mean"] = round(cv_scores.mean(), 4)
    metrics["cv_auc_std"] = round(cv_scores.std(), 4)

    return metrics, model, feature_names


# ══════════════════════════════════════════════════════════════
#  Section 4: 全量预测 + 入库
# ══════════════════════════════════════════════════════════════

def predict_all(model, X_all, user_ids, feature_names) -> pd.DataFrame:
    """全量预测并返回 DataFrame"""
    probas = model.predict_proba(X_all)[:, 1]
    preds = model.predict(X_all)

    results = pd.DataFrame({
        "user_id": user_ids,
        "churn_probability": probas.round(4),
        "predicted_churn": preds.astype(int),
        "is_high_risk": (probas > 0.7).astype(int),  # >70% 为高风险
    })
    return results


def save_to_db(results: pd.DataFrame, feature_importance: dict):
    """将预测结果写入 churn_predictions 表"""
    session = SessionLocal()
    try:
        # 清空旧数据
        session.execute(text("TRUNCATE TABLE churn_predictions"))
        session.commit()

        # 批量插入
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_sql = text("""
            INSERT INTO churn_predictions
                (user_id, churn_probability, predicted_churn, is_high_risk, feature_json, created_at)
            VALUES (:uid, :prob, :pred, :risk, :feat, :ts)
        """)

        records = []
        for _, row in results.iterrows():
            records.append({
                "uid": int(row["user_id"]),
                "prob": float(row["churn_probability"]),
                "pred": int(row["predicted_churn"]),
                "risk": int(row["is_high_risk"]),
                "feat": json.dumps(feature_importance[:5]),
                "ts": now,
            })

        session.execute(insert_sql, records)
        session.commit()
        print(f"✓ {len(records)} 条预测结果写入 churn_predictions")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ══════════════════════════════════════════════════════════════
#  Section 5: 主流程
# ══════════════════════════════════════════════════════════════

def run() -> dict:
    """完整执行: 特征提取 → 训练 → 评估 → 全量预测 → 入库"""

    print("=" * 56)
    print("  用户流失预测 —— XGBoost 二分类")
    print("  流失定义: 连续30天无登录")
    print("=" * 56)

    # Step 1: 特征提取
    print("\n[1/5] 提取用户特征...")
    df = extract_features()
    print(f"  提取用户: {len(df):,} | 流失: {df['churned'].sum():,} "
          f"({df['churned'].sum()/len(df)*100:.1f}%)")

    # Step 2: 特征工程
    print("\n[2/5] 特征工程 (衍生特征 + 标准化)...")
    X, y, feature_names = engineer_features(df)
    print(f"  特征维度: {len(feature_names)}  |  特征: {feature_names[:6]}...")

    # Step 3: 训练 + 评估
    print("\n[3/5] XGBoost 训练...")
    metrics, model, feature_names = train_and_evaluate(X, y, feature_names)

    print("\n  模型评估:")
    print(f"    Accuracy  : {metrics['accuracy']}")
    print(f"    Precision : {metrics['precision']}")
    print(f"    Recall    : {metrics['recall']}")
    print(f"    AUC       : {metrics['auc']}")
    print(f"    CV AUC    : {metrics['cv_auc_mean']:.4f} ± {metrics['cv_auc_std']:.4f}")
    print(f"\n  混淆矩阵:")
    cm = metrics["confusion_matrix"]
    print(f"    TP={cm['tp']:>6}  FP={cm['fp']:>6}")
    print(f"    FN={cm['fn']:>6}  TN={cm['tn']:>6}")

    print(f"\n  Top-5 特征重要性:")
    for f in metrics["top_features"][:5]:
        print(f"    {f['feature']:28s}  {f['importance']:.4f}")

    # Step 4: 全量预测
    print("\n[4/5] 全量预测...")
    results = predict_all(model, X, df["user_id"].values, feature_names)
    high_risk = results["is_high_risk"].sum()
    print(f"  高风险用户 (概率>70%): {high_risk:,} ({high_risk/len(results)*100:.1f}%)")
    print(f"  平均流失概率: {results['churn_probability'].mean():.4f}")

    # Step 5: 保存
    print("\n[5/5] 保存模型 + 写入数据库...")
    model.save_model(MODEL_PATH)
    print(f"  模型 → {MODEL_PATH}")
    save_to_db(results, metrics["top_features"])

    print(f"\n{'='*56}")
    print(f"  完成! 模型已保存, 预测结果已入库")
    print(f"{'='*56}")

    return {
        "model_metrics": metrics,
        "summary": {
            "total_users": len(results),
            "predicted_churn": int(results["predicted_churn"].sum()),
            "high_risk_users": int(high_risk),
            "avg_churn_probability": float(results["churn_probability"].mean().round(4)),
        },
    }


if __name__ == "__main__":
    run()
