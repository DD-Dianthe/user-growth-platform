"""数据库连接与 Session 管理 — MySQL / SQLite 双模式"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "mysql")

if DB_TYPE == "sqlite":
    SQLITE_PATH = os.getenv(
        "SQLITE_PATH",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "user_growth.db"),
    )
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},  # SQLite 需此参数
    )
else:
    DATABASE_URL = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}"
        f":{os.getenv('MYSQL_PASSWORD', '')}"
        f"@{os.getenv('MYSQL_HOST', '127.0.0.1')}"
        f":{os.getenv('MYSQL_PORT', '3306')}"
        f"/{os.getenv('MYSQL_DATABASE', 'user_growth')}"
        f"?charset=utf8mb4"
    )
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：每个请求获取独立 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构。SQLite 模式自动建表；MySQL 模式推荐使用 DDL。
    """
    Base.metadata.create_all(bind=engine)
