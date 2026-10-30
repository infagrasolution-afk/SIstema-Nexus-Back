from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# ── Customer Schemas ──────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    tax_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[Decimal] = Decimal('0.0000')
    credit_days: Optional[int] = 0
    contact_person: Optional[str] = None
    notes: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    credit_days: Optional[int] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(BaseModel):
    id: int
    tax_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[Decimal] = Decimal('0.0000')
    credit_days: Optional[int] = 0
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ── Sale Detail Schemas ───────────────────────────────────────────────────────

class SaleDetailBase(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    tax_rate_id: Optional[int] = None
    discount_percent: Optional[Decimal] = Decimal('0.0000')
    discount_amount: Optional[Decimal] = Decimal('0.0000')

class SaleDetailCreate(SaleDetailBase):
    pass

class SaleDetailResponse(SaleDetailBase):
    id: int
    sale_id: int
    subtotal: Decimal
    model_config = ConfigDict(from_attributes=True)

# ── Sale Schemas ──────────────────────────────────────────────────────────────

class SaleBase(BaseModel):
    customer_id: int
    warehouse_id: Optional[int] = 1
    payment_method: Optional[str] = "cash"
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    cash_session_id: Optional[int] = None
    status: Optional[str] = "COMPLETED"
    fiscal_invoice_number: Optional[str] = None
    control_number: Optional[str] = None
    printer_serial: Optional[str] = None
    igtf_amount: Optional[Decimal] = Decimal('0.0000')
    discount_total: Optional[Decimal] = Decimal('0.0000')
    notes: Optional[str] = None

class SaleCreate(SaleBase):
    warehouse_id: int
    details: List[SaleDetailBase]

class SaleResponse(SaleBase):
    id: int
    tenant_id: int
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    created_at: datetime
    cash_session_id: Optional[int] = None
    status: str
    voided_reason: Optional[str] = None
    details: List[SaleDetailResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ── Budget Schemas ────────────────────────────────────────────────────────────

class BudgetItemBase(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal

class BudgetBase(BaseModel):
    customer_id: int
    currency: Optional[str] = "USD"
    valid_until: Optional[str] = None

class BudgetCreate(BudgetBase):
    items: List[BudgetItemBase]

class BudgetItemResponse(BudgetItemBase):
    id: int
    budget_id: int
    subtotal: Decimal
    model_config = ConfigDict(from_attributes=True)

class BudgetResponse(BudgetBase):
    id: int
    tenant_id: int
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    status: str
    created_at: datetime
    created_by_name: Optional[str] = None
    items: List[BudgetItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ── Credit Note Schemas ───────────────────────────────────────────────────────

class CreditNoteItemBase(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    tax_rate: Optional[Decimal] = Decimal('16.0000')
    tax_amount: Optional[Decimal] = Decimal('0.0000')
    total: Decimal

class CreditNoteItemCreate(CreditNoteItemBase):
    pass

class CreditNoteItemResponse(CreditNoteItemBase):
    id: int
    credit_note_id: int
    model_config = ConfigDict(from_attributes=True)

class CreditNoteCreate(BaseModel):
    sale_id: int
    customer_id: int
    reason: str
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    control_number: Optional[str] = None
    notes: Optional[str] = None
    restock_inventory: Optional[bool] = True
    items: List[CreditNoteItemCreate] = []

class CreditNoteResponse(BaseModel):
    id: int
    number: Optional[str] = None
    control_number: Optional[str] = None
    sale_id: int
    customer_id: int
    reason: str
    currency: str
    exchange_rate: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    status: str
    notes: Optional[str] = None
    created_at: datetime
    items: List[CreditNoteItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ── Debit Note Schemas ────────────────────────────────────────────────────────

class DebitNoteCreate(BaseModel):
    type: str
    customer_id: int
    amount: Decimal
    reason: str
    reference_invoice_id: Optional[int] = None
    control_number: Optional[str] = None

class DebitNoteResponse(BaseModel):
    id: int
    number: Optional[str] = None
    control_number: Optional[str] = None
    type: str
    customer_id: int
    amount: Decimal
    reason: str
    status: str
    reference_invoice_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
