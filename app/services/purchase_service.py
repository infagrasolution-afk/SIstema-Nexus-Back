from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domain.purchases import Purchase, PurchaseDetail, PurchaseStatus, Supplier
from app.domain.inventory import MovementType, MovementSubtype, Product, StockSummary
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
        subtotal = Decimal('0.0000')

        # Buscar nombre del proveedor
        sup_result = await db.execute(select(Supplier).where(Supplier.id == purchase_in.supplier_id))
        supplier = sup_result.scalars().first()
        supplier_name = supplier.name if supplier else f"Proveedor #{purchase_in.supplier_id}"

        # Estado inicial
        initial_status = PurchaseStatus.DRAFT if purchase_in.draft else PurchaseStatus.COMPLETED

        rate = Decimal(str(purchase_in.exchange_rate or 1.0))
        iva_withholding = Decimal(str(purchase_in.iva_withholding or 0.0))
        islr_withholding = Decimal(str(purchase_in.islr_withholding or 0.0))

        new_purchase = Purchase(
            supplier_id=purchase_in.supplier_id,
            warehouse_id=purchase_in.warehouse_id or 1,
            invoice_number=purchase_in.invoice_number,
            control_number=purchase_in.control_number,
            reference=purchase_in.reference,
            payment_method=purchase_in.payment_method,
            currency=purchase_in.currency or "USD",
            exchange_rate=rate,
            iva_withholding=iva_withholding,
            islr_withholding=islr_withholding,
            notes=purchase_in.notes,
            status=initial_status,
            subtotal=Decimal('0.0000'),
            tax_total=Decimal('0.0000'),
            total=Decimal('0.0000'),
            tenant_id=tenant_id
        )
        db.add(new_purchase)
        await db.flush()

        for detail in purchase_in.details:
            qty = Decimal(str(detail.quantity))
            cost = Decimal(str(detail.cost_price))
            detail_subtotal = qty * cost
            subtotal += detail_subtotal

            new_detail = PurchaseDetail(
                purchase_id=new_purchase.id,
                product_id=detail.product_id,
                quantity=qty,
                cost_price=cost,
                subtotal=detail_subtotal,
                received_quantity=qty if not purchase_in.draft else Decimal('0.0000'),
                tenant_id=tenant_id
            )
            db.add(new_detail)

            # Si no es borrador, actualizar inventario y costo promedio ponderado
            if not purchase_in.draft:
                result = await db.execute(select(Product).where(Product.id == detail.product_id))
                product = result.scalars().first()
                if product:
                    stock_stmt = select(func.sum(StockSummary.quantity)).where(
                        StockSummary.product_id == product.id,
                        StockSummary.tenant_id == tenant_id
                    )
                    current_stock = await db.scalar(stock_stmt) or Decimal('0.0000')
                    current_stock = Decimal(str(current_stock))
                    avg_cost = Decimal(str(product.average_cost or 0.0))

                    if current_stock > Decimal('0.0000'):
                        total_val = current_stock * avg_cost
                        new_val = qty * cost
                        product.average_cost = (total_val + new_val) / (current_stock + qty)
                    else:
                        product.average_cost = cost
                    product.cost = cost

                # Entrada en WMS
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=purchase_in.warehouse_id or 1,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.PURCHASE,
                    quantity=qty,
                    reference=f"Compra #{new_purchase.id:06d} / Factura: {purchase_in.invoice_number or purchase_in.reference or ''}",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_name=user_name,
                )

        new_purchase.subtotal = subtotal
        # Cálculo de IVA (16% estándar SENIAT)
        new_purchase.tax_total = subtotal * Decimal('0.1600')
        new_purchase.total = subtotal + new_purchase.tax_total

        # Neto a pagar descontando retenciones fiscales venezolanas (IVA e ISLR)
        net_payable = new_purchase.total - iva_withholding - islr_withholding
        if net_payable < Decimal('0.0000'):
            net_payable = Decimal('0.0000')

        # Integración con Cuentas por Pagar (CxP)
        if not purchase_in.draft and purchase_in.payment_method == "credit":
            await TreasuryService.create_ap(
                db, new_purchase.id, new_purchase.supplier_id, net_payable, tenant_id
            )

        # Log
        if not purchase_in.draft:
            await MovementLogger.log_purchase(
                db=db,
                tenant_id=tenant_id,
                purchase_id=new_purchase.id,
                supplier_name=supplier_name,
                total=new_purchase.total,
                currency=purchase_in.currency or "USD",
                payment_method=purchase_in.payment_method,
                reference=purchase_in.invoice_number or purchase_in.reference,
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
        receive_in: PurchaseReceiveIn,
        tenant_id: int,
        user_id: int = None,
        user_name: str = None,
    ) -> dict:
        """Procesa la recepción de mercancía de una OC con soporte para entregas parciales."""
        receive_map = {}
        if receive_in.items:
            for item in receive_in.items:
                receive_map[item.product_id] = Decimal(str(item.received_quantity))

        received_details = []
        target_wh = receive_in.warehouse_id or purchase.warehouse_id or 1

        for detail in purchase.details:
            qty = receive_map.get(detail.product_id, Decimal(str(detail.quantity))) if receive_in.items else Decimal(str(detail.quantity))
            if qty <= Decimal('0.0000'):
                continue

            # Actualizar cantidad recibida en el detalle
            detail.received_quantity = (Decimal(str(detail.received_quantity or 0.0))) + qty

            # Actualizar costo promedio ponderado
            result = await db.execute(select(Product).where(Product.id == detail.product_id))
            product = result.scalars().first()
            if product:
                stock_stmt = select(func.sum(StockSummary.quantity)).where(
                    StockSummary.product_id == product.id,
                    StockSummary.tenant_id == tenant_id
                )
                current_stock = await db.scalar(stock_stmt) or Decimal('0.0000')
                current_stock = Decimal(str(current_stock))
                avg_cost = Decimal(str(product.average_cost or 0.0))
                cost = Decimal(str(detail.cost_price))

                if current_stock > Decimal('0.0000'):
                    total_val = current_stock * avg_cost
                    new_val = qty * cost
                    product.average_cost = (total_val + new_val) / (current_stock + qty)
                else:
                    product.average_cost = cost
                product.cost = cost

            # Entrada WMS
            await WMSService.register_movement(
                db=db,
                product_id=detail.product_id,
                warehouse_id=target_wh,
                movement_type=MovementType.IN,
                movement_subtype=MovementSubtype.PURCHASE,
                quantity=qty,
                reference=f"Recepción Compra #{purchase.id:06d} (Factura: {purchase.invoice_number or purchase.reference or ''})",
                tenant_id=tenant_id,
                user_id=user_id,
                user_name=user_name,
            )
            received_details.append({"product_id": detail.product_id, "received_qty": float(qty)})

        purchase.status = PurchaseStatus.COMPLETED

        # Generar CxP si es a crédito y no se había generado antes
        if purchase.payment_method == "credit":
            iva_ret = Decimal(str(purchase.iva_withholding or 0.0))
            islr_ret = Decimal(str(purchase.islr_withholding or 0.0))
            net_payable = Decimal(str(purchase.total)) - iva_ret - islr_ret
            if net_payable < Decimal('0.0000'):
                net_payable = Decimal('0.0000')

            await TreasuryService.create_ap(
                db, purchase.id, purchase.supplier_id, net_payable, tenant_id
            )

        # Nombre del proveedor para el log
        sup_result = await db.execute(select(Supplier).where(Supplier.id == purchase.supplier_id))
        supplier = sup_result.scalars().first()
        supplier_name = supplier.name if supplier else f"Proveedor #{purchase.supplier_id}"

        await MovementLogger.log_purchase(
            db=db,
            tenant_id=tenant_id,
            purchase_id=purchase.id,
            supplier_name=supplier_name,
            total=purchase.total,
            currency=purchase.currency or "USD",
            payment_method=purchase.payment_method,
            reference=purchase.invoice_number or purchase.reference,
            user_id=user_id,
            user_name=user_name,
        )

        await db.commit()
        return {
            "status": "success",
            "message": f"Compra #{purchase.id} recibida exitosamente en almacén {target_wh}.",
            "received_details": received_details,
        }
