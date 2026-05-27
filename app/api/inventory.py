from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_tenant, get_current_user
from app.domain.inventory import Product, Warehouse, BinLocation, Batch, ExchangeRateHistory
from app.services.inventory_service import InventoryService
from app.services.currency_service import CurrencyService
from app.services.wms_service import WMSService
from app.schemas.inventory import (
    ProductCreate, ProductResponse, 
    WarehouseCreate, WarehouseResponse,
    BinLocationCreate, BinLocationResponse,
    BatchCreate, BatchResponse,
    StockAdjustmentCreate, StockMovementResponse,
    StockChargeCreate, StockDischargeCreate
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

@router.get("/alerts")
async def get_inventory_alerts(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    return await WMSService.get_stock_alerts(db, tenant_id)

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

@router.post("/adjustments")
async def adjust_stock(
    adjustment: StockAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user) # get_current_user from auth
):
    movement = await InventoryService.adjust_stock(
        db=db,
        adjustment=adjustment,
        tenant_id=tenant_id,
        user_id=current_user.id
    )
    return {"message": "Stock adjusted successfully", "movement_id": movement.id}

@router.get("/adjustments", response_model=List[StockMovementResponse])
async def get_adjustments(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.orm import selectinload
    from app.domain.inventory import StockMovement
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.tenant_id == tenant_id)
        .where(StockMovement.movement_type == "ADJUSTMENT")
        .options(selectinload(StockMovement.product))
        .options(selectinload(StockMovement.warehouse))
        .order_by(StockMovement.created_at.desc())
    )
    return result.scalars().all()

@router.post("/charges")
async def create_charge(
    charge: StockChargeCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user)
):
    movement = await InventoryService.charge_stock(
        db=db,
        charge=charge,
        tenant_id=tenant_id,
        user_id=current_user.id
    )
    return {"message": "Cargo registrado con éxito", "movement_id": movement.id}

@router.get("/charges", response_model=List[StockMovementResponse])
async def get_charges(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.orm import selectinload
    from app.domain.inventory import StockMovement, MovementSubtype
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.tenant_id == tenant_id)
        .where(StockMovement.movement_subtype == MovementSubtype.CHARGE)
        .options(selectinload(StockMovement.product))
        .options(selectinload(StockMovement.warehouse))
        .order_by(StockMovement.created_at.desc())
    )
    return result.scalars().all()

@router.post("/discharges")
async def create_discharge(
    discharge: StockDischargeCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user)
):
    movement = await InventoryService.discharge_stock(
        db=db,
        discharge=discharge,
        tenant_id=tenant_id,
        user_id=current_user.id
    )
    return {"message": "Descargo registrado con éxito", "movement_id": movement.id}

@router.get("/discharges", response_model=List[StockMovementResponse])
async def get_discharges(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.orm import selectinload
    from app.domain.inventory import StockMovement, MovementType, MovementSubtype
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.tenant_id == tenant_id)
        .where(StockMovement.movement_type == MovementType.OUT)
        # Assuming most OUT movements that aren't SALES or TRANSFERS are DISCHARGES
        .where(StockMovement.movement_subtype != MovementSubtype.SALE)
        .where(StockMovement.movement_subtype != MovementSubtype.TRANSFER)
        .options(selectinload(StockMovement.product))
        .options(selectinload(StockMovement.warehouse))
        .order_by(StockMovement.created_at.desc())
    )
    return result.scalars().all()

# --- Products ---
@router.get("/products", response_model=List[ProductResponse])
async def get_products(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    products = result.scalars().all()
    
    from app.domain.inventory import StockSummary
    from sqlalchemy import func
    
    stock_stmt = (
        select(StockSummary.product_id, func.sum(StockSummary.quantity))
        .where(StockSummary.tenant_id == tenant_id)
        .group_by(StockSummary.product_id)
    )
    stock_result = await db.execute(stock_stmt)
    stock_dict = {row[0]: row[1] for row in stock_result.all()}
    
    for product in products:
        product.stock = stock_dict.get(product.id, 0.0)
        
    return products

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
    new_product.stock = 0.0
    return new_product

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .where(Product.tenant_id == tenant_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    for field, value in product_in.model_dump().items():
        setattr(product, field, value)
        
    await db.commit()
    await db.refresh(product)
    
    from app.domain.inventory import StockSummary
    from sqlalchemy import func
    stock_result = await db.execute(
        select(func.sum(StockSummary.quantity))
        .where(StockSummary.product_id == product.id)
        .where(StockSummary.tenant_id == tenant_id)
    )
    product.stock = stock_result.scalar() or 0.0
    
    return product

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .where(Product.tenant_id == tenant_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    await db.delete(product)
    await db.commit()
    return {"message": "Producto eliminado"}

# --- Warehouses ---
@router.get("/warehouses", response_model=List[WarehouseResponse])
async def get_warehouses(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.tenant_id == tenant_id)
        .options(selectinload(Warehouse.bins))
    )
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
    await db.refresh(new_warehouse, attribute_names=['bins'])
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
