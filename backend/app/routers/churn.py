"""用户流失预测 API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional
from app.database import get_db
from ml.churn_prediction import run as run_churn_prediction

router = APIRouter(prefix="/api/churn", tags=["流失预测"])


@router.post("/run")
def run_prediction():
    """运行 XGBoost 训练 + 全量预测"""
    try:
        result = run_churn_prediction()
        metrics = result["model_metrics"]
        summary = result["summary"]
        return {
            "status": "ok",
            "message": f"训练完成: AUC={metrics['auc']}, "
                       f"高风险 {summary['high_risk_users']:,} 人",
            "model_metrics": metrics,
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流失预测运行失败: {str(e)}")


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """流失风险概览统计"""
    sql = text("""
        SELECT
            COUNT(*)                           AS total_users,
            SUM(predicted_churn)               AS predicted_churn,
            SUM(is_high_risk)                  AS high_risk,
            ROUND(AVG(churn_probability), 4)   AS avg_probability,
            ROUND(MAX(churn_probability), 4)   AS max_probability,
            ROUND(MIN(churn_probability), 4)   AS min_probability
        FROM churn_predictions
    """)
    row = db.execute(sql).fetchone()

    # 按概率分段分布
    dist_sql = text("""
        SELECT
            CASE
                WHEN churn_probability >= 0.8 THEN '80-100%'
                WHEN churn_probability >= 0.6 THEN '60-80%'
                WHEN churn_probability >= 0.4 THEN '40-60%'
                WHEN churn_probability >= 0.2 THEN '20-40%'
                ELSE '0-20%'
            END AS probability_bucket,
            COUNT(*) AS user_count,
            ROUND(AVG(churn_probability), 4) AS avg_prob
        FROM churn_predictions
        GROUP BY probability_bucket
        ORDER BY MIN(churn_probability) DESC
    """)
    dist = [dict(r._mapping) for r in db.execute(dist_sql).fetchall()]

    # 高风险用户中的特征画像
    profile_sql = text("""
        SELECT
            cp.is_high_risk,
            COUNT(*)                                                     AS user_count,
            ROUND(AVG(us.login_count), 1)                               AS avg_login,
            ROUND(AVG(us.view_count), 1)                                AS avg_view,
            ROUND(AVG(us.purchase_count), 1)                            AS avg_purchase,
            ROUND(AVG(us.total_amount), 2)                              AS avg_amount,
            ROUND(AVG(us.days_since_last_active), 1)                    AS avg_days_inactive
        FROM churn_predictions cp
        LEFT JOIN user_segments us ON cp.user_id = us.user_id
        GROUP BY cp.is_high_risk
        ORDER BY cp.is_high_risk DESC
    """)
    profile = [dict(r._mapping) for r in db.execute(profile_sql).fetchall()]

    return {
        "overview": dict(row._mapping),
        "distribution": dist,
        "profile": profile,
    }


@router.get("/high-risk")
def get_high_risk_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("probability", pattern="^(probability|user_id)$"),
    db: Session = Depends(get_db),
):
    """获取高风险用户列表 (流失概率 > 0.7)"""
    order_col = "cp.churn_probability DESC" if sort_by == "probability" else "cp.user_id ASC"

    count_sql = text("SELECT COUNT(*) FROM churn_predictions WHERE is_high_risk = 1")
    total = db.execute(count_sql).scalar()

    sql = text(f"""
        SELECT
            cp.user_id,
            cp.churn_probability,
            cp.predicted_churn,
            cp.is_high_risk,
            cp.created_at                                            AS predicted_at,
            COALESCE(us.login_count, 0)                              AS login_count,
            COALESCE(us.view_count, 0)                               AS view_count,
            COALESCE(us.purchase_count, 0)                           AS purchase_count,
            COALESCE(us.total_amount, 0)                             AS total_amount,
            COALESCE(us.days_since_last_active, 0)                   AS days_inactive,
            COALESCE(us.segment, 'unknown')                          AS segment
        FROM churn_predictions cp
        LEFT JOIN user_segments us ON cp.user_id = us.user_id
        WHERE cp.is_high_risk = 1
        ORDER BY {order_col}
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(sql, {"limit": limit, "offset": offset}).fetchall()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [dict(r._mapping) for r in rows],
    }
