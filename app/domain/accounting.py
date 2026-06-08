from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class AccountType(str, enum.Enum):
    ASSET = "Activo"
    LIABILITY = "Pasivo"
    EQUITY = "Capital"
    REVENUE = "Ingreso"
    EXPENSE = "Gasto"

class Account(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # e.g. Activo, Pasivo
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

class JournalEntry(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    reference = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    
    details = relationship("JournalEntryDetail", back_populates="journal_entry", cascade="all, delete-orphan")

class JournalEntryDetail(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "journal_entry_details"
    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    
    journal_entry = relationship("JournalEntry", back_populates="details")
    account = relationship("Account")

class DebitNote(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "debit_notes"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, index=True, nullable=True)
    type = Column(String, default="Débito") # Débito or Crédito
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey('sales.id'), nullable=True) # Linked to a sale/invoice
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="UNPAID") # UNPAID, PAID
    
    # We can use string references instead of importing Sales to avoid circular dependencies
    customer = relationship("app.domain.sales.Customer")
    reference_invoice = relationship("app.domain.sales.Sale")

class BankStatement(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "bank_statements"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False) # Should be a bank account (1000)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String, default="DRAFT") # DRAFT, RECONCILED
    
    account = relationship("Account")
    lines = relationship("BankStatementLine", back_populates="statement", cascade="all, delete-orphan")

class BankStatementLine(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "bank_statement_lines"
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey('bank_statements.id', ondelete='CASCADE'), nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    amount = Column(Float, nullable=False) # Positive for deposits, negative for withdrawals
    is_reconciled = Column(Boolean, default=False)
    linked_journal_detail_id = Column(Integer, ForeignKey('journal_entry_details.id'), nullable=True)
    
    statement = relationship("BankStatement", back_populates="lines")
    linked_journal_detail = relationship("JournalEntryDetail")
