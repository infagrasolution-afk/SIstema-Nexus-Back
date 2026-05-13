from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.core.database import Base
from app.domain.base import TimestampMixin

class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    license_key = Column(String, unique=True, index=True, nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    parent_id = Column(Integer, ForeignKey('tenants.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationship to branches
    branches = relationship("Tenant", backref=backref("parent", remote_side=[id]))
