from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.sales import Sale, SaleDetail, Budget, BudgetItem, Customer
from app.domain.inventory import MovementType, MovementSubtype
from app.services.wms_service import WMSService
from app.schemas.sales import SaleCreate, BudgetCreate, CustomerCreate
from app.services.treasury_service import TreasuryService
from app.services.movement_logger import MovementLogger


class SalesService:
    @staticmethod
    async def find_or_create_customer(
        db: AsyncSession,
        customer_in: CustomerCreate,
        tenant_id: int,
        user_id: int,
        user_name: str
    ):
        result = await db.execute(
            select(Customer).where(Customer.tax_id == customer_in.tax_id, Customer.tenant_id == tenant_id)
        )
        customer = result.scalars().first()
        if not customer:
            customer = Customer(
                tax_id=customer_in.tax_id,
                name=customer_in.name,
                phone=customer_in.phone,
                email=customer_in.email,
                address=customer_in.address,
                tenant_id=tenant_id,
                created_by_id=user_id,
                created_by_name=user_name
            )
            db.add(customer)
            await db.flush()
        return customer

    @staticmethod
    async def create_sale(
        db: AsyncSession,
        sale_in: SaleCreate,
        tenant_id: int,
        user_id: int,
        user_name: str
    ) -> Sale:
        subtotal = 0.0
        tax_total = 0.0

        # Fetch customer name for logging
        cust_result = await db.execute(select(Customer).where(Customer.id == sale_in.customer_id))
        customer = cust_result.scalars().first()
        customer_name = customer.name if customer else f"Cliente #{sale_in.customer_id}"

        new_sale = Sale(
            customer_id=sale_in.customer_id,
            payment_method=sale_in.payment_method,
            currency=sale_in.currency,
            exchange_rate=sale_in.exchange_rate,
            cash_session_id=sale_in.cash_session_id,
            status=sale_in.status,
            subtotal=0, tax_total=0, total=0,
            tenant_id=tenant_id,
            created_by_id=user_id,
            created_by_name=user_name
        )
        db.add(new_sale)
        await db.flush()

        for detail in sale_in.details:
            detail_subtotal = detail.quantity * detail.unit_price
            subtotal += detail_subtotal
            detail_tax = detail_subtotal * 0.16
            tax_total += detail_tax

            new_detail = SaleDetail(
                sale_id=new_sale.id,
                product_id=detail.product_id,
                quantity=detail.quantity,
                unit_price=detail.unit_price,
                subtotal=detail_subtotal,
                tax_rate_id=detail.tax_rate_id,
                tenant_id=tenant_id,
                created_by_id=user_id,
                created_by_name=user_name
            )
            db.add(new_detail)

            # Inventory deduction via WMS ONLY if not ON_HOLD
            if sale_in.status != "ON_HOLD":
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=sale_in.warehouse_id,
                    movement_type=MovementType.OUT,
                    movement_subtype=MovementSubtype.SALE,   # ← trazabilidad correcta
                    quantity=detail.quantity,
                    reference=f"Venta #{new_sale.id:06d}",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_name=user_name,
                )

        new_sale.subtotal = subtotal
        igtf_total = 0.0
        if sale_in.currency == "USD":
            igtf_total = (subtotal + tax_total) * 0.03
        new_sale.tax_total = tax_total + igtf_total
        new_sale.total = subtotal + tax_total + igtf_total

        # CxC Integration ONLY if not ON_HOLD
        if new_sale.status != "ON_HOLD" and new_sale.payment_method == "credit":
            await TreasuryService.create_ar(db, new_sale.id, new_sale.customer_id, new_sale.total, tenant_id)

        # ── Log principal de la venta ──────────────────────────────────────────
        if new_sale.status != "ON_HOLD":
            await MovementLogger.log_sale(
                db=db,
                tenant_id=tenant_id,
                sale_id=new_sale.id,
                customer_name=customer_name,
                total=new_sale.total,
                currency=sale_in.currency or "VES",
                payment_method=sale_in.payment_method,
                user_id=user_id,
                user_name=user_name,
                status="COMPLETED",
            )

        await db.commit()
        await db.refresh(new_sale)
        await db.refresh(new_sale, ["details"])
        return new_sale

    @staticmethod
    async def create_budget(
        db: AsyncSession,
        budget_in: BudgetCreate,
        tenant_id: int,
        user_id: int,
        user_name: str
    ) -> Budget:
        subtotal = 0.0
        tax_total = 0.0

        new_budget = Budget(
            customer_id=budget_in.customer_id,
            currency=budget_in.currency,
            valid_until=budget_in.valid_until,
            subtotal=0, tax_total=0, total=0,
            tenant_id=tenant_id,
            created_by_id=user_id,
            created_by_name=user_name
        )
        db.add(new_budget)
        await db.flush()

        for item in budget_in.items:
            item_subtotal = item.quantity * item.unit_price
            subtotal += item_subtotal
            item_tax = item_subtotal * 0.16
            tax_total += item_tax

            new_item = BudgetItem(
                budget_id=new_budget.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item_subtotal,
                tenant_id=tenant_id,
                created_by_id=user_id,
                created_by_name=user_name
            )
            db.add(new_item)

        new_budget.subtotal = subtotal
        new_budget.tax_total = tax_total
        new_budget.total = subtotal + tax_total

        await db.commit()
        await db.refresh(new_budget)
        await db.refresh(new_budget, ["items"])
        return new_budget
