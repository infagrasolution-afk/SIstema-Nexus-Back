from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.inventory import StockMovement, MovementType, Product
from app.schemas.inventory import WarehouseResponse

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
        out_movement = StockMovement(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            movement_type=MovementType.OUT,
            quantity=quantity,
            reference=f"Transfer to Warehouse #{to_warehouse_id}",
            tenant_id=tenant_id
        )
        db.add(out_movement)
        
        # 2. Add to destination
        in_movement = StockMovement(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            movement_type=MovementType.IN,
            quantity=quantity,
            reference=f"Transfer from Warehouse #{from_warehouse_id}",
            tenant_id=tenant_id
        )
        db.add(in_movement)
        
        await db.commit()
        return True
