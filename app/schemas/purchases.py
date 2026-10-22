from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.domain.purchases import PurchaseStatus

class PurchaseDetailBase(BaseModel):
    product_id: int
    quantity: float
    cost_price: float

class PurchaseCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    reference: Optional[str] = None
    payment_method: str = "cash"
    draft: bool = False  # Si True, crea en estado DRAFT; si False, completa directamente
    details: List[PurchaseDetailBase]

class PurchaseUpdate(BaseModel):
    reference: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

class PurchaseReceiveItem(BaseModel):
    product_id: int
    received_quantity: float  # Cantidad realmente recibida (puede ser parcial)

class PurchaseReceiveIn(BaseModel):
    warehouse_id: int
    items: Optional[List[PurchaseReceiveItem]] = None  # Si None, se reciben todas las lineas completas
    notes: Optional[str] = None

class SupplierBasicResponse(BaseModel):
    id: int
    name: str
    tax_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PurchaseDetailResponse(PurchaseDetailBase):
    id: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class PurchaseResponse(BaseModel):
    id: int
    supplier_id: int
    supplier: Optional[SupplierBasicResponse] = None
    status: PurchaseStatus
    subtotal: float
    tax_total: float
    total: float
    reference: Optional[str] = None
    payment_method: str
    created_at: datetime
    details: List[PurchaseDetailResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
