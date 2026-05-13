from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_tenant
from app.domain.inventory import Product, Warehouse, BinLocation, Batch, ExchangeRateHistory
from app.services.inventory_service import InventoryService
from app.services.currency_service import CurrencyService
from app.schemas.inventory import (
    ProductCreate, ProductResponse, 
    WarehouseCreate, WarehouseResponse,
    BinLocationCreate, BinLocationResponse,
    BatchCreate, BatchResponse
)
from pydantic import BaseModel

class RateUpdate(BaseModel):
    rate: float
    provider: str = "Manual"

class StockTransfer(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: float

router = APIRouter()

@router.get("/exchange-rate")
async def get_exchange_rate(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    rate = CurrencyService.get_bcv_rate()
    
    # Save to history if it's the latest rate
    new_hist = ExchangeRateHistory(rate=rate, provider="BCV", tenant_id=tenant_id)
    db.add(new_hist)
    await db.commit()
    
    return {"rate": rate, "provider": "BCV"}

@router.get("/exchange-rate/history")
async def get_exchange_history(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(ExchangeRateHistory)
        .where(ExchangeRateHistory.tenant_id == tenant_id)
        .order_by(ExchangeRateHistory.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()

@router.post("/exchange-rate")
async def update_exchange_rate_manual(
    rate_in: RateUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_hist = ExchangeRateHistory(
        rate=rate_in.rate, 
        provider=rate_in.provider, 
        tenant_id=tenant_id
    )
    db.add(new_hist)
    await db.commit()
    return {"message": "Rate updated manually"}

@router.post("/transfers")
async def transfer_stock(
    transfer: StockTransfer,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    await InventoryService.transfer_stock(
        db, transfer.product_id, transfer.from_warehouse_id, 
        transfer.to_warehouse_id, transfer.quantity, tenant_id
    )
    return {"message": "Transfer successful"}

# --- Products ---
@router.get("/products", response_model=List[ProductResponse])
async def get_products(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    return result.scalars().all()

@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate, 
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_product = Product(**product_in.model_dump(), tenant_id=tenant_id)
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product

# --- Warehouses ---
@router.get("/warehouses", response_model=List[WarehouseResponse])
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
    return result.scalars().all()

@router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    warehouse_in: WarehouseCreate, 
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_warehouse = Warehouse(**warehouse_in.model_dump(), tenant_id=tenant_id)
    db.add(new_warehouse)
    await db.commit()
    await db.refresh(new_warehouse)
    return new_warehouse

# --- Bin Locations ---
@router.get("/warehouses/{warehouse_id}/bins", response_model=List[BinLocationResponse])
async def get_bins(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(BinLocation)
        .where(BinLocation.warehouse_id == warehouse_id)
        .where(BinLocation.tenant_id == tenant_id)
    )
    return result.scalars().all()

@router.post("/bins", response_model=BinLocationResponse)
async def create_bin(
    bin_in: BinLocationCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_bin = BinLocation(**bin_in.model_dump(), tenant_id=tenant_id)
    db.add(new_bin)
    await db.commit()
    await db.refresh(new_bin)
    return new_bin

# --- Batches ---
@router.get("/products/{product_id}/batches", response_model=List[BatchResponse])
async def get_product_batches(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Batch)
        .where(Batch.product_id == product_id)
        .where(Batch.tenant_id == tenant_id)
    )
    return result.scalars().all()

@router.post("/batches", response_model=BatchResponse)
async def create_batch(
    batch_in: BatchCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    new_batch = Batch(**batch_in.model_dump(), tenant_id=tenant_id)
    db.add(new_batch)
    await db.commit()
    await db.refresh(new_batch)
    return new_batch
