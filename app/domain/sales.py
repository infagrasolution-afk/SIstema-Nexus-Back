from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin
from app.domain.inventory import Product
from app.domain.cash import CashSession

class Customer(Base, TimestampMixin, TenantMixin):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String)
    phone = Column(String)
    tax_id = Column(String)

class TaxRate(Base, TimestampMixin, TenantMixin):
    __tablename__ = "tax_rates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rate = Column(Float, nullable=False)

class Sale(Base, TimestampMixin, TenantMixin):
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
    
    customer = relationship("Customer")
    tenant = relationship("app.domain.tenant.Tenant")
    cash_session = relationship("CashSession", back_populates="sales")
    details = relationship("SaleDetail", back_populates="sale")

class SaleDetail(Base, TimestampMixin, TenantMixin):
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
