from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

class Category(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="category")

class ExchangeRateHistory(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "exchange_rate_history"

    id = Column(Integer, primary_key=True, index=True)
    rate = Column(Float, nullable=False)
    provider = Column(String, default="BCV") # BCV or Manual
    
class Warehouse(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationship to Bins
    bins = relationship("BinLocation", back_populates="warehouse", cascade="all, delete-orphan")

class BinLocation(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "bin_locations"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String, index=True, nullable=False) # e.g. A1-S2-B3 (Aisle 1, Shelf 2, Bin 3)
    description = Column(String, nullable=True)
    zone = Column(String, nullable=True) # e.g. Cold Storage, Dry, High Value
    
    warehouse = relationship("Warehouse", back_populates="bins")

class Batch(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String, index=True, nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    production_date = Column(DateTime(timezone=True), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    
    product = relationship("Product", back_populates="batches")

class SerialNumber(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "serial_numbers"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    serial_number = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="IN_STOCK") # IN_STOCK, SOLD, DAMAGED, TRANSIT
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    bin_location_id = Column(Integer, ForeignKey("bin_locations.id"), nullable=True)
    
    product = relationship("Product")

class Product(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    price = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    average_cost = Column(Float, default=0.0)
    
    # WMS Features
    track_batches = Column(Boolean, default=False)
    track_expiry = Column(Boolean, default=False)
    min_stock = Column(Float, default=0.0)
    max_stock = Column(Float, default=0.0)
    
    unit_of_measure = Column(String, default="unit") # kg, mt, box, etc
    track_serials = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)
    
    category = relationship("Category", back_populates="products")
    batches = relationship("Batch", back_populates="product")
    movements = relationship("StockMovement", back_populates="product")

class MovementType:
    IN = "IN"           # Purchase, Return, Charge
    OUT = "OUT"         # Sale, Damage, Discharge
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"

class MovementSubtype:
    INITIAL_BALANCE = "INITIAL_BALANCE"
    CHARGE = "CHARGE"
    DISCHARGE = "DISCHARGE"
    ADJUSTMENT = "ADJUSTMENT"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    TRANSFER = "TRANSFER"   # ← nuevo
    DAMAGE = "DAMAGE"
    RETURN = "RETURN"
    DONATION = "DONATION"
    EXPIRED = "EXPIRED"
    THEFT = "THEFT"
    DISPATCH = "DISPATCH"   # ← nuevo
    OTHER = "OTHER"

class StockMovement(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    bin_location_id = Column(Integer, ForeignKey("bin_locations.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    
    movement_type = Column(String, nullable=False) # IN, OUT, TRANSFER, ADJUSTMENT
    movement_subtype = Column(String, nullable=True) # CHARGE, DISCHARGE, SALE, PURCHASE, etc.
    quantity = Column(Float, nullable=False)
    reference = Column(String, nullable=True) # Invoice #, Transfer #
    document_number = Column(String, nullable=True) # Physical or system doc number
    notes = Column(String, nullable=True) # Detailed observations
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    product = relationship("Product", back_populates="movements")
    warehouse = relationship("Warehouse")
    bin_location = relationship("BinLocation")
    batch = relationship("Batch")

class StockSummary(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "stock_summary"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    bin_location_id = Column(Integer, ForeignKey("bin_locations.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    quantity = Column(Float, default=0.0)
    
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    bin_location = relationship("BinLocation")
    batch = relationship("Batch")

class DispatchNote(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "dispatch_notes"
    id = Column(Integer, primary_key=True, index=True)
    source_warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    destination_warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=False)
    status = Column(String, default="PENDING") # PENDING, IN_TRANSIT, RECEIVED, CANCELLED
    reference = Column(String, nullable=True)
    
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])
    items = relationship("DispatchNoteItem", back_populates="dispatch_note", cascade="all, delete-orphan")

class DispatchNoteItem(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "dispatch_note_items"
    id = Column(Integer, primary_key=True, index=True)
    dispatch_note_id = Column(Integer, ForeignKey('dispatch_notes.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    
    dispatch_note = relationship("DispatchNote", back_populates="items")
    product = relationship("Product")
