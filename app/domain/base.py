from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declared_attr

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TenantMixin:
    @declared_attr
    def tenant_id(cls):
        return Column(Integer, ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
