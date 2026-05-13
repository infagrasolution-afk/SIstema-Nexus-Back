from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.purchases import Purchase, PurchaseDetail, PurchaseStatus
from app.domain.inventory import StockMovement, MovementType, Product
from app.schemas.purchases import PurchaseCreate

class PurchaseService:
    @staticmethod
    async def create_purchase(db: AsyncSession, purchase_in: PurchaseCreate, tenant_id: int) -> Purchase:
        subtotal = 0.0
        
        new_purchase = Purchase(
            supplier_id=purchase_in.supplier_id,
            reference=purchase_in.reference,
            status=PurchaseStatus.COMPLETED, # For now auto-complete
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
            
            # Update product cost (Weighted Average or Last Price)
            # For simplicity, we use Last Price here
            result = await db.execute(select(Product).where(Product.id == detail.product_id))
            product = result.scalars().first()
            if product:
                product.cost = detail.cost_price
            
            # Inventory entry
            movement = StockMovement(
                product_id=detail.product_id,
                warehouse_id=purchase_in.warehouse_id,
                movement_type=MovementType.IN,
                quantity=detail.quantity,
                reference=f"Purchase #{new_purchase.id} / Ref: {purchase_in.reference}",
                tenant_id=tenant_id
            )
            db.add(movement)
            
        new_purchase.subtotal = subtotal
        new_purchase.tax_total = subtotal * 0.16 # Mocked tax
        new_purchase.total = subtotal + new_purchase.tax_total
        
        await db.commit()
        await db.refresh(new_purchase)
        await db.refresh(new_purchase, ["details"])
        return new_purchase
