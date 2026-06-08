from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from datetime import datetime

class CustomerCreate(BaseModel):
    tax_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerResponse(BaseModel):
    id: int
    tax_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SaleDetailBase(BaseModel):
    product_id: int
    quantity: float
    unit_price: float
    tax_rate_id: Optional[int] = None

class SaleBase(BaseModel):
    customer_id: int
    payment_method: Optional[str] = "cash"
    currency: Optional[str] = "USD"
    exchange_rate: Optional[float] = 1.0
    cash_session_id: Optional[int] = None
    status: Optional[str] = "COMPLETED"
    fiscal_invoice_number: Optional[str] = None
    printer_serial: Optional[str] = None

class SaleCreate(SaleBase):
    warehouse_id: int
    details: List[SaleDetailBase]

class SaleDetailResponse(SaleDetailBase):
    id: int
    sale_id: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class SaleResponse(SaleBase):
    id: int
    tenant_id: int
    subtotal: float
    tax_total: float
    total: float
    created_at: datetime
    cash_session_id: Optional[int]
    status: str
    details: List[SaleDetailResponse]
    model_config = ConfigDict(from_attributes=True)

class BudgetItemBase(BaseModel):
    product_id: int
    quantity: float
    unit_price: float

class BudgetBase(BaseModel):
    customer_id: int
    currency: Optional[str] = "USD"
    valid_until: Optional[str] = None

class BudgetCreate(BudgetBase):
    items: List[BudgetItemBase]

class BudgetItemResponse(BudgetItemBase):
    id: int
    budget_id: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class BudgetResponse(BudgetBase):
    id: int
    tenant_id: int
    subtotal: float
    tax_total: float
    total: float
    status: str
    created_at: datetime
    created_by_name: Optional[str] = None
    items: List[BudgetItemResponse]
    model_config = ConfigDict(from_attributes=True)

class DebitNoteCreate(BaseModel):
    type: str
    customer_id: int
    amount: float
    reason: str
    reference_invoice_id: Optional[int] = None

class DebitNoteResponse(BaseModel):
    id: int
    number: Optional[str] = None
    type: str
    customer_id: int
    amount: float
    reason: str
    status: str
    reference_invoice_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
