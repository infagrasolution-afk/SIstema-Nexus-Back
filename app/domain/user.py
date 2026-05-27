from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class User(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    modules = Column(String, nullable=True) # e.g. "sales,inventory"
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)

    role = relationship("Role", back_populates="users")

