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


class CustomerBasicResponse(BaseModel):
    id: int
    name: str
    tax_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SupplierBasicResponse(BaseModel):
    id: int
    name: str
    tax_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AccountsReceivableCreate(BaseModel):
    sale_id: Optional[int] = None  # Opcional para CxC manuales
    customer_id: int
    total_amount: float
    due_date: datetime
    notes: Optional[str] = None

class AccountsReceivableBase(BaseModel):
    sale_id: Optional[int] = None
    customer_id: int
    total_amount: float
    remaining_amount: float
    due_date: datetime
    status: DebtStatus
    notes: Optional[str] = None

class AccountsReceivableResponse(AccountsReceivableBase):
    id: int
    created_at: datetime
    customer: Optional[CustomerBasicResponse] = None
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)


class AccountsPayableCreate(BaseModel):
    purchase_id: Optional[int] = None  # Opcional para CxP manuales
    supplier_id: int
    total_amount: float
    due_date: datetime
    notes: Optional[str] = None

class AccountsPayableBase(BaseModel):
    purchase_id: Optional[int] = None
    supplier_id: int
    total_amount: float
    remaining_amount: float
    due_date: datetime
    status: DebtStatus
    notes: Optional[str] = None

class AccountsPayableResponse(AccountsPayableBase):
    id: int
    created_at: datetime
    supplier: Optional[SupplierBasicResponse] = None
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)
