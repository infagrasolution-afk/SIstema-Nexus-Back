from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from datetime import datetime, timedelta
from app.domain.sales import Sale, Customer
from app.domain.purchases import Purchase
from app.domain.inventory import Product, StockSummary
from app.domain.treasury import AccountsReceivable, AccountsPayable, DebtStatus


class DashboardService:
    @staticmethod
    async def get_summary(
        db: AsyncSession,
        tenant_id: int,
        period: str = "month",  # today | week | month | year | all
    ):
        now = datetime.utcnow()

        # ── Rango de fechas según el período ──────────────────────────────────
        if period == "today":
            date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            date_from = now - timedelta(days=7)
        elif period == "month":
            date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            date_from = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            date_from = None  # all time

        # ── Ventas ────────────────────────────────────────────────────────────
        sale_base = select(Sale).where(
            Sale.tenant_id == tenant_id,
            Sale.status == "COMPLETED"
        )
        if date_from:
            sale_base = sale_base.where(Sale.created_at >= date_from)

        sales_sum = await db.scalar(
            select(func.sum(Sale.total)).where(
                Sale.tenant_id == tenant_id,
                Sale.status == "COMPLETED",
                *([Sale.created_at >= date_from] if date_from else [])
            )
        )
        sales_count = await db.scalar(
            select(func.count(Sale.id)).where(
                Sale.tenant_id == tenant_id,
                Sale.status == "COMPLETED",
                *([Sale.created_at >= date_from] if date_from else [])
            )
        )

        # ── Compras ───────────────────────────────────────────────────────────
        purchases_sum = await db.scalar(
            select(func.sum(Purchase.total)).where(
                Purchase.tenant_id == tenant_id,
                Purchase.status == "COMPLETED",
                *([Purchase.created_at >= date_from] if date_from else [])
            )
        )

        # ── Inventario ────────────────────────────────────────────────────────
        active_products = await db.scalar(
            select(func.count(Product.id)).where(Product.tenant_id == tenant_id)
        )

        # Stock total en Bs (suma de StockSummary)
        stock_value_query = await db.execute(
            select(func.sum(StockSummary.quantity * Product.average_cost))
            .join(Product, Product.id == StockSummary.product_id)
            .where(StockSummary.tenant_id == tenant_id)
        )
        stock_value = stock_value_query.scalar() or 0.0

        # Low stock: productos con stock < 5 (podrías usar un campo min_stock en el futuro)
        low_stock_result = await db.execute(
            select(Product.id, Product.name, Product.sku, func.coalesce(func.sum(StockSummary.quantity), 0).label("total_stock"))
            .outerjoin(StockSummary, StockSummary.product_id == Product.id)
            .where(Product.tenant_id == tenant_id)
            .group_by(Product.id, Product.name, Product.sku)
            .having(func.coalesce(func.sum(StockSummary.quantity), 0) < 5)
            .order_by(func.coalesce(func.sum(StockSummary.quantity), 0).asc())
            .limit(10)
        )
        low_stock_items = [
            {"id": row.id, "name": row.name, "sku": row.sku, "stock": float(row.total_stock)}
            for row in low_stock_result.all()
        ]

        # ── Cuentas por cobrar/pagar ──────────────────────────────────────────
        ar_open = await db.scalar(
            select(func.sum(AccountsReceivable.remaining_amount)).where(
                AccountsReceivable.tenant_id == tenant_id,
                AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
            )
        )
        ap_open = await db.scalar(
            select(func.sum(AccountsPayable.remaining_amount)).where(
                AccountsPayable.tenant_id == tenant_id,
                AccountsPayable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
            )
        )

        # CxC vencidas
        ar_overdue = await db.scalar(
            select(func.count(AccountsReceivable.id)).where(
                AccountsReceivable.tenant_id == tenant_id,
                AccountsReceivable.due_date < now,
                AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
            )
        )

        # ── Gráfico de ventas por día (últimos 7 días) ────────────────────────
        sales_chart = []
        days_labels = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_sum = await db.scalar(
                select(func.sum(Sale.total)).where(
                    Sale.tenant_id == tenant_id,
                    Sale.status == "COMPLETED",
                    Sale.created_at >= day_start,
                    Sale.created_at < day_end,
                )
            )
            label = days_labels[day_start.weekday() + 1 if day_start.weekday() < 6 else 0]
            sales_chart.append({"name": label, "fecha": day_start.strftime("%Y-%m-%d"), "ventas": float(day_sum or 0)})

        # ── Top 5 productos más vendidos ──────────────────────────────────────
        from app.domain.sales import SaleDetail
        top_products_result = await db.execute(
            select(Product.name, Product.sku, func.sum(SaleDetail.quantity).label("total_vendido"))
            .join(SaleDetail, SaleDetail.product_id == Product.id)
            .join(Sale, Sale.id == SaleDetail.sale_id)
            .where(
                Sale.tenant_id == tenant_id,
                Sale.status == "COMPLETED",
                *([Sale.created_at >= date_from] if date_from else [])
            )
            .group_by(Product.name, Product.sku)
            .order_by(func.sum(SaleDetail.quantity).desc())
            .limit(5)
        )
        top_products = [
            {"name": r.name, "sku": r.sku, "total_vendido": float(r.total_vendido)}
            for r in top_products_result.all()
        ]

        # ── Top 5 clientes ────────────────────────────────────────────────────
        top_customers_result = await db.execute(
            select(Customer.name, func.sum(Sale.total).label("total_comprado"), func.count(Sale.id).label("num_ventas"))
            .join(Sale, Sale.customer_id == Customer.id)
            .where(
                Sale.tenant_id == tenant_id,
                Sale.status == "COMPLETED",
                *([Sale.created_at >= date_from] if date_from else [])
            )
            .group_by(Customer.name)
            .order_by(func.sum(Sale.total).desc())
            .limit(5)
        )
        top_customers = [
            {"name": r.name, "total_comprado": float(r.total_comprado), "num_ventas": r.num_ventas}
            for r in top_customers_result.all()
        ]

        return {
            "period": period,
            "date_from": date_from.isoformat() if date_from else None,
            # ── KPIs principales ──────────────────────────────────────────────
            "total_sales": float(sales_sum or 0),
            "total_orders": int(sales_count or 0),
            "total_purchases": float(purchases_sum or 0),
            "active_products": int(active_products or 0),
            "stock_value": float(stock_value),
            "low_stock_count": len(low_stock_items),
            # ── Tesorería ─────────────────────────────────────────────────────
            "ar_open": float(ar_open or 0),
            "ap_open": float(ap_open or 0),
            "ar_overdue_count": int(ar_overdue or 0),
            # ── Gráficos ──────────────────────────────────────────────────────
            "sales_chart": sales_chart,
            "low_stock_items": low_stock_items,
            "top_products": top_products,
            "top_customers": top_customers,
        }
