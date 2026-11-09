import json
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime

class TenantBase(BaseModel):
    name: str
    email: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    parent_id: Optional[int] = None
    modules: Optional[Any] = {"sales": {"is_active": True}, "inventory": {"is_active": True}, "accounting": {"is_active": True}}
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    primary_color: Optional[str] = "#2563eb"
    secondary_color: Optional[str] = "#64748b"
    settings: Optional[Any] = {}

    @field_validator('modules', 'settings', mode='before')
    @classmethod
    def parse_json_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v

class TenantUpdate(TenantBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class TenantProfileUpdate(BaseModel):
    """Campos seguros que una empresa puede editar sobre sí misma (sin alterar módulos o licencias)."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    settings: Optional[Any] = None

    @field_validator('settings', mode='before')
    @classmethod
    def parse_settings_field(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v

class TenantResponse(TenantBase):
    id: int
    license_key: Optional[str] = None
    subscription_end: Optional[datetime] = None
    is_active: Optional[bool] = True
    parent_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

TenantResponse.model_rebuild()
