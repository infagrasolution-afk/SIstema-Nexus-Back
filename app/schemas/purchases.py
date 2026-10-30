from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.domain.purchases import PurchaseStatus

# ── Supplier Schemas ──────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_days: Optional[int] = 0
    is_withholding_agent: Optional[bool] = False
    notes: Optional[str] = None

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_days: Optional[int] = None
    is_withholding_agent: Optional[bool] = None
    notes: Optional[str] = None

class SupplierBasicResponse(BaseModel):
    id: int
    name: str
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SupplierResponse(SupplierCreate):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ── Purchase Detail Schemas ───────────────────────────────────────────────────

class PurchaseDetailBase(BaseModel):
    product_id: int
    quantity: Decimal
    cost_price: Decimal

class PurchaseDetailResponse(PurchaseDetailBase):
    id: int
    subtotal: Decimal
    received_quantity: Decimal = Decimal('0.0000')
    model_config = ConfigDict(from_attributes=True)

# ── Purchase Schemas ──────────────────────────────────────────────────────────

class PurchaseCreate(BaseModel):
    supplier_id: int
    warehouse_id: int = 1
    invoice_number: Optional[str] = None
    control_number: Optional[str] = None
    reference: Optional[str] = None
    payment_method: str = "cash"
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    iva_withholding: Optional[Decimal] = Decimal('0.0000')
    islr_withholding: Optional[Decimal] = Decimal('0.0000')
    notes: Optional[str] = None
    draft: bool = False  # Si True, crea en estado DRAFT; si False, completa directamente
    details: List[PurchaseDetailBase]

class PurchaseUpdate(BaseModel):
    invoice_number: Optional[str] = None
    control_number: Optional[str] = None
    reference: Optional[str] = None
    payment_method: Optional[str] = None
    currency: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    iva_withholding: Optional[Decimal] = None
    islr_withholding: Optional[Decimal] = None
    notes: Optional[str] = None

class PurchaseReceiveItem(BaseModel):
    product_id: int
    received_quantity: Decimal  # Cantidad realmente recibida (puede ser parcial)

class PurchaseReceiveIn(BaseModel):
    warehouse_id: int
    items: Optional[List[PurchaseReceiveItem]] = None  # Si None, se reciben todas las líneas completas
    notes: Optional[str] = None

class PurchaseResponse(BaseModel):
    id: int
    supplier_id: int
    supplier: Optional[SupplierBasicResponse] = None
    warehouse_id: Optional[int] = 1
    invoice_number: Optional[str] = None
    control_number: Optional[str] = None
    status: PurchaseStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    iva_withholding: Decimal = Decimal('0.0000')
    islr_withholding: Decimal = Decimal('0.0000')
    currency: str = "USD"
    exchange_rate: Decimal = Decimal('1.0000')
    reference: Optional[str] = None
    payment_method: str
    notes: Optional[str] = None
    created_at: datetime
    details: List[PurchaseDetailResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
