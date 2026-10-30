from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class PurchaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"       # Pendiente de aprobación
    APPROVED = "APPROVED"     # Aprobada, pendiente de recepción
    COMPLETED = "COMPLETED"   # Recibida y completada
    CANCELLED = "CANCELLED"

class Supplier(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    tax_id = Column(String, unique=True, index=True)
    phone = Column(String)
    address = Column(Text)
    # Datos adicionales para gestión de proveedores
    contact_person = Column(String, nullable=True)  # Persona de contacto
    bank_name = Column(String, nullable=True)  # Banco para pagos
    bank_account = Column(String, nullable=True)  # Número de cuenta
    payment_terms = Column(String, default="contado")  # contado, credito_15, credito_30, credito_60
    credit_days = Column(Integer, default=0)
    is_withholding_agent = Column(Boolean, default=False)  # ¿Es agente de retención?
    notes = Column(Text, nullable=True)
    
    purchases = relationship("Purchase", back_populates="supplier")

class Purchase(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=True)  # Almacén de recepción
    status = Column(Enum(PurchaseStatus), default=PurchaseStatus.DRAFT)
    subtotal = Column(Numeric(18, 4), nullable=False, default=0.0)
    tax_total = Column(Numeric(18, 4), nullable=False, default=0.0)
    total = Column(Numeric(18, 4), nullable=False, default=0.0)
    # Datos del documento del proveedor
    reference = Column(String)  # Número de referencia interna
    invoice_number = Column(String, nullable=True, index=True)  # Número de factura del proveedor
    control_number = Column(String, nullable=True)  # Número de control fiscal del proveedor
    invoice_date = Column(String, nullable=True)  # Fecha de la factura del proveedor
    # Retenciones
    iva_withholding = Column(Numeric(18, 4), default=0.0)  # Retención de IVA (75%)
    islr_withholding = Column(Numeric(18, 4), default=0.0)  # Retención de ISLR
    # Pago
    payment_method = Column(String, default="cash")
    is_accounted = Column(Boolean, default=False)
    exchange_rate = Column(Numeric(18, 4), default=1.0)
    currency = Column(String, default="USD")
    notes = Column(Text, nullable=True)
    
    supplier = relationship("Supplier", back_populates="purchases")
    details = relationship("PurchaseDetail", back_populates="purchase")

class PurchaseDetail(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "purchase_details"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False)
    received_quantity = Column(Numeric(18, 4), default=0.0)  # Para recepciones parciales
    cost_price = Column(Numeric(18, 4), nullable=False)
    subtotal = Column(Numeric(18, 4), nullable=False)
    
    purchase = relationship("Purchase", back_populates="details")
    product = relationship("Product")
