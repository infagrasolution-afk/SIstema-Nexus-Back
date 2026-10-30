from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from decimal import Decimal
import enum
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

def utc_now():
    return datetime.now(timezone.utc)

class AccountType(str, enum.Enum):
    ASSET = "Activo"
    LIABILITY = "Pasivo"
    EQUITY = "Capital"
    REVENUE = "Ingreso"
    EXPENSE = "Gasto"

class JournalEntryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"

class Account(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False) # e.g. Activo, Pasivo
    balance = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    is_active = Column(Boolean, default=True)

class JournalEntry(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=utc_now, nullable=False)
    reference = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), default=JournalEntryStatus.POSTED.value, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    exchange_rate = Column(Numeric(18, 4), default=Decimal('1.0000'), nullable=False)
    
    details = relationship("JournalEntryDetail", back_populates="journal_entry", cascade="all, delete-orphan")

class JournalEntryDetail(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "journal_entry_details"
    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    debit = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    credit = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    
    journal_entry = relationship("JournalEntry", back_populates="details")
    account = relationship("Account")

class DebitNote(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "debit_notes"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), index=True, nullable=True)
    control_number = Column(String(50), nullable=True)  # Número de control fiscal SENIAT
    type = Column(String(20), default="Débito") # Débito or Crédito
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey('sales.id'), nullable=True) # Linked to a sale/invoice
    amount = Column(Numeric(18, 4), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="UNPAID") # UNPAID, PAID
    
    # String references to avoid circular dependencies
    customer = relationship("app.domain.sales.Customer")
    reference_invoice = relationship("app.domain.sales.Sale")

class BankStatement(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "bank_statements"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False) # Should be a bank account (1000)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String(20), default="DRAFT") # DRAFT, RECONCILED
    
    account = relationship("Account")
    lines = relationship("BankStatementLine", back_populates="statement", cascade="all, delete-orphan")

class BankStatementLine(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "bank_statement_lines"
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey('bank_statements.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String(255), nullable=False)
    reference = Column(String(100), nullable=True)
    amount = Column(Numeric(18, 4), nullable=False) # Positive for deposits, negative for withdrawals
    is_reconciled = Column(Boolean, default=False)
    linked_journal_detail_id = Column(Integer, ForeignKey('journal_entry_details.id'), nullable=True)
    
    statement = relationship("BankStatement", back_populates="lines")
    linked_journal_detail = relationship("JournalEntryDetail")
