from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class SaleDetailBase(BaseModel):
    product_id: int
    quantity: float
    unit_price: float
    tax_rate_id: Optional[int] = None

class SaleBase(BaseModel):
    customer_id: int
    payment_method: Optional[str] = "cash"
    currency: Optional[str] = "USD"
    exchange_rate: Optional[float] = 1.0
    cash_session_id: Optional[int] = None

class SaleCreate(SaleBase):
    warehouse_id: int
    details: List[SaleDetailBase]

class SaleDetailResponse(SaleDetailBase):
    id: int
    sale_id: int
    subtotal: float
    model_config = ConfigDict(from_attributes=True)

class SaleResponse(SaleBase):
    id: int
    tenant_id: int
    subtotal: float
    tax_total: float
    total: float
    created_at: datetime
    cash_session_id: Optional[int]
    details: List[SaleDetailResponse]
    model_config = ConfigDict(from_attributes=True)
