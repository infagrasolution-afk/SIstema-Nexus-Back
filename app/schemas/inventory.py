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
