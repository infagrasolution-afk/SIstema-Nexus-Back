from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum

class SessionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"

class CashRegisterBase(BaseModel):
    name: str
    computer_uid: Optional[str] = None

class CashRegisterCreate(CashRegisterBase):
    pass

class CashRegister(CashRegisterBase):
    id: int
    is_active: int

    class Config:
        from_attributes = True

class CashSessionBase(BaseModel):
    register_id: int
    starting_cash: float

class CashSessionCreate(BaseModel):
    computer_uid: str
    starting_cash: float
    register_id: Optional[int] = None

class CashSessionClose(BaseModel):
    actual_cash: float

class CashSession(BaseModel):
    id: int
    register_id: int
    user_id: int
    opening_time: datetime
    closing_time: Optional[datetime] = None
    starting_cash: float
    expected_cash: float
    actual_cash: Optional[float] = None
    status: SessionStatus
    
    register: CashRegister

    class Config:
        from_attributes = True
