from typing import Optional, List
from pydantic import BaseModel

class PermissionBase(BaseModel):
    code: str
    description: Optional[str] = None
    module: str

class PermissionResponse(PermissionBase):
    id: int
    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: List[int] = []

class RoleUpdate(RoleBase):
    permission_ids: Optional[List[int]] = None

class RoleResponse(RoleBase):
    id: int
    is_system_role: bool
    permissions: List[PermissionResponse] = []
    class Config:
        from_attributes = True
