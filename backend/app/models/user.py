"""SQLAlchemy 数据模型 —— 对应 users / user_events / orders 三表"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    age = Column(Integer)
    gender = Column(String(4))
    city = Column(String(32))
    device_type = Column(String(16))
    registration_time = Column(DateTime, index=True)
    channel = Column(String(32))


class UserEvent(Base):
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True)
    event_type = Column(String(32), index=True)
    event_time = Column(DateTime, index=True)
    session_id = Column(String(64))
    page_url = Column(String(256))
    duration_ms = Column(Integer)


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    product_category = Column(String(32))
    order_status = Column(String(16))
    is_first_order = Column(Boolean)
    pay_time = Column(DateTime, index=True)
