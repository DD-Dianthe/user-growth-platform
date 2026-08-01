"""FastAPI 主入口"""

import sys, os
# 将项目根目录加入 sys.path，以便 ml/ 等模块可被导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.routers.dashboard import router as dashboard_router
from app.routers.anomaly import router as anomaly_router
from app.routers.user_segments import router as user_segments_router
from app.routers.churn import router as churn_router
from app.routers.upload import router as upload_router
from app.routers.auto_analyze import router as auto_analyze_router

# 启动时初始化数据库
init_db()

app = FastAPI(
    title="用户增长智能分析平台",
    description="BI 看板 / 自助上传分析 / 异常检测 / 流失预测 / 用户分群 / ML",
    version="0.1.0",
)

# CORS —— 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(anomaly_router)
app.include_router(user_segments_router)
app.include_router(churn_router)
app.include_router(upload_router)
app.include_router(auto_analyze_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# ── 生产环境：托管前端静态文件 ──
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
STATIC_ACTIVE = os.path.isdir(STATIC_DIR) and os.path.isfile(os.path.join(STATIC_DIR, "index.html"))

if STATIC_ACTIVE:
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")


@app.get("/")
def root():
    """首页：有静态文件时返回 SPA 入口，否则返回 API 信息"""
    if STATIC_ACTIVE:
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
    return {"app": "用户增长智能分析平台", "docs": "/docs"}
