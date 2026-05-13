from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.sales import Sale, SaleDetail
from app.domain.inventory import StockMovement, MovementType
from app.schemas.sales import SaleCreate

class SalesService:
    @staticmethod
    async def create_sale(db: AsyncSession, sale_in: SaleCreate, tenant_id: int) -> Sale:
        subtotal = 0.0
        tax_total = 0.0
        
        new_sale = Sale(
            customer_id=sale_in.customer_id,
            payment_method=sale_in.payment_method,
            currency=sale_in.currency,
            exchange_rate=sale_in.exchange_rate,
            cash_session_id=sale_in.cash_session_id,
            subtotal=0, tax_total=0, total=0,
            tenant_id=tenant_id
        )
        db.add(new_sale)
        await db.flush() 
        
        for detail in sale_in.details:
            detail_subtotal = detail.quantity * detail.unit_price
            subtotal += detail_subtotal
            
            # Logic for taxes (currently mocked at 16%, could be fetched from DB)
            detail_tax = detail_subtotal * 0.16 
            tax_total += detail_tax
            
            new_detail = SaleDetail(
                sale_id=new_sale.id,
                product_id=detail.product_id,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
                subtotal=detail_subtotal,
                tax_rate_id=detail.tax_rate_id,
                tenant_id=tenant_id
            )
            db.add(new_detail)
            
            # Inventory deduction
            movement = StockMovement(
                product_id=detail.product_id,
                warehouse_id=sale_in.warehouse_id,
                movement_type=MovementType.OUT,
                quantity=detail.quantity,
                reference=f"Sale #{new_sale.id}",
                tenant_id=tenant_id
            )
            db.add(movement)
            
        new_sale.subtotal = subtotal
        new_sale.tax_total = tax_total
        new_sale.total = subtotal + tax_total
        
        await db.commit()
        await db.refresh(new_sale)
        
        # Load details for response
        await db.refresh(new_sale, ["details"])
        return new_sale
