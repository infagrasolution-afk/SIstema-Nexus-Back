from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.sales import Sale, SaleDetail, Budget, BudgetItem, Customer
from app.domain.inventory import Product, MovementType, MovementSubtype
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
        subtotal = Decimal('0.0000')
        tax_total = Decimal('0.0000')
        discount_total = Decimal('0.0000')

        # Fetch customer name for logging
        cust_result = await db.execute(select(Customer).where(Customer.id == sale_in.customer_id))
        customer = cust_result.scalars().first()
        customer_name = customer.name if customer else f"Cliente #{sale_in.customer_id}"

        rate = Decimal(str(sale_in.exchange_rate)) if sale_in.exchange_rate and sale_in.exchange_rate > 0 else Decimal('1.0000')

        new_sale = Sale(
            customer_id=sale_in.customer_id,
            warehouse_id=sale_in.warehouse_id or 1,
            payment_method=sale_in.payment_method,
            currency=sale_in.currency or "USD",
            exchange_rate=rate,
            cash_session_id=sale_in.cash_session_id,
            status=sale_in.status or "COMPLETED",
            fiscal_invoice_number=sale_in.fiscal_invoice_number,
            control_number=sale_in.control_number,
            printer_serial=sale_in.printer_serial,
            notes=sale_in.notes,
            subtotal=Decimal('0.0000'),
            tax_total=Decimal('0.0000'),
            total=Decimal('0.0000'),
            discount_total=Decimal('0.0000'),
            igtf_amount=Decimal('0.0000'),
            tenant_id=tenant_id,
            created_by_id=user_id,
            created_by_name=user_name
        )
        db.add(new_sale)
        await db.flush()

        for detail in sale_in.details:
            qty = Decimal(str(detail.quantity))
            u_price = Decimal(str(detail.unit_price))

            # Consultar producto para verificar exoneración y tasa de impuesto
            prod_result = await db.execute(select(Product).where(Product.id == detail.product_id))
            product = prod_result.scalars().first()

            # Descuentos por ítem
            disc_percent = Decimal(str(getattr(detail, 'discount_percent', 0) or 0))
            disc_amount = Decimal(str(getattr(detail, 'discount_amount', 0) or 0))

            base_line = qty * u_price
            if disc_percent > 0:
                disc_amount = (base_line * disc_percent) / Decimal('100.0')

            line_subtotal = base_line - disc_amount
            if line_subtotal < Decimal('0.0000'):
                line_subtotal = Decimal('0.0000')

            subtotal += line_subtotal
            discount_total += disc_amount

            # Cálculo de impuesto dinámico (SENIAT / Producto)
            line_tax = Decimal('0.0000')
            if product and not product.tax_exempt:
                rate_to_apply = (product.tax_rate or Decimal('16.0000')) / Decimal('100.0')
                line_tax = line_subtotal * rate_to_apply
            elif not product:
                # Fallback al 16% general de IVA en Venezuela si el producto no tiene configuración
                line_tax = line_subtotal * Decimal('0.1600')

            tax_total += line_tax

            new_detail = SaleDetail(
                sale_id=new_sale.id,
                product_id=detail.product_id,
                quantity=qty,
                unit_price=u_price,
                subtotal=line_subtotal,
                discount_percent=disc_percent,
                discount_amount=disc_amount,
                tax_rate_id=detail.tax_rate_id,
                tenant_id=tenant_id,
                created_by_id=user_id,
                created_by_name=user_name
            )
            db.add(new_detail)

            # Deducción de inventario mediante WMS solo si no está en espera (ON_HOLD)
            if sale_in.status != "ON_HOLD":
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=sale_in.warehouse_id or 1,
                    movement_type=MovementType.OUT,
                    movement_subtype=MovementSubtype.SALE,
                    quantity=qty,
                    reference=f"Venta #{new_sale.id:06d}",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_name=user_name,
                )

        new_sale.subtotal = subtotal
        new_sale.discount_total = discount_total

        # IGTF (Impuesto a las Grandes Transacciones Financieras 3% en pagos con divisas)
        igtf_total = Decimal('0.0000')
        if (sale_in.currency == "USD" or getattr(sale_in, 'igtf_amount', None)) and sale_in.payment_method in ["cash", "zelle", "crypto", "divisas"]:
            igtf_total = (subtotal + tax_total) * Decimal('0.0300')

        new_sale.igtf_amount = igtf_total
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
