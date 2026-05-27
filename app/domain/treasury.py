from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class DebtStatus(str, enum.Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"

class AccountsReceivable(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts_receivable"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(DebtStatus), default=DebtStatus.OPEN)
    notes = Column(String)
    
    sale = relationship("Sale")
    customer = relationship("Customer")
    payments = relationship("TreasuryPayment", back_populates="ar_account")

class AccountsPayable(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts_payable"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
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
    amount = Column(Float, nullable=False)
    payment_method = Column(String, default="cash") # cash, transfer, card
    reference = Column(String) # confirmation number
    payment_date = Column(DateTime, default=datetime.utcnow)
    
    ar_account = relationship("AccountsReceivable", back_populates="payments")
    ap_account = relationship("AccountsPayable", back_populates="payments")
