from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin

class PurchaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Supplier(Base, TimestampMixin, TenantMixin):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    tax_id = Column(String, unique=True, index=True)
    phone = Column(String)
    address = Column(Text)
    
    purchases = relationship("Purchase", back_populates="supplier")

class Purchase(Base, TimestampMixin, TenantMixin):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    status = Column(Enum(PurchaseStatus), default=PurchaseStatus.DRAFT)
    subtotal = Column(Float, nullable=False, default=0.0)
    tax_total = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    reference = Column(String) # Invoice number from supplier
    
    supplier = relationship("Supplier", back_populates="purchases")
    details = relationship("PurchaseDetail", back_populates="purchase")

class PurchaseDetail(Base, TimestampMixin, TenantMixin):
    __tablename__ = "purchase_details"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    purchase = relationship("Purchase", back_populates="details")
    product = relationship("Product")
