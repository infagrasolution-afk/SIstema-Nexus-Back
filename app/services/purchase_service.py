from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.purchases import Purchase, PurchaseDetail, PurchaseStatus, Supplier
from app.domain.inventory import MovementType, MovementSubtype, Product
from app.services.wms_service import WMSService
from app.schemas.purchases import PurchaseCreate
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

        new_purchase = Purchase(
            supplier_id=purchase_in.supplier_id,
            reference=purchase_in.reference,
            payment_method=purchase_in.payment_method,
            status=PurchaseStatus.COMPLETED,
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

            # Update product cost (Last Price)
            result = await db.execute(select(Product).where(Product.id == detail.product_id))
            product = result.scalars().first()
            if product:
                # Weighted average cost
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

            # Inventory entry via WMS with correct subtype
            await WMSService.register_movement(
                db=db,
                product_id=detail.product_id,
                warehouse_id=purchase_in.warehouse_id,
                movement_type=MovementType.IN,
                movement_subtype=MovementSubtype.PURCHASE,   # ← trazabilidad correcta
                quantity=detail.quantity,
                reference=f"Compra #{new_purchase.id:06d} / Ref: {purchase_in.reference or ''}",
                tenant_id=tenant_id,
                user_id=user_id,
                user_name=user_name,
            )

        new_purchase.subtotal = subtotal
        new_purchase.tax_total = subtotal * 0.16
        new_purchase.total = subtotal + new_purchase.tax_total

        # CxP Integration
        if purchase_in.payment_method == "credit":
            await TreasuryService.create_ap(
                db, new_purchase.id, new_purchase.supplier_id, new_purchase.total, tenant_id
            )

        # ── Log principal de la compra ─────────────────────────────────────────
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
