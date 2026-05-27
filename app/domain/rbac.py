from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class Role(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_system_role = Column(Boolean, default=False) # Roles that cannot be deleted
    
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"
    # Note: Permissions are global and defined by the system, not per tenant.
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False) # e.g. "sales:create"
    description = Column(String, nullable=True)
    module = Column(String, nullable=False) # e.g. "sales", "inventory"
    
    role_permissions = relationship("RolePermission", back_populates="permission")

class RolePermission(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uix_role_permission'),
    )

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")
