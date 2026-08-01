"""Dashboard API 路由"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import (
    DashboardResponse,
    FunnelResponse,
    RetentionResponse,
    TrendResponse,
    SourceResponse,
)
from app.services.dashboard import (
    get_dashboard_overview,
    get_funnel,
    get_retention,
    get_trends,
    get_source_distribution,
)

router = APIRouter(prefix="/api", tags=["Dashboard"])


# ── GET /api/dashboard ────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    target_date: date | None = Query(None, description="目标日期，默认最新有数据的日期"),
    db: Session = Depends(get_db),
):
    """核心指标概览：DAU / 新增用户 / GMV / 支付用户 / 转化率"""
    result = get_dashboard_overview(db, target_date)
    if result is None:
        raise HTTPException(status_code=404, detail="暂无数据")
    return result


# ── GET /api/funnel ───────────────────────────────────────

@router.get("/funnel", response_model=FunnelResponse)
def funnel(
    start_date: date | None = Query(None, description="开始日期 (默认最近30天)"),
    end_date: date | None = Query(None, description="结束日期 (默认最新)"),
    db: Session = Depends(get_db),
):
    """用户转化漏斗：浏览 → 加购 → 支付"""
    return get_funnel(db, start_date, end_date)


# ── GET /api/retention ────────────────────────────────────

@router.get("/retention", response_model=RetentionResponse)
def retention(
    start_date: date | None = Query(None, description="开始日期 (默认最近30天)"),
    end_date: date | None = Query(None, description="结束日期 (默认最新)"),
    db: Session = Depends(get_db),
):
    """按日留存分析：次日留存 & 7 日留存"""
    return get_retention(db, start_date, end_date)


# ── GET /api/trends ────────────────────────────────────────

@router.get("/trends", response_model=TrendResponse)
def trends(
    start_date: date | None = Query(None, description="开始日期 (默认最近30天)"),
    end_date: date | None = Query(None, description="结束日期 (默认最新)"),
    db: Session = Depends(get_db),
):
    """DAU & GMV 日趋势数据（折线图用）"""
    return get_trends(db, start_date, end_date)


# ── GET /api/source ────────────────────────────────────────

@router.get("/source", response_model=SourceResponse)
def source_distribution(db: Session = Depends(get_db)):
    """用户来源渠道分布（饼图/玫瑰图用）"""
    return get_source_distribution(db)
