from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TenantBase(BaseModel):
    name: str
    email: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    parent_id: Optional[int] = None
    modules: Optional[dict] = {"sales": {"is_active": True}, "inventory": {"is_active": True}, "accounting": {"is_active": True}}
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    primary_color: Optional[str] = "#2563eb"
    secondary_color: Optional[str] = "#64748b"
    settings: Optional[dict] = {}


class TenantUpdate(TenantBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(TenantBase):
    id: int
    license_key: Optional[str] = None
    subscription_end: Optional[datetime] = None
    is_active: Optional[bool] = True
    parent_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

TenantResponse.model_rebuild()
