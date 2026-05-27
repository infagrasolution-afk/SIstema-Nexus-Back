from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.domain.inventory import StockMovement, StockSummary, Product, MovementType
# from app.schemas.inventory import StockAdjustment # Not used currently

class WMSService:
    @staticmethod
    async def register_movement(
        db: AsyncSession, 
        product_id: int, 
        warehouse_id: int, 
        quantity: float, 
        movement_type: str,
        movement_subtype: str = None,
        bin_location_id: int = None,
        batch_id: int = None,
        reference: str = None,
        document_number: str = None,
        notes: str = None,
        tenant_id: int = None
    ):
        # 1. Register the historical movement
        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            bin_location_id=bin_location_id,
            batch_id=batch_id,
            movement_type=movement_type,
            movement_subtype=movement_subtype,
            quantity=quantity,
            reference=reference,
            document_number=document_number,
            notes=notes,
            tenant_id=tenant_id
        )
        db.add(movement)
        
        # 2. Update or Create StockSummary
        stmt = select(StockSummary).where(
            and_(
                StockSummary.product_id == product_id,
                StockSummary.warehouse_id == warehouse_id,
                StockSummary.bin_location_id == bin_location_id,
                StockSummary.batch_id == batch_id,
                StockSummary.tenant_id == tenant_id
            )
        )
        result = await db.execute(stmt)
        summary = result.scalars().first()
        
        adjustment = quantity if movement_type in [MovementType.IN, MovementType.ADJUSTMENT] else -quantity
        
        if summary:
            summary.quantity += adjustment
        else:
            summary = StockSummary(
                product_id=product_id,
                warehouse_id=warehouse_id,
                bin_location_id=bin_location_id,
                batch_id=batch_id,
                quantity=adjustment,
                tenant_id=tenant_id
            )
            db.add(summary)
            
        await db.flush()
        return movement

    @staticmethod
    async def get_stock_alerts(db: AsyncSession, tenant_id: int):
        # Find products where total stock < min_stock
        from sqlalchemy import func
        stmt = select(
            Product.name, Product.sku, Product.min_stock, 
            func.sum(StockSummary.quantity).label("current_stock")
        ).join(StockSummary).where(
            Product.tenant_id == tenant_id
        ).group_by(Product.id).having(
            func.sum(StockSummary.quantity) < Product.min_stock
        )
        
        result = await db.execute(stmt)
        return result.all()
