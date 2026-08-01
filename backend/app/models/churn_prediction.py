"""SQLAlchemy 模型 —— churn_predictions 用户流失预测结果表"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from app.database import Base


class ChurnPrediction(Base):
    __tablename__ = "churn_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    churn_probability = Column(Float, default=0.0)
    predicted_churn = Column(Integer, default=0)
    is_high_risk = Column(Integer, default=0, index=True)
    feature_json = Column(Text, nullable=True)
    created_at = Column(DateTime)
