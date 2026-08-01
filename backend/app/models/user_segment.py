"""SQLAlchemy 模型 —— user_segments 用户分群结果表"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database import Base


class UserSegment(Base):
    __tablename__ = "user_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    login_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.00)
    days_since_last_active = Column(Integer, default=0)
    cluster_id = Column(Integer)
    segment = Column(String(32), index=True)
    feature_json = Column(Text, nullable=True)
    created_at = Column(DateTime)
