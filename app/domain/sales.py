from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text, Boolean
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
    # Campos de crédito
    credit_limit = Column(Numeric(18, 4), default=0.0)  # Límite de crédito en USD
    credit_days = Column(Integer, default=0)  # Días de crédito (0 = solo contado)
    # Contacto adicional
    contact_person = Column(String, nullable=True)  # Persona de contacto
    notes = Column(Text, nullable=True)  # Observaciones internas

class TaxRate(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "tax_rates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rate = Column(Numeric(8, 4), nullable=False)

class Sale(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=True)  # Almacén de despacho
    subtotal = Column(Numeric(18, 4), nullable=False)
    tax_total = Column(Numeric(18, 4), nullable=False)
    igtf_amount = Column(Numeric(18, 4), default=0.0)  # IGTF 3% separado para claridad fiscal
    discount_total = Column(Numeric(18, 4), default=0.0)  # Descuento total aplicado
    total = Column(Numeric(18, 4), nullable=False)
    payment_method = Column(String, default="cash") # cash, card, transfer, credit, mobile, zelle, mixed
    currency = Column(String, default="USD")
    exchange_rate = Column(Numeric(18, 4), default=1.0)
    cash_session_id = Column(Integer, ForeignKey('cash_sessions.id'), nullable=True)
    is_accounted = Column(Boolean, default=False)
    status = Column(String, default="COMPLETED") # COMPLETED, ON_HOLD, CANCELLED, VOIDED
    # Campos fiscales obligatorios
    fiscal_invoice_number = Column(String, nullable=True, index=True)  # Número de factura fiscal
    control_number = Column(String, nullable=True, index=True)  # Número de control SENIAT
    printer_serial = Column(String, nullable=True)
    # Notas
    notes = Column(Text, nullable=True)  # Observaciones de la venta
    voided_reason = Column(Text, nullable=True)  # Motivo de anulación
    
    customer = relationship("Customer")
    tenant = relationship("app.domain.tenant.Tenant")
    cash_session = relationship("CashSession", back_populates="sales")
    details = relationship("SaleDetail", back_populates="sale")
    warehouse = relationship("app.domain.inventory.Warehouse")

class SaleDetail(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "sale_details"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0.0)  # Descuento por línea en %
    discount_amount = Column(Numeric(18, 4), default=0.0)  # Descuento por línea en monto
    tax_rate_id = Column(Integer, ForeignKey('tax_rates.id'), nullable=True)
    tax_amount = Column(Numeric(18, 4), default=0.0)  # IVA calculado de esta línea
    subtotal = Column(Numeric(18, 4), nullable=False)
    
    sale = relationship("Sale", back_populates="details")
    product = relationship("Product")
    tax_rate = relationship("TaxRate")

class Budget(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    subtotal = Column(Numeric(18, 4), nullable=False)
    tax_total = Column(Numeric(18, 4), nullable=False)
    total = Column(Numeric(18, 4), nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED, EXPIRED
    valid_until = Column(String, nullable=True) # or DateTime
    notes = Column(Text, nullable=True)
    
    customer = relationship("Customer")
    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")

class BudgetItem(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "budget_items"
    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0.0)
    subtotal = Column(Numeric(18, 4), nullable=False)
    
    budget = relationship("Budget", back_populates="items")
    product = relationship("Product")

class CreditNote(Base, TimestampMixin, TenantMixin, AuditMixin):
    """Nota de Crédito — documento fiscal que reduce la deuda de un cliente."""
    __tablename__ = "credit_notes"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, index=True, nullable=True)  # Correlativo: NC-0001
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    reference_invoice_id = Column(Integer, ForeignKey('sales.id'), nullable=True)
    # Montos
    subtotal = Column(Numeric(18, 4), nullable=False)
    tax_amount = Column(Numeric(18, 4), default=0.0)
    total = Column(Numeric(18, 4), nullable=False)
    # Fiscal
    fiscal_number = Column(String, nullable=True)  # Número fiscal de la NC
    control_number = Column(String, nullable=True)  # Número de control SENIAT
    # Detalle
    reason = Column(Text, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, VOIDED
    # Tipo de afectación
    affects_inventory = Column(Boolean, default=True)  # Si los productos regresan al almacén
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=True)
    
    customer = relationship("Customer")
    reference_invoice = relationship("Sale")
    items = relationship("CreditNoteItem", back_populates="credit_note", cascade="all, delete-orphan")

class CreditNoteItem(Base, TimestampMixin, TenantMixin, AuditMixin):
    """Líneas de detalle de una Nota de Crédito."""
    __tablename__ = "credit_note_items"
    id = Column(Integer, primary_key=True, index=True)
    credit_note_id = Column(Integer, ForeignKey('credit_notes.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    subtotal = Column(Numeric(18, 4), nullable=False)
    
    credit_note = relationship("CreditNote", back_populates="items")
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
    quantity = Column(Numeric(18, 4), nullable=False)
    
    delivery_note = relationship("DeliveryNote", back_populates="items")
    product = relationship("Product")
