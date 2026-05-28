from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.domain.inventory import StockMovement, StockSummary, Product, Warehouse, MovementType
from app.services.movement_logger import MovementLogger


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
        tenant_id: int = None,
        user_id: int = None,
        user_name: str = None,
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

        # 3. Log to SystemMovement
        try:
            # Fetch product and warehouse names for denormalization
            prod_result = await db.execute(select(Product).where(Product.id == product_id))
            product = prod_result.scalars().first()
            wh_result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
            warehouse = wh_result.scalars().first()

            # Map movement_subtype/type to operation label
            operation_map = {
                "CHARGE":      "CHARGE",
                "DISCHARGE":   "DISCHARGE",
                "ADJUSTMENT":  "ADJUSTMENT",
                "TRANSFER":    "TRANSFER",
                "DISPATCH":    "DISPATCH",
                "SALE":        "SALE",
                "PURCHASE":    "PURCHASE",
            }
            operation = operation_map.get(movement_subtype, "ADJUSTMENT")

            await MovementLogger.log_stock_movement(
                db=db,
                tenant_id=tenant_id,
                operation=operation,
                product_id=product_id,
                product_name=product.name if product else f"Producto #{product_id}",
                product_sku=product.sku if product else "",
                warehouse_id=warehouse_id,
                warehouse_name=warehouse.name if warehouse else f"Almacén #{warehouse_id}",
                quantity=abs(quantity),
                unit=product.unit_of_measure if product else "unidades",
                reference_id=movement.id,
                reference_code=reference or document_number,
                user_id=user_id,
                user_name=user_name,
                notes=notes,
            )
        except Exception:
            # Never block the main operation due to logging failures
            pass

        return movement

    @staticmethod
    async def get_stock_alerts(db: AsyncSession, tenant_id: int):
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
