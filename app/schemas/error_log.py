from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AppErrorLogCreate(BaseModel):
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[Optional[str]] = None
    error_message: str
    error_stack: Optional[str] = None
    component: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None

class AppErrorLogResponse(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    error_message: str
    error_stack: Optional[str] = None
    component: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
