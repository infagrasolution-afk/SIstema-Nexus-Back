from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean, Enum, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class DebtStatus(str, enum.Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"

class BankAccount(Base, TimestampMixin, TenantMixin, AuditMixin):
    """Cuentas bancarias de la empresa — para conciliación y control de tesorería."""
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)  # Banesco, Mercantil, Provincial, BDV, etc.
    account_number = Column(String, nullable=False, index=True)
    account_type = Column(String, default="corriente")  # corriente, ahorro, divisas
    currency = Column(String, default="VES")  # VES, USD
    holder_name = Column(String, nullable=True)  # Titular de la cuenta
    holder_tax_id = Column(String, nullable=True)  # RIF del titular
    initial_balance = Column(Numeric(18, 4), default=0.0)
    current_balance = Column(Numeric(18, 4), default=0.0)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

class AccountsReceivable(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts_receivable"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=True)  # Nullable para CxC manuales
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Numeric(18, 4), nullable=False)
    remaining_amount = Column(Numeric(18, 4), nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(DebtStatus), default=DebtStatus.OPEN)
    notes = Column(String)
    
    sale = relationship("Sale")
    customer = relationship("Customer")
    payments = relationship("TreasuryPayment", back_populates="ar_account")

class AccountsPayable(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts_payable"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=True)  # Nullable para CxP manuales
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    total_amount = Column(Numeric(18, 4), nullable=False)
    remaining_amount = Column(Numeric(18, 4), nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(DebtStatus), default=DebtStatus.OPEN)
    notes = Column(String)
    
    purchase = relationship("Purchase")
    supplier = relationship("Supplier")
    payments = relationship("TreasuryPayment", back_populates="ap_account")

class TreasuryPayment(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "treasury_payments"
    id = Column(Integer, primary_key=True, index=True)
    ar_id = Column(Integer, ForeignKey('accounts_receivable.id'), nullable=True)
    ap_id = Column(Integer, ForeignKey('accounts_payable.id'), nullable=True)
    bank_account_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)  # Cuenta bancaria destino/origen
    amount = Column(Numeric(18, 4), nullable=False)
    payment_method = Column(String, default="cash") # cash, transfer, card, mobile, zelle, check
    reference = Column(String) # confirmation number / referencia bancaria
    payment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exchange_rate = Column(Numeric(18, 4), default=1.0)  # Tasa al momento del pago
    currency = Column(String, default="VES")
    notes = Column(Text, nullable=True)
    
    ar_account = relationship("AccountsReceivable", back_populates="payments")
    ap_account = relationship("AccountsPayable", back_populates="payments")
    bank_account = relationship("BankAccount")
