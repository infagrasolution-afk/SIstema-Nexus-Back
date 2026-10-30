from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

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
    barcode: Optional[str] = None
    price: Decimal
    cost: Decimal = Decimal('0.0000')
    average_cost: Decimal = Decimal('0.0000')
    tax_exempt: bool = False
    tax_rate: Decimal = Decimal('16.0000')
    margin_percent: Decimal = Decimal('30.0000')
    
    # WMS Fields
    track_batches: bool = False
    track_expiry: bool = False
    min_stock: Decimal = Decimal('0.0000')
    max_stock: Decimal = Decimal('0.0000')
    unit_of_measure: str = "unit"
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    category_id: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    average_cost: Optional[Decimal] = None
    tax_exempt: Optional[bool] = None
    tax_rate: Optional[Decimal] = None
    margin_percent: Optional[Decimal] = None
    track_batches: Optional[bool] = None
    track_expiry: Optional[bool] = None
    min_stock: Optional[Decimal] = None
    max_stock: Optional[Decimal] = None
    unit_of_measure: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None

class ProductResponse(ProductBase):
    id: int
    tenant_id: int
    category_id: Optional[int] = None
    stock: Decimal = Decimal('0.0000')
    model_config = ConfigDict(from_attributes=True)

class InitialStockImport(BaseModel):
    sku: str
    name: str
    cost: Decimal = Decimal('0.0000')
    price: Decimal = Decimal('0.0000')
    quantity: Decimal
    warehouse_id: int

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
    quantity: Decimal
    reference: Optional[str] = "Manual Adjustment"
    unit_cost: Optional[Decimal] = None

class StockAdjustmentCreate(StockAdjustmentBase):
    pass

class StockChargeCreate(BaseModel):
    product_id: int
    warehouse_id: int
    bin_location_id: Optional[int] = None
    batch_id: Optional[int] = None
    quantity: Decimal
    reference: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    unit_cost: Optional[Decimal] = None

class StockDischargeCreate(BaseModel):
    product_id: int
    warehouse_id: int
    bin_location_id: Optional[int] = None
    batch_id: Optional[int] = None
    quantity: Decimal
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
    quantity: Decimal
    reference: Optional[str] = None
    document_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    product: Optional[ProductResponse] = None
    warehouse: Optional[WarehouseResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- Dispatch Notes ---
class DispatchNoteItemBase(BaseModel):
    product_id: int
    quantity: Decimal

class DispatchNoteItemCreate(DispatchNoteItemBase):
    pass

class DispatchNoteItemResponse(DispatchNoteItemBase):
    id: int
    product: Optional[ProductResponse] = None
    model_config = ConfigDict(from_attributes=True)

class DispatchNoteBase(BaseModel):
    source_warehouse_id: int
    destination_warehouse_id: int
    reference: Optional[str] = None

class DispatchNoteCreate(DispatchNoteBase):
    items: List[DispatchNoteItemCreate]

class DispatchNoteResponse(DispatchNoteBase):
    id: int
    status: str
    tenant_id: int
    items: List[DispatchNoteItemResponse] = []
    source_warehouse: Optional[WarehouseResponse] = None
    destination_warehouse: Optional[WarehouseResponse] = None
    model_config = ConfigDict(from_attributes=True)

# --- Inventory Audits ---
class InventoryAuditDetailBase(BaseModel):
    product_id: int
    expected_quantity: Decimal = Decimal('0.0000')
    counted_quantity: Optional[Decimal] = None
    difference: Optional[Decimal] = None

class InventoryAuditDetailCreate(BaseModel):
    product_id: int
    counted_quantity: Decimal

class InventoryAuditDetailResponse(InventoryAuditDetailBase):
    id: int
    audit_id: int
    product: Optional[ProductResponse] = None
    model_config = ConfigDict(from_attributes=True)

class InventoryAuditBase(BaseModel):
    warehouse_id: int
    name: str
    notes: Optional[str] = None

class InventoryAuditCreate(InventoryAuditBase):
    pass

class InventoryAuditResponse(InventoryAuditBase):
    id: int
    status: str
    tenant_id: int
    created_at: datetime
    warehouse: Optional[WarehouseResponse] = None
    details: List[InventoryAuditDetailResponse] = []
    model_config = ConfigDict(from_attributes=True)
