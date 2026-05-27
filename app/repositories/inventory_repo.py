from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.domain.inventory import Product, StockMovement, Warehouse

class ProductRepository(BaseRepository[Product]):
    def __init__(self):
        super().__init__(Product)
        
    async def get_by_sku(self, db: AsyncSession, sku: str) -> Optional[Product]:
        result = await db.execute(select(self.model).filter(self.model.sku == sku))
        return result.scalars().first()

class StockMovementRepository(BaseRepository[StockMovement]):
    def __init__(self):
        super().__init__(StockMovement)

class WarehouseRepository(BaseRepository[Warehouse]):
    def __init__(self):
        super().__init__(Warehouse)

# Instantiate the repositories
product_repo = ProductRepository()
stock_movement_repo = StockMovementRepository()
warehouse_repo = WarehouseRepository()
