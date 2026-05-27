from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Bins ---
class BinLocationBase(BaseModel):
    code: str
    description: Optional[str] = None
    zone: Optional[str] = None
    warehouse_id: int

class BinLocationCreate(BinLocationBase):
    pass

class BinLocationResponse(BinLocationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Batches ---
class BatchBase(BaseModel):
    batch_number: str
    expiry_date: Optional[datetime] = None
    production_date: Optional[datetime] = None
    product_id: int
    supplier_id: Optional[int] = None

class BatchCreate(BatchBase):
    pass

class BatchResponse(BatchBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Products ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    price: float
    cost: float = 0.0
    average_cost: float = 0.0
    
    # WMS Fields
    track_batches: bool = False
    track_expiry: bool = False
    min_stock: float = 0.0
    max_stock: float = 0.0
    unit_of_measure: str = "unit"

class ProductCreate(ProductBase):
    category_id: Optional[int] = None

class ProductResponse(ProductBase):
    id: int
    tenant_id: int
    stock: float = 0.0
    model_config = ConfigDict(from_attributes=True)

# --- Warehouses ---
class WarehouseBase(BaseModel):
    name: str
    address: Optional[str] = None
    is_active: bool = True

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseResponse(WarehouseBase):
    id: int
    tenant_id: int
    bins: List[BinLocationResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Movements & Adjustments ---
class StockAdjustmentBase(BaseModel):
    product_id: int
    warehouse_id: int
    bin_location_id: Optional[int] = None
    batch_id: Optional[int] = None
    quantity: float
    reference: Optional[str] = "Manual Adjustment"
    unit_cost: Optional[float] = None # For calculating average cost if it's an IN adjustment

class StockAdjustmentCreate(StockAdjustmentBase):
    pass

class StockChargeCreate(BaseModel):
    product_id: int
    warehouse_id: int
    bin_location_id: Optional[int] = None
    batch_id: Optional[int] = None
    quantity: float
    reference: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    unit_cost: Optional[float] = None

class StockDischargeCreate(BaseModel):
    product_id: int
    warehouse_id: int
    bin_location_id: Optional[int] = None
    batch_id: Optional[int] = None
    quantity: float
    reference: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    reason: Optional[str] = None

class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    movement_type: str
    movement_subtype: Optional[str] = None
    quantity: float
    reference: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    # Optional nested info
    product: Optional[ProductResponse] = None
    warehouse: Optional[WarehouseResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
