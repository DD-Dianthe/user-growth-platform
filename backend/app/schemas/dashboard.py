"""Dashboard API 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ── 请求参数 ───────────────────────────────────────────────

class DateRangeQuery(BaseModel):
    """通用日期范围查询，默认取最近 30 天"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# ── Dashboard 概览 ─────────────────────────────────────────

class DashboardOverview(BaseModel):
    """BI 看板核心指标卡片"""
    dau: int = Field(..., description="日活跃用户数")
    new_users: int = Field(..., description="当日新增用户")
    gmv: float = Field(..., description="当日交易总额 (GMV)")
    paying_users: int = Field(..., description="当日支付用户数")
    conversion_rate: float = Field(..., description="支付转化率 (支付人数/浏览人数)")


class DashboardResponse(BaseModel):
    date: date
    overview: DashboardOverview


# ── 漏斗 ───────────────────────────────────────────────────

class FunnelStep(BaseModel):
    step: str = Field(..., description="漏斗步骤名称")
    count: int = Field(..., description="人数")
    rate: Optional[float] = Field(None, description="相对上一步的转化率")


class FunnelResponse(BaseModel):
    steps: list[FunnelStep]
    overall_rate: float = Field(..., description="首步→末步整体转化率")


# ── 留存 ──────────────────────────────────────────────────

class RetentionItem(BaseModel):
    """单日留存"""
    date: date
    new_users: int
    day1_retention: Optional[float] = Field(None, description="次日留存率")
    day7_retention: Optional[float] = Field(None, description="7 日留存率")


class RetentionResponse(BaseModel):
    items: list[RetentionItem]


# ── 趋势数据 ────────────────────────────────────────────────

class TrendItem(BaseModel):
    date: date
    dau: int
    gmv: float


class TrendResponse(BaseModel):
    items: list[TrendItem]


# ── 来源分布 ────────────────────────────────────────────────

class SourceItem(BaseModel):
    channel: str
    count: int


class SourceResponse(BaseModel):
    items: list[SourceItem]
