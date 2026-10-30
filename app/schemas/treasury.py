from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.domain.treasury import DebtStatus

# ── Bank Account Schemas ──────────────────────────────────────────────────────

class BankAccountBase(BaseModel):
    bank_name: str
    account_number: str
    account_type: Optional[str] = "Corriente"
    currency: Optional[str] = "USD"
    initial_balance: Optional[Decimal] = Decimal('0.0000')
    is_active: Optional[bool] = True
    notes: Optional[str] = None

class BankAccountCreate(BankAccountBase):
    pass

class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class BankAccountResponse(BankAccountBase):
    id: int
    current_balance: Decimal
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ── Treasury Payment Schemas ──────────────────────────────────────────────────

class TreasuryPaymentBase(BaseModel):
    amount: Decimal
    payment_method: str = "cash"
    reference: Optional[str] = None
    bank_account_id: Optional[int] = None
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    notes: Optional[str] = None
    ar_id: Optional[int] = None
    ap_id: Optional[int] = None

class TreasuryPaymentCreate(TreasuryPaymentBase):
    pass

class TreasuryPaymentResponse(TreasuryPaymentBase):
    id: int
    payment_date: datetime
    model_config = ConfigDict(from_attributes=True)

# ── Customer / Supplier Basic ─────────────────────────────────────────────────

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

# ── Accounts Receivable (CxC) ─────────────────────────────────────────────────

class AccountsReceivableCreate(BaseModel):
    sale_id: Optional[int] = None  # Opcional para CxC manuales
    customer_id: int
    total_amount: Decimal
    due_date: datetime
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    notes: Optional[str] = None

class AccountsReceivableBase(BaseModel):
    sale_id: Optional[int] = None
    customer_id: int
    total_amount: Decimal
    remaining_amount: Decimal
    paid_amount: Optional[Decimal] = Decimal('0.0000')
    due_date: datetime
    status: DebtStatus
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    notes: Optional[str] = None

class AccountsReceivableResponse(AccountsReceivableBase):
    id: int
    created_at: datetime
    customer: Optional[CustomerBasicResponse] = None
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)

# ── Accounts Payable (CxP) ────────────────────────────────────────────────────

class AccountsPayableCreate(BaseModel):
    purchase_id: Optional[int] = None  # Opcional para CxP manuales
    supplier_id: int
    total_amount: Decimal
    due_date: datetime
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    notes: Optional[str] = None

class AccountsPayableBase(BaseModel):
    purchase_id: Optional[int] = None
    supplier_id: int
    total_amount: Decimal
    remaining_amount: Decimal
    paid_amount: Optional[Decimal] = Decimal('0.0000')
    due_date: datetime
    status: DebtStatus
    currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = Decimal('1.0000')
    notes: Optional[str] = None

class AccountsPayableResponse(AccountsPayableBase):
    id: int
    created_at: datetime
    supplier: Optional[SupplierBasicResponse] = None
    payments: List[TreasuryPaymentResponse] = []
    model_config = ConfigDict(from_attributes=True)
