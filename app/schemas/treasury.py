from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.domain.treasury import DebtStatus

class TreasuryPaymentBase(BaseModel):
    amount: float
    payment_method: str = "cash"
    reference: Optional[str] = None
    ar_id: Optional[int] = None
    ap_id: Optional[int] = None

class TreasuryPaymentCreate(TreasuryPaymentBase):
    pass

class TreasuryPaymentResponse(TreasuryPaymentBase):
    id: int
    payment_date: datetime
    model_config = ConfigDict(from_attributes=True)

class AccountsReceivableBase(BaseModel):
    sale_id: int
    customer_id: int
    total_amount: float
    remaining_amount: float
    due_date: datetime
    status: DebtStatus
    notes: Optional[str] = None

class AccountsReceivableResponse(AccountsReceivableBase):
    id: int
    created_at: datetime
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)

class AccountsPayableBase(BaseModel):
    purchase_id: int
    supplier_id: int
    total_amount: float
    remaining_amount: float
    due_date: datetime
    status: DebtStatus
    notes: Optional[str] = None

class AccountsPayableResponse(AccountsPayableBase):
    id: int
    created_at: datetime
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)
