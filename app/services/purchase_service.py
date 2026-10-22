from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.purchases import Purchase, PurchaseDetail, PurchaseStatus, Supplier
from app.domain.inventory import MovementType, MovementSubtype, Product
from app.services.wms_service import WMSService
from app.schemas.purchases import PurchaseCreate, PurchaseReceiveIn
from app.services.treasury_service import TreasuryService
from app.services.movement_logger import MovementLogger


class PurchaseService:
    @staticmethod
    async def create_purchase(
        db: AsyncSession,
        purchase_in: PurchaseCreate,
        tenant_id: int,
        user_id: int = None,
        user_name: str = None
    ) -> Purchase:
        subtotal = 0.0

        # Fetch supplier name for logging
        sup_result = await db.execute(select(Supplier).where(Supplier.id == purchase_in.supplier_id))
        supplier = sup_result.scalars().first()
        supplier_name = supplier.name if supplier else f"Proveedor #{purchase_in.supplier_id}"

        # Status: DRAFT if requested, otherwise COMPLETED directly
        initial_status = PurchaseStatus.DRAFT if purchase_in.draft else PurchaseStatus.COMPLETED

        new_purchase = Purchase(
            supplier_id=purchase_in.supplier_id,
            reference=purchase_in.reference,
            payment_method=purchase_in.payment_method,
            status=initial_status,
            tenant_id=tenant_id
        )
        db.add(new_purchase)
        await db.flush()

        for detail in purchase_in.details:
            detail_subtotal = detail.quantity * detail.cost_price
            subtotal += detail_subtotal

            new_detail = PurchaseDetail(
                purchase_id=new_purchase.id,
                product_id=detail.product_id,
                quantity=detail.quantity,
                cost_price=detail.cost_price,
                subtotal=detail_subtotal,
                tenant_id=tenant_id
            )
            db.add(new_detail)

            # Only update cost and inventory if NOT draft
            if not purchase_in.draft:
                # Update product cost (Weighted Average)
                result = await db.execute(select(Product).where(Product.id == detail.product_id))
                product = result.scalars().first()
                if product:
                    from sqlalchemy import func
                    from app.domain.inventory import StockSummary
                    stock_stmt = select(func.sum(StockSummary.quantity)).where(
                        StockSummary.product_id == product.id,
                        StockSummary.tenant_id == tenant_id
                    )
                    current_stock = await db.scalar(stock_stmt) or 0
                    if current_stock > 0:
                        total_val = current_stock * product.average_cost
                        new_val = detail.quantity * detail.cost_price
                        product.average_cost = (total_val + new_val) / (current_stock + detail.quantity)
                    else:
                        product.average_cost = detail.cost_price
                    product.cost = detail.cost_price

                # Inventory entry via WMS
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=purchase_in.warehouse_id,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.PURCHASE,
                    quantity=detail.quantity,
                    reference=f"Compra #{new_purchase.id:06d} / Ref: {purchase_in.reference or ''}",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_name=user_name,
                )

        new_purchase.subtotal = subtotal
        new_purchase.tax_total = subtotal * 0.16
        new_purchase.total = subtotal + new_purchase.tax_total

        # CxP Integration (only if not draft)
        if not purchase_in.draft and purchase_in.payment_method == "credit":
            await TreasuryService.create_ap(
                db, new_purchase.id, new_purchase.supplier_id, new_purchase.total, tenant_id
            )

        # Log
        if not purchase_in.draft:
            await MovementLogger.log_purchase(
                db=db,
                tenant_id=tenant_id,
                purchase_id=new_purchase.id,
                supplier_name=supplier_name,
                total=new_purchase.total,
                currency="VES",
                payment_method=purchase_in.payment_method,
                reference=purchase_in.reference,
                user_id=user_id,
                user_name=user_name,
            )

        await db.commit()
        await db.refresh(new_purchase)
        await db.refresh(new_purchase, ["details"])
        return new_purchase

    @staticmethod
    async def receive_purchase(
        db: AsyncSession,
        purchase: Purchase,
        receive_in,
        tenant_id: int,
        user_id: int = None,
        user_name: str = None,
    ) -> dict:
        """Procesa la recepción de mercancía de una OC. Soporta recepción parcial."""
        from app.domain.inventory import StockSummary
        from sqlalchemy import func

        # Build a quantity map from receive_in.items (product_id → received_qty)
        receive_map = {}
        if receive_in.items:
            for item in receive_in.items:
                receive_map[item.product_id] = item.received_quantity

        received_details = []
        for detail in purchase.details:
            qty = receive_map.get(detail.product_id, detail.quantity) if receive_in.items else detail.quantity
            if qty <= 0:
                continue

            # Update product cost (Weighted Average)
            result = await db.execute(select(Product).where(Product.id == detail.product_id))
            product = result.scalars().first()
            if product:
                stock_stmt = select(func.sum(StockSummary.quantity)).where(
                    StockSummary.product_id == product.id,
                    StockSummary.tenant_id == tenant_id
                )
                current_stock = await db.scalar(stock_stmt) or 0
                if current_stock > 0:
                    total_val = current_stock * product.average_cost
                    new_val = qty * detail.cost_price
                    product.average_cost = (total_val + new_val) / (current_stock + qty)
                else:
                    product.average_cost = detail.cost_price
                product.cost = detail.cost_price

            # Inventory entry via WMS
            await WMSService.register_movement(
                db=db,
                product_id=detail.product_id,
                warehouse_id=receive_in.warehouse_id,
                movement_type=MovementType.IN,
                movement_subtype=MovementSubtype.PURCHASE,
                quantity=qty,
                reference=f"Recepción OC #{purchase.id:06d}",
                tenant_id=tenant_id,
                user_id=user_id,
                user_name=user_name,
            )
            received_details.append({"product_id": detail.product_id, "received_qty": qty})

        purchase.status = PurchaseStatus.COMPLETED

        # CxP Integration
        if purchase.payment_method == "credit":
            await TreasuryService.create_ap(
                db, purchase.id, purchase.supplier_id, purchase.total, tenant_id
            )

        # Get supplier name for log
        sup_result = await db.execute(select(Supplier).where(Supplier.id == purchase.supplier_id))
        supplier = sup_result.scalars().first()
        supplier_name = supplier.name if supplier else f"Proveedor #{purchase.supplier_id}"

        await MovementLogger.log_purchase(
            db=db,
            tenant_id=tenant_id,
            purchase_id=purchase.id,
            supplier_name=supplier_name,
            total=purchase.total,
            currency="VES",
            payment_method=purchase.payment_method,
            reference=purchase.reference,
            user_id=user_id,
            user_name=user_name,
        )

        await db.commit()
        return {
            "status": "success",
            "message": f"OC #{purchase.id} marcada como COMPLETED. Inventario actualizado.",
            "received_details": received_details,
        }
