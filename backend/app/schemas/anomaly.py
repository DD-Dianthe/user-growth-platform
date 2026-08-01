"""异常检测 API 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ── 运行检测 ─────────────────────────────────────────────

class DetectionResponse(BaseModel):
    total_alerts: int = Field(..., description="检测到的异常总数")
    zscore_count: int = Field(..., description="Z-Score 检测异常数")
    iforest_count: int = Field(..., description="Isolation Forest 检测异常数")
    critical: int = Field(..., description="严重异常数")
    warning: int = Field(..., description="警告数")


# ── 告警记录 ─────────────────────────────────────────────

class AlertItem(BaseModel):
    alert_date: str
    method: str
    metric_name: str
    metric_value: float
    expected_value: Optional[float] = None
    z_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    severity: str
    details: dict = {}


class AlertListResponse(BaseModel):
    items: list[AlertItem]
