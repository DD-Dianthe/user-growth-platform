"""SQLAlchemy 模型 —— anomaly_alerts 异常告警表"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text
from app.database import Base


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_date = Column(DateTime, index=True)
    detect_time = Column(DateTime)
    method = Column(String(32), index=True)
    metric_name = Column(String(32))
    metric_value = Column(Float)
    expected_value = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    severity = Column(String(16))
    details = Column(Text, nullable=True)
