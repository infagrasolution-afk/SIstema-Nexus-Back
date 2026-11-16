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
        """
        Evalúa las alarmas de reposición de inventario:
        1. Por Almacén específico (cuando el producto tiene configurado `min_stock` en ese almacén o global)
        2. Global por Producto (cuando la suma o existencia en almacén está en o por debajo de `min_stock`)
        Retorna una lista detallada indicando que el producto está próximo a agotarse y debe reponerse.
        """
        from sqlalchemy import func

        # Obtener todos los productos e información de almacenes
        prod_res = await db.execute(select(Product).where(Product.tenant_id == tenant_id))
        products = {p.id: p for p in prod_res.scalars().all()}

        wh_res = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
        warehouses = {w.id: w for w in wh_res.scalars().all()}

        sum_res = await db.execute(select(StockSummary).where(StockSummary.tenant_id == tenant_id))
        summaries = sum_res.scalars().all()

        alerts = []
        alerted_product_wh = set()

        # 1. Evaluar stock por cada Almacén donde exista configuración o registro
        wh_grouped: dict[tuple[int, int], dict] = {}
        for s in summaries:
            key = (s.product_id, s.warehouse_id)
            if key not in wh_grouped:
                wh_grouped[key] = {"qty": 0.0, "min_stock": 0.0}
            wh_grouped[key]["qty"] += float(s.quantity or 0.0)
            if float(getattr(s, "min_stock", 0.0) or 0.0) > wh_grouped[key]["min_stock"]:
                wh_grouped[key]["min_stock"] = float(s.min_stock or 0.0)

        for (pid, wid), info in wh_grouped.items():
            prod = products.get(pid)
            if not prod:
                continue
            wh = warehouses.get(wid)
            wh_name = wh.name if wh else f"Almacén #{wid}"
            effective_min = info["min_stock"] if info["min_stock"] > 0 else float(prod.min_stock or 0.0)
            curr_qty = info["qty"]

            if effective_min > 0 and curr_qty <= effective_min:
                alerted_product_wh.add(pid)
                deficit = max(0.0, effective_min - curr_qty)
                status_label = "AGOTADO" if curr_qty <= 0 else "PRÓXIMO A AGOTARSE"
                alerts.append({
                    "product_id": pid,
                    "name": prod.name,
                    "sku": prod.sku,
                    "warehouse_id": wid,
                    "warehouse_name": wh_name,
                    "current_stock": round(curr_qty, 2),
                    "min_stock": round(effective_min, 2),
                    "deficit": round(deficit, 2),
                    "status": status_label,
                    "message": (
                        f"⚠️ ¡Alerta de Inventario en {wh_name}! El producto «{prod.name}» ({prod.sku}) "
                        f"{'está AGOTADO (0 und)' if curr_qty <= 0 else f'está próximo a agotarse (Quedan {curr_qty:g} de mín. {effective_min:g})'}. "
                        f"¡Debes reponer mercancía!"
                    ),
                })

        # 2. Evaluar productos que tengan min_stock > 0 pero aún no tengan fila en StockSummary (stock = 0)
        for pid, prod in products.items():
            if pid in alerted_product_wh:
                continue
            p_min = float(prod.min_stock or 0.0)
            if p_min > 0:
                total_qty = sum(
                    v["qty"] for (k_pid, _), v in wh_grouped.items() if k_pid == pid
                )
                if total_qty <= p_min:
                    alerts.append({
                        "product_id": pid,
                        "name": prod.name,
                        "sku": prod.sku,
                        "warehouse_id": None,
                        "warehouse_name": "General / Todos los Almacenes",
                        "current_stock": round(total_qty, 2),
                        "min_stock": round(p_min, 2),
                        "deficit": round(max(0.0, p_min - total_qty), 2),
                        "status": "AGOTADO" if total_qty <= 0 else "PRÓXIMO A AGOTARSE",
                        "message": (
                            f"⚠️ ¡Alerta de Inventario! El producto «{prod.name}» ({prod.sku}) "
                            f"{'está AGOTADO (0 und)' if total_qty <= 0 else f'está próximo a agotarse (Quedan {total_qty:g} de mín. {p_min:g})'}. "
                            f"¡Debes reponer mercancía!"
                        ),
                    })

        return alerts
