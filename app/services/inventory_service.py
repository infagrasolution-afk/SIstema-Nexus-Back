from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.domain.inventory import StockMovement, MovementType, MovementSubtype, Product, StockSummary
from app.services.wms_service import WMSService
from app.repositories.inventory_repo import product_repo, stock_movement_repo
from app.schemas.inventory import StockAdjustmentCreate, StockChargeCreate, StockDischargeCreate

class InventoryService:
    @staticmethod
    async def transfer_stock(
        db: AsyncSession, 
        product_id: int, 
        from_warehouse_id: int, 
        to_warehouse_id: int, 
        quantity: float, 
        tenant_id: int
    ):
        # 1. Deduct from source
        await WMSService.register_movement(
            db, product_id, from_warehouse_id, quantity, MovementType.OUT, 
            reference=f"Transfer to Warehouse #{to_warehouse_id}", tenant_id=tenant_id
        )
        
        # 2. Add to destination
        await WMSService.register_movement(
            db, product_id, to_warehouse_id, quantity, MovementType.IN, 
            reference=f"Transfer from Warehouse #{from_warehouse_id}", tenant_id=tenant_id
        )
        
        await db.commit()
        return True

    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        adjustment: StockAdjustmentCreate,
        tenant_id: int,
        user_id: int
    ):
        # 1. Start a transaction and lock the product row using with_for_update()
        product = await product_repo.get_with_lock(db, adjustment.product_id)
        if not product or product.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # 2. Check current stock from StockSummary (Enterprise optimization)
        stock_stmt = select(func.sum(StockSummary.quantity)).where(
            StockSummary.product_id == product.id,
            StockSummary.tenant_id == tenant_id
        )
        current_stock = await db.scalar(stock_stmt) or 0

        # 3. Validation
        if adjustment.quantity < 0 and abs(adjustment.quantity) > current_stock:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Stock actual: {current_stock}")

        # 4. Register Movement via WMS
        mov_type = MovementType.IN if adjustment.quantity > 0 else MovementType.OUT
        
        movement = await WMSService.register_movement(
            db=db,
            product_id=product.id,
            warehouse_id=adjustment.warehouse_id,
            bin_location_id=adjustment.bin_location_id,
            batch_id=adjustment.batch_id,
            movement_type=mov_type,
            movement_subtype=MovementSubtype.ADJUSTMENT,
            quantity=abs(adjustment.quantity),
            reference=adjustment.reference,
            tenant_id=tenant_id
        )
        movement.user_id = user_id

        # 5. Calculate Weighted Average Cost if it's an IN movement with a unit cost
        if mov_type == MovementType.IN and adjustment.unit_cost:
            total_value_current = current_stock * product.average_cost
            new_value = adjustment.quantity * adjustment.unit_cost
            new_total_qty = current_stock + adjustment.quantity
            
            if new_total_qty > 0:
                product.average_cost = (total_value_current + new_value) / new_total_qty

        await db.commit()
        return movement

    @staticmethod
    async def charge_stock(
        db: AsyncSession,
        charge: StockChargeCreate,
        tenant_id: int,
        user_id: int
    ):
        product = await product_repo.get_with_lock(db, charge.product_id)
        if not product or product.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        stock_stmt = select(func.sum(StockSummary.quantity)).where(
            StockSummary.product_id == product.id,
            StockSummary.tenant_id == tenant_id
        )
        current_stock = await db.scalar(stock_stmt) or 0

        if charge.quantity <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

        movement = await WMSService.register_movement(
            db=db,
            product_id=product.id,
            warehouse_id=charge.warehouse_id,
            bin_location_id=charge.bin_location_id,
            batch_id=charge.batch_id,
            movement_type=MovementType.IN,
            movement_subtype=MovementSubtype.CHARGE,
            quantity=charge.quantity,
            reference=charge.reference,
            document_number=charge.document_number,
            notes=charge.notes,
            tenant_id=tenant_id
        )
        movement.user_id = user_id

        if charge.unit_cost:
            total_value_current = current_stock * product.average_cost
            new_value = charge.quantity * charge.unit_cost
            new_total_qty = current_stock + charge.quantity
            
            if new_total_qty > 0:
                product.average_cost = (total_value_current + new_value) / new_total_qty

        await db.commit()
        return movement

    @staticmethod
    async def discharge_stock(
        db: AsyncSession,
        discharge: StockDischargeCreate,
        tenant_id: int,
        user_id: int
    ):
        product = await product_repo.get_with_lock(db, discharge.product_id)
        if not product or product.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        stock_stmt = select(func.sum(StockSummary.quantity)).where(
            StockSummary.product_id == product.id,
            StockSummary.warehouse_id == discharge.warehouse_id,
            StockSummary.tenant_id == tenant_id
        )
        current_stock = await db.scalar(stock_stmt) or 0

        if discharge.quantity <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

        if discharge.quantity > current_stock:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente en el almacén. Stock actual: {current_stock}")

        movement = await WMSService.register_movement(
            db=db,
            product_id=product.id,
            warehouse_id=discharge.warehouse_id,
            bin_location_id=discharge.bin_location_id,
            batch_id=discharge.batch_id,
            movement_type=MovementType.OUT,
            movement_subtype=discharge.reason or MovementSubtype.DISCHARGE,
            quantity=discharge.quantity,
            reference=discharge.reference,
            document_number=discharge.document_number,
            notes=discharge.notes,
            tenant_id=tenant_id
        )
        movement.user_id = user_id

        await db.commit()
        return movement
