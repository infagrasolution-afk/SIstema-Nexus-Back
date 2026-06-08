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
    StockChargeCreate, StockDischargeCreate,
    DispatchNoteCreate, DispatchNoteResponse,
    InitialStockImport
)
from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from pydantic import BaseModel

class RateUpdate(BaseModel):
    rate: float
    provider: str = "Manual"

class StockTransfer(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: float

class RecalculatePricesRequest(BaseModel):
    margin_percent: float

router = APIRouter()

@router.get("/exchange-rate")
async def get_exchange_rate(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
):
    return await WMSService.get_stock_alerts(db, tenant_id)

@router.post("/exchange-rate")
async def update_exchange_rate_manual(
    rate_in: RateUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory")),
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
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory")),
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
    
    rate = CurrencyService.get_bcv_rate()
    for product in products:
        product.stock = stock_dict.get(product.id, 0.0)
        # Stored in Bs, convert to USD for frontend UI
        product.price = product.price / rate if rate > 0 else product.price
        product.cost = product.cost / rate if rate > 0 else product.cost
        product.average_cost = product.average_cost / rate if rate > 0 else product.average_cost
        
    return products

@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate, 
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.exc import IntegrityError
    rate = CurrencyService.get_bcv_rate()
    
    # Convert input USD to Bs using daily exchange rate before storing
    product_data = product_in.model_dump()
    product_data["price"] = product_data["price"] * rate
    product_data["cost"] = product_data["cost"] * rate
    product_data["average_cost"] = product_data["average_cost"] * rate
    
    new_product = Product(**product_data, tenant_id=tenant_id)
    db.add(new_product)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "sku" in error_msg.lower():
            raise HTTPException(status_code=400, detail="El SKU ingresado ya está registrado para otro producto. Por favor, utiliza un SKU único.")
        raise HTTPException(status_code=400, detail="Error de integridad: verifica que los datos sean válidos.")
    await db.refresh(new_product)
    new_product.stock = 0.0
    
    # Present USD to the frontend
    new_product.price = new_product.price / rate if rate > 0 else new_product.price
    new_product.cost = new_product.cost / rate if rate > 0 else new_product.cost
    new_product.average_cost = new_product.average_cost / rate if rate > 0 else new_product.average_cost
    
    return new_product

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from sqlalchemy.exc import IntegrityError
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .where(Product.tenant_id == tenant_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    rate = CurrencyService.get_bcv_rate()
    product_data = product_in.model_dump()
    product_data["price"] = product_data["price"] * rate
    product_data["cost"] = product_data["cost"] * rate
    product_data["average_cost"] = product_data["average_cost"] * rate
    
    for field, value in product_data.items():
        setattr(product, field, value)
        
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "sku" in error_msg.lower():
            raise HTTPException(status_code=400, detail="El SKU ingresado ya está registrado para otro producto. Por favor, utiliza un SKU único.")
        raise HTTPException(status_code=400, detail="Error de integridad: verifica que los datos sean válidos.")
        
    await db.refresh(product)
    
    from app.domain.inventory import StockSummary
    from sqlalchemy import func
    stock_result = await db.execute(
        select(func.sum(StockSummary.quantity))
        .where(StockSummary.product_id == product.id)
        .where(StockSummary.tenant_id == tenant_id)
    )
    product.stock = stock_result.scalar() or 0.0
    
    # Present USD to the frontend
    product.price = product.price / rate if rate > 0 else product.price
    product.cost = product.cost / rate if rate > 0 else product.cost
    product.average_cost = product.average_cost / rate if rate > 0 else product.average_cost
    
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


@router.post("/products/import")
async def import_products_bulk(
    products_in: List[ProductCreate],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory"))
):
    imported_count = 0
    errors = []
    rate = CurrencyService.get_bcv_rate()
    
    for idx, p_in in enumerate(products_in):
        if not p_in.sku or not p_in.name:
            errors.append(f"Fila {idx+1}: SKU y Nombre son campos obligatorios.")
            continue
            
        # Check if already exists
        check_stmt = select(Product).where(Product.sku == p_in.sku, Product.tenant_id == tenant_id)
        res = await db.execute(check_stmt)
        existing = res.scalars().first()
        
        price_bs = p_in.price * rate
        cost_bs = p_in.cost * rate
        avg_cost_bs = p_in.average_cost * rate
        
        if existing:
            # Update existing
            for field, value in p_in.model_dump().items():
                if field == "price":
                    existing.price = price_bs
                elif field == "cost":
                    existing.cost = cost_bs
                elif field == "average_cost":
                    existing.average_cost = avg_cost_bs
                else:
                    setattr(existing, field, value)
        else:
            # Create new
            product_data = p_in.model_dump()
            product_data["price"] = price_bs
            product_data["cost"] = cost_bs
            product_data["average_cost"] = avg_cost_bs
            new_p = Product(**product_data, tenant_id=tenant_id)
            db.add(new_p)
            
        imported_count += 1
        
    await db.commit()
    return {"status": "success", "imported": imported_count, "errors": errors}

@router.post("/import-initial-stock")
async def import_initial_stock(
    items_in: List[InitialStockImport],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory"))
):
    from sqlalchemy.exc import IntegrityError
    from app.domain.inventory import MovementType, MovementSubtype
    
    imported_count = 0
    errors = []
    rate = CurrencyService.get_bcv_rate()
    
    for idx, item in enumerate(items_in):
        if not item.sku or not item.name:
            errors.append(f"Fila {idx+1}: SKU y Nombre son campos obligatorios.")
            continue
            
        # 1. Find or Create Product
        check_stmt = select(Product).where(Product.sku == item.sku, Product.tenant_id == tenant_id)
        res = await db.execute(check_stmt)
        product = res.scalars().first()
        
        price_bs = item.price * rate
        cost_bs = item.cost * rate
        
        if not product:
            new_product = Product(
                sku=item.sku,
                name=item.name,
                price=price_bs,
                cost=cost_bs,
                average_cost=cost_bs,
                tenant_id=tenant_id
            )
            db.add(new_product)
            await db.flush() # flush to get the ID
            product = new_product
        else:
            # Optionally update cost/price if they want the cargo inicial to overwrite?
            # We'll just leave existing products as they are, but use them for the movement.
            pass
            
        # 2. Inject Initial Stock
        if item.quantity > 0:
            charge = StockChargeCreate(
                product_id=product.id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
                reference=f"Cargo Inicial CSV - Fila {idx+1}",
                notes="Importación masiva de saldo inicial"
            )
            await InventoryService.charge_stock(
                db=db,
                charge=charge,
                tenant_id=tenant_id,
                user_id=current_user.id
            )
            
        imported_count += 1
        
    await db.commit()
    return {"status": "success", "imported": imported_count, "errors": errors}

@router.post("/products/recalculate")
async def recalculate_product_prices(
    req: RecalculatePricesRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory"))
):
    # Fetch all products
    result = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    products = result.scalars().all()
    
    updated_count = 0
    for product in products:
        if product.cost is not None and product.cost > 0:
            product.price = product.cost * (1 + req.margin_percent / 100)
            updated_count += 1
            
    await db.commit()
    return {"status": "success", "updated_count": updated_count}


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
@router.post("/dispatch-notes/{dispatch_note_id}/dispatch")
async def confirm_dispatch(
    dispatch_note_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory")),
):
    """Confirma el despacho de una nota: mueve stock del almacén origen al destino."""
    from app.domain.inventory import DispatchNote, DispatchNoteItem, MovementType, MovementSubtype
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(DispatchNote)
        .where(DispatchNote.id == dispatch_note_id, DispatchNote.tenant_id == tenant_id)
        .options(selectinload(DispatchNote.items))
    )
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Nota de despacho no encontrada")
    if note.status not in ["PENDING", "IN_TRANSIT"]:
        raise HTTPException(status_code=400, detail=f"La nota ya fue procesada (status: {note.status})")

    for item in note.items:
        # Descarga del almacén origen
        await WMSService.register_movement(
            db=db,
            product_id=item.product_id,
            warehouse_id=note.source_warehouse_id,
            movement_type=MovementType.OUT,
            movement_subtype=MovementSubtype.DISCHARGE,
            quantity=item.quantity,
            reference=f"Despacho #{dispatch_note_id}",
            tenant_id=tenant_id,
            user_id=current_user.id,
            user_name=current_user.username,
        )
        # Carga en almacén destino
        await WMSService.register_movement(
            db=db,
            product_id=item.product_id,
            warehouse_id=note.destination_warehouse_id,
            movement_type=MovementType.IN,
            movement_subtype=MovementSubtype.CHARGE,
            quantity=item.quantity,
            reference=f"Recepción Despacho #{dispatch_note_id}",
            tenant_id=tenant_id,
            user_id=current_user.id,
            user_name=current_user.username,
        )

    note.status = "RECEIVED"
    await db.commit()
    return {"message": f"Despacho #{dispatch_note_id} confirmado. Stock transferido correctamente."}

@router.get("/dispatch-notes", response_model=List[DispatchNoteResponse])
async def list_dispatch_notes(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from app.domain.inventory import DispatchNote, DispatchNoteItem
    from app.schemas.inventory import DispatchNoteResponse
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(DispatchNote)
        .where(DispatchNote.tenant_id == tenant_id)
        .options(
            selectinload(DispatchNote.items).selectinload(DispatchNoteItem.product),
            selectinload(DispatchNote.source_warehouse),
            selectinload(DispatchNote.destination_warehouse)
        )
    )
    return result.scalars().all()

@router.post("/dispatch-notes", response_model=DispatchNoteResponse)
async def create_dispatch_note(
    note_in: DispatchNoteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user)
):
    from app.domain.inventory import DispatchNote, DispatchNoteItem
    from app.schemas.inventory import DispatchNoteResponse
    from sqlalchemy.orm import selectinload
    
    # 1. Create the master DispatchNote record
    new_note = DispatchNote(
        source_warehouse_id=note_in.source_warehouse_id,
        destination_warehouse_id=note_in.destination_warehouse_id,
        reference=note_in.reference,
        status="PENDING",
        tenant_id=tenant_id
    )
    db.add(new_note)
    await db.flush() # gets new_note.id
    
    # 2. Add the items
    for item in note_in.items:
        new_item = DispatchNoteItem(
            dispatch_note_id=new_note.id,
            product_id=item.product_id,
            quantity=item.quantity,
            tenant_id=tenant_id
        )
        db.add(new_item)
        
    await db.commit()
    
    # Fetch complete note to return
    result = await db.execute(
        select(DispatchNote)
        .where(DispatchNote.id == new_note.id)
        .options(
            selectinload(DispatchNote.items).selectinload(DispatchNoteItem.product),
            selectinload(DispatchNote.source_warehouse),
            selectinload(DispatchNote.destination_warehouse)
        )
    )
    return result.scalars().first()

# --- Inventory Audits ---
from app.domain.inventory import InventoryAudit, InventoryAuditDetail
from app.schemas.inventory import InventoryAuditCreate, InventoryAuditResponse, InventoryAuditDetailCreate, InventoryAuditDetailResponse

@router.get("/audits", response_model=List[InventoryAuditResponse])
async def get_audits(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory"))
):
    result = await db.execute(
        select(InventoryAudit)
        .where(InventoryAudit.tenant_id == tenant_id)
        .options(
            selectinload(InventoryAudit.warehouse),
            selectinload(InventoryAudit.details).selectinload(InventoryAuditDetail.product)
        )
        .order_by(InventoryAudit.created_at.desc())
    )
    return result.scalars().all()

@router.post("/audits", response_model=InventoryAuditResponse)
async def create_audit(
    audit_in: InventoryAuditCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory"))
):
    # Crear auditoría
    audit = InventoryAudit(
        warehouse_id=audit_in.warehouse_id,
        name=audit_in.name,
        notes=audit_in.notes,
        tenant_id=tenant_id,
        status="IN_PROGRESS"
    )
    db.add(audit)
    await db.flush()
    
    # Pre-cargar todos los productos como detalles esperando ser contados
    result = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
    products = result.scalars().all()
    
    for p in products:
        db.add(InventoryAuditDetail(
            audit_id=audit.id,
            product_id=p.id,
            expected_quantity=p.stock,
            tenant_id=tenant_id
        ))
        
    await db.commit()
    
    # Devolver con relaciones
    res = await db.execute(
        select(InventoryAudit).where(InventoryAudit.id == audit.id)
        .options(selectinload(InventoryAudit.warehouse), selectinload(InventoryAudit.details).selectinload(InventoryAuditDetail.product))
    )
    return res.scalars().first()

@router.post("/audits/{audit_id}/details")
async def add_audit_detail(
    audit_id: int,
    detail_in: InventoryAuditDetailCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("inventory"))
):
    # Buscar el detalle existente
    result = await db.execute(
        select(InventoryAuditDetail)
        .where(InventoryAuditDetail.audit_id == audit_id, InventoryAuditDetail.product_id == detail_in.product_id, InventoryAuditDetail.tenant_id == tenant_id)
    )
    detail = result.scalars().first()
    
    if not detail:
        raise HTTPException(status_code=404, detail="Producto no encontrado en esta auditoría")
        
    detail.counted_quantity = detail_in.counted_quantity
    detail.difference = detail_in.counted_quantity - detail.expected_quantity
    await db.commit()
    return {"message": "Conteo registrado"}

@router.post("/audits/{audit_id}/apply")
async def apply_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: BaseModel = Depends(get_current_user),
    _: bool = Depends(require_module("inventory"))
):
    result = await db.execute(
        select(InventoryAudit).where(InventoryAudit.id == audit_id, InventoryAudit.tenant_id == tenant_id)
        .options(selectinload(InventoryAudit.details))
    )
    audit = result.scalars().first()
    if not audit:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    if audit.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Auditoría ya aplicada")
        
    for detail in audit.details:
        if detail.counted_quantity is not None and detail.difference != 0:
            # Generate Adjustment
            movement_type = MovementType.IN if detail.difference > 0 else MovementType.OUT
            await WMSService.register_movement(
                db=db,
                product_id=detail.product_id,
                warehouse_id=audit.warehouse_id,
                movement_type=movement_type,
                movement_subtype=MovementSubtype.ADJUSTMENT,
                quantity=abs(detail.difference),
                reference=f"Ajuste Auditoría: {audit.name}",
                tenant_id=tenant_id,
                user_id=current_user.id,
                user_name=current_user.username
            )
            
    audit.status = "COMPLETED"
    await db.commit()
    return {"message": "Auditoría aplicada y ajustes de inventario generados"}
