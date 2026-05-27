from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    modules: Optional[str] = None


class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    tenant_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
