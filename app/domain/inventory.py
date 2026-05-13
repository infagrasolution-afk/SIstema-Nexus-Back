from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin

class Category(Base, TimestampMixin, TenantMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="category")

class ExchangeRateHistory(Base, TimestampMixin, TenantMixin):
    __tablename__ = "exchange_rate_history"

    id = Column(Integer, primary_key=True, index=True)
    rate = Column(Float, nullable=False)
    provider = Column(String, default="BCV") # BCV or Manual
    
class Warehouse(Base, TimestampMixin, TenantMixin):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationship to Bins
    bins = relationship("BinLocation", back_populates="warehouse", cascade="all, delete-orphan")

class BinLocation(Base, TimestampMixin, TenantMixin):
    __tablename__ = "bin_locations"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String, index=True, nullable=False) # e.g. A1-S2-B3 (Aisle 1, Shelf 2, Bin 3)
    description = Column(String, nullable=True)
    zone = Column(String, nullable=True) # e.g. Cold Storage, Dry, High Value
    
    warehouse = relationship("Warehouse", back_populates="bins")

class Batch(Base, TimestampMixin, TenantMixin):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String, index=True, nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    production_date = Column(DateTime(timezone=True), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    
    product = relationship("Product", back_populates="batches")

class Product(Base, TimestampMixin, TenantMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    price = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    
    # WMS Features
    track_batches = Column(Boolean, default=False)
    track_expiry = Column(Boolean, default=False)
    min_stock = Column(Float, default=0.0)
    max_stock = Column(Float, default=0.0)
    
    unit_of_measure = Column(String, default="unit") # kg, mt, box, etc
    
    category = relationship("Category", back_populates="products")
    batches = relationship("Batch", back_populates="product")
    movements = relationship("StockMovement", back_populates="product")

class MovementType:
    IN = "IN"           # Purchase, Return
    OUT = "OUT"         # Sale, Damage
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"

class StockMovement(Base, TimestampMixin, TenantMixin):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    bin_location_id = Column(Integer, ForeignKey("bin_locations.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    
    movement_type = Column(String, nullable=False) # IN, OUT, TRANSFER, ADJUSTMENT
    quantity = Column(Float, nullable=False)
    reference = Column(String, nullable=True) # Invoice #, Transfer #
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    product = relationship("Product", back_populates="movements")
    warehouse = relationship("Warehouse")
    bin_location = relationship("BinLocation")
    batch = relationship("Batch")
