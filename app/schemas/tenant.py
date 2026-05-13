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

class TenantUpdate(TenantBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(TenantBase):
    id: int
    license_key: Optional[str] = None
    subscription_end: Optional[datetime] = None
    is_active: bool
    parent_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

TenantResponse.model_rebuild()
