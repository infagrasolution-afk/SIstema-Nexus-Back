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
    details: List[PurchaseDetailBase]

class PurchaseDetailResponse(PurchaseDetailBase):
    id: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class PurchaseResponse(BaseModel):
    id: int
    supplier_id: int
    status: PurchaseStatus
    subtotal: float
    tax_total: float
    total: float
    reference: Optional[str] = None
    payment_method: str
    created_at: datetime
    details: List[PurchaseDetailResponse]
    
    model_config = ConfigDict(from_attributes=True)
