from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin
from app.domain.inventory import Product
from app.domain.cash import CashSession

class Customer(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String)
    phone = Column(String)
    tax_id = Column(String)
    address = Column(String, nullable=True)

class TaxRate(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "tax_rates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rate = Column(Float, nullable=False)

class Sale(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    subtotal = Column(Float, nullable=False)
    tax_total = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    payment_method = Column(String, default="cash") # cash, card, transfer
    currency = Column(String, default="USD")
    exchange_rate = Column(Float, default=1.0)
    cash_session_id = Column(Integer, ForeignKey('cash_sessions.id'), nullable=True)
    is_accounted = Column(Boolean, default=False)
    status = Column(String, default="COMPLETED") # COMPLETED, ON_HOLD, CANCELLED
    fiscal_invoice_number = Column(String, nullable=True)
    printer_serial = Column(String, nullable=True)
    
    customer = relationship("Customer")
    tenant = relationship("app.domain.tenant.Tenant")
    cash_session = relationship("CashSession", back_populates="sales")
    details = relationship("SaleDetail", back_populates="sale")

class SaleDetail(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "sale_details"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    tax_rate_id = Column(Integer, ForeignKey('tax_rates.id'), nullable=True)
    subtotal = Column(Float, nullable=False)
    
    sale = relationship("Sale", back_populates="details")
    product = relationship("Product")
    tax_rate = relationship("TaxRate")

class Budget(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    subtotal = Column(Float, nullable=False)
    tax_total = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED
    valid_until = Column(String, nullable=True) # or DateTime
    
    customer = relationship("Customer")
    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")

class BudgetItem(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "budget_items"
    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    budget = relationship("Budget", back_populates="items")
    product = relationship("Product")

class DeliveryNote(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "delivery_notes"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=True)
    status = Column(String, default="DRAFT") # DRAFT, DISPATCHED, DELIVERED
    delivery_address = Column(String, nullable=True)
    
    customer = relationship("Customer")
    sale = relationship("Sale")
    items = relationship("DeliveryNoteItem", back_populates="delivery_note", cascade="all, delete-orphan")

class DeliveryNoteItem(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "delivery_note_items"
    id = Column(Integer, primary_key=True, index=True)
    delivery_note_id = Column(Integer, ForeignKey('delivery_notes.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    
    delivery_note = relationship("DeliveryNote", back_populates="items")
    product = relationship("Product")
