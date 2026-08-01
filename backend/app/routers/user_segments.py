"""用户画像分群 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional
from app.database import get_db
from ml.user_segmentation import run as run_segmentation

router = APIRouter(prefix="/api/user-segments", tags=["用户分群"])


@router.post("/run")
def run_clustering():
    """执行 KMeans 聚类, 返回分群概览"""
    try:
        result = run_segmentation()
        return {
            "status": "ok",
            "message": f"聚类完成: {result['total_users']} 用户 → {result['segments']} 个分群",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聚类运行失败: {str(e)}")


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """获取用户分群概览统计"""
    sql = text("""
        SELECT
            segment,
            COUNT(*)              AS user_count,
            ROUND(AVG(login_count), 1)   AS avg_login,
            ROUND(AVG(view_count), 1)    AS avg_view,
            ROUND(AVG(purchase_count), 1) AS avg_purchase,
            ROUND(AVG(total_amount), 2)  AS avg_amount,
            ROUND(AVG(days_since_last_active), 1) AS avg_days_inactive,
            ROUND(SUM(total_amount), 2)  AS total_amount
        FROM user_segments
        GROUP BY segment
        ORDER BY FIELD(segment, '高价值用户','潜力用户','普通用户','流失用户')
    """)
    rows = db.execute(sql).fetchall()

    segments = []
    total_users = 0
    total_gmv = 0.0
    for row in rows:
        segments.append({
            "segment": row[0],
            "user_count": int(row[1]),
            "avg_login": float(row[2]),
            "avg_view": float(row[3]),
            "avg_purchase": float(row[4]),
            "avg_amount": float(row[5]),
            "avg_days_inactive": float(row[6]),
            "total_amount": float(row[7]),
        })
        total_users += int(row[1])
        total_gmv += float(row[7])

    return {
        "total_users": total_users,
        "total_gmv": round(total_gmv, 2),
        "segments": segments,
    }


@router.get("/detail")
def get_detail(
    segment: Optional[str] = Query(None, description="筛选用户类别"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取用户分群详情列表（支持分页和类别筛选）"""
    base = "FROM user_segments"
    count_sql = text(f"SELECT COUNT(*) {base}" + (f" WHERE segment = :seg" if segment else ""))
    params = {"seg": segment} if segment else {}

    total = db.execute(count_sql, params).scalar()

    offset = (page - 1) * page_size
    data_sql = text(
        "SELECT user_id, segment, login_count, view_count, purchase_count, "
        "ROUND(total_amount,2), days_since_last_active, cluster_id "
        f"{base}"
        + (f" WHERE segment = :seg" if segment else "")
        + " ORDER BY total_amount DESC "
        + "LIMIT :limit OFFSET :offset"
    )
    params.update({"limit": page_size, "offset": offset})
    rows = db.execute(data_sql, params).fetchall()

    items = [
        {
            "user_id": r[0], "segment": r[1], "login_count": r[2],
            "view_count": r[3], "purchase_count": r[4],
            "total_amount": float(r[5]), "days_since_last_active": r[6],
            "cluster_id": r[7],
        }
        for r in rows
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
