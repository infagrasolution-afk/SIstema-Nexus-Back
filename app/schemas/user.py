from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.rbac import RoleResponse, PermissionResponse


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    modules: Optional[str] = None   # Módulos del tenant que puede ver: "sales,inventory"


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None                    # ← Asignar rol existente
    permission_ids: Optional[List[int]] = None       # ← Permisos directos adicionales


class UserUpdate(BaseModel):
    """Schema para actualización parcial de usuario."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    modules: Optional[str] = None
    role_id: Optional[int] = None
    permission_ids: Optional[List[int]] = None


class UserResponse(UserBase):
    id: int
    tenant_id: int
    role_id: Optional[int] = None
    created_at: datetime

    # Estado de bloqueo de cuenta
    is_locked: Optional[bool] = False
    login_attempts: Optional[int] = 0
    locked_at: Optional[datetime] = None

    # Datos del rol y permisos (cargados en el endpoint)
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)
