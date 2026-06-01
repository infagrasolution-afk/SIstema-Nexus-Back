from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class AppErrorLog(Base):
    __tablename__ = "app_error_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    error_message = Column(Text, nullable=False)
    error_stack = Column(Text, nullable=True)
    component = Column(String, nullable=True)
    url = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
