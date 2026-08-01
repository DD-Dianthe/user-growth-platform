"""异常检测 API 路由"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, Query, HTTPException
from app.schemas.anomaly import DetectionResponse, AlertListResponse

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


# ── POST /api/anomaly/detect ─────────────────────────────

@router.post("/detect", response_model=DetectionResponse)
def run_detection():
    """运行 Z-Score + Isolation Forest 异常检测，覆盖写入 anomaly_alerts 表"""
    try:
        from ml.anomaly_detection import run_all_detection
        result = run_all_detection()
        return result
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"ML 模块加载失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测运行异常: {e}")


# ── GET /api/anomaly/alerts ──────────────────────────────

@router.get("/alerts", response_model=AlertListResponse)
def get_alerts(
    method: str | None = Query(None, description="筛选方法: zscore / isolation_forest"),
    min_severity: str = Query("warning", description="最低严重级别: warning / critical"),
    limit: int = Query(50, description="最大返回条数"),
):
    """查询已保存的异常告警记录"""
    try:
        from ml.anomaly_detection import query_alerts
        items = query_alerts(method=method, min_severity=min_severity, limit=limit)
        return {"items": items}
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"ML 模块加载失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询异常: {e}")
