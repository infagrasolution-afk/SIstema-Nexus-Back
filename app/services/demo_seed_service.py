"""
Servicio de Población de Datos de Demostración e Inducción (Empresa Demo Venezuela).
Carga un ecosistema 100% completo y realista adaptado a Venezuela (SENIAT / LOTTT / BCV / VEN-NIF)
en TODOS los módulos del sistema ERP:
- Identidad corporativa y Logo SVG institucional en Base64
- Almacenes, Ubicaciones (Bins QR), 8 Productos con 3 Precios (P1, P2, P3), Stock Mínimo y Alarmas Activas
- Movimientos Kardex: Saldo Inicial, Cargos (Entradas), Descargos (Mermas), Notas de Despacho y Auditoría Física
- Clientes y Proveedores con RIF venezolano
- Facturas emitidas, Presupuestos, Notas de Entrega, Notas de Crédito y Notas de Débito
- Órdenes de Compra con Retención de IVA (75% SENIAT)
- Tesorería: Cuentas Bancarias (Banesco, Mercantil, Zelle), CxC, CxP y Cajas Registradoras
- Contabilidad VEN-NIF: Plan Único de Cuentas y Asientos de Libro Diario
- Nómina LOTTT: Ficha de Trabajadores, Período y Recibos calculados (SSO, RPE, FAOV, Cestaticket)
- Movimientos Forenses en Vivo con Usuario, Operación e IP
"""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tenant import Tenant
from app.domain.inventory import (
    Product,
    Warehouse,
    BinLocation,
    StockSummary,
    StockMovement,
    MovementType,
    MovementSubtype,
    DispatchNote,
    DispatchNoteItem,
    InventoryAudit,
    InventoryAuditDetail,
)
from app.domain.sales import (
    Customer,
    Sale,
    SaleDetail,
    Budget,
    BudgetItem,
    CreditNote,
    CreditNoteItem,
    DeliveryNote,
    DeliveryNoteItem,
)
from app.domain.purchases import Supplier, Purchase, PurchaseDetail, PurchaseStatus
from app.domain.treasury import BankAccount, AccountsReceivable, AccountsPayable, DebtStatus
from app.domain.accounting import Account, JournalEntry, JournalEntryDetail, DebitNote, JournalEntryStatus
from app.domain.cash import CashRegister
from app.domain.payroll import Employee, PayrollPeriod, PayrollReceipt
from app.domain.audit import SystemMovement
from app.services.currency_service import CurrencyService

DEMO_COMPANY_LOGO_DATA_URI = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNDAiIGhlaWdodD0i"
    "ODAiIHZpZXdCb3g9IjAgMCAyNDAgODAiPjxyZWN0IHdpZHRoPSI3MCIgaGVpZ2h0PSI3MCIgeD0iNSIg"
    "eT0iNSIgcng9IjE2IiBmaWxsPSIjMWUzYThhIi8+PHBhdGggZD0iTTM5IDE4TDE5IDU4SDMwTDM0IDQ5"
    "SDQ2TDUwIDU4SDYxTDM5IDE4Wk0zNiAzOUw0MCAyOUw0NCAzOUgzNloiIGZpbGw9IiNmZmZmZmYiLz48"
    "Y2lyY2xlIGN4PSI1OCIIGN5PSIyMiIgcj0iNiIgZmlsbD0iIzM4YmRmOCIvPjx0ZXh0IHg9Ijg4IiB5"
    "PSIzOCI font-family=\"Arial, sans-serif\" font-size=\"24\" font-weight=\"900\" "
    "fill=\"#1e3a8a\">APEX CORP</text><text x=\"88\" y=\"58\" font-family=\"Arial, sans-serif\" "
    "font-size=\"11\" font-weight=\"700\" fill=\"#475569\">VENEZUELA DEMO C.A.</text></svg>"
)


class DemoSeedService:
    @staticmethod
    async def seed_demo_company_data(
        db: AsyncSession,
        master_db: AsyncSession,
        tenant_id: int
    ) -> dict:
        """
        Puebla TODOS los módulos de la base de datos del tenant con información empresarial
        venezolana realista para demostraciones comerciales e inducciones guiadas. Es idempotente.
        """
        rate = float(await CurrencyService.get_bcv_rate(db))
        if rate <= 1.0:
            rate = 36.50

        # 1. Actualizar perfil fiscal y logo de la empresa en Master DB
        t_res = await master_db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_res.scalars().first()
        if tenant:
            if not tenant.tax_id or tenant.tax_id == "J-00000000-0":
                tenant.tax_id = "J-41258963-0"
            if not tenant.address:
                tenant.address = "Av. Francisco de Miranda, Torre Parque Cristal, Piso 8, Ofic. 8-B, Los Palos Grandes, Caracas"
            if not tenant.phone:
                tenant.phone = "+58 (212) 285-9410"
            if not tenant.email:
                tenant.email = "facturacion@apexdemo.com.ve"
            if not tenant.primary_color:
                tenant.primary_color = "#1e3a8a"
            if not getattr(tenant, "logo_url", None):
                tenant.logo_url = DEMO_COMPANY_LOGO_DATA_URI
            await master_db.commit()

        created_counts = {
            "warehouses": 0,
            "bins": 0,
            "products": 0,
            "customers": 0,
            "suppliers": 0,
            "sales": 0,
            "budgets": 0,
            "delivery_notes": 0,
            "credit_notes": 0,
            "debit_notes": 0,
            "purchases": 0,
            "dispatch_notes": 0,
            "audits": 0,
            "accounts": 0,
            "journal_entries": 0,
            "employees": 0,
            "bank_accounts": 0,
        }

        # 2. Almacenes y Ubicaciones (Bins QR)
        wh_res = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
        warehouses = wh_res.scalars().all()
        if not warehouses:
            w1 = Warehouse(
                name="Almacén Principal Caracas (Chacao)",
                address="Zona Industrial Los Cortijos, Galpón 14, Caracas",
                is_active=True,
                tenant_id=tenant_id,
            )
            w2 = Warehouse(
                name="Sucursal Centro Occidente (Valencia)",
                address="Zona Industrial Municipal Norte, Av. Este-Oeste, Valencia",
                is_active=True,
                tenant_id=tenant_id,
            )
            db.add_all([w1, w2])
            await db.flush()
            main_wh_id = w1.id
            sec_wh_id = w2.id
            created_counts["warehouses"] = 2
        else:
            main_wh_id = warehouses[0].id
            sec_wh_id = warehouses[1].id if len(warehouses) > 1 else warehouses[0].id

        existing_bins = (await db.execute(select(BinLocation).where(BinLocation.tenant_id == tenant_id))).scalars().all()
        if not existing_bins:
            db.add_all([
                BinLocation(
                    warehouse_id=main_wh_id,
                    code="PAS1-EST1-N1",
                    zone="Zona A - Tecnología y POS",
                    description="Estantería frontal de despacho rápido",
                    tenant_id=tenant_id,
                ),
                BinLocation(
                    warehouse_id=main_wh_id,
                    code="PAS2-EST3-N2",
                    zone="Zona B - Insumos y Papelería",
                    description="Estantería central para cajas y rollos térmicos",
                    tenant_id=tenant_id,
                ),
                BinLocation(
                    warehouse_id=sec_wh_id,
                    code="VAL-A1-01",
                    zone="Galpón Principal Valencia",
                    description="Recepción y despacho regional",
                    tenant_id=tenant_id,
                ),
            ])
            created_counts["bins"] = 3

        # 3. Productos con 3 Niveles de Precios + 2 Productos en Alarma de Stock Mínimo
        demo_products = [
            {
                "sku": "TECH-POS-001",
                "name": "Impresora Térmica POS 80mm USB/LAN Corte Automático",
                "description": "Impresora térmica de recibos 80mm compatible con facturación SENIAT",
                "cost_usd": 65.00,
                "price_1_usd": 115.00,
                "price_2_usd": 98.00,
                "price_3_usd": 88.00,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 45,
                "min_stock": 8,
            },
            {
                "sku": "TECH-MON-002",
                "name": "Monitor Corporativo Full HD 24 Pulgadas IPS",
                "description": "Monitor LED 24 pulgadas HDMI/VGA sin bordes para estaciones de trabajo",
                "cost_usd": 85.00,
                "price_1_usd": 145.00,
                "price_2_usd": 130.00,
                "price_3_usd": 118.00,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 30,
                "min_stock": 5,
            },
            {
                "sku": "TECH-SCN-003",
                "name": "Lector de Código de Barras 2D / QR Inalámbrico",
                "description": "Escáner láser e imagen 2D para punto de venta y almacenes WMS",
                "cost_usd": 28.00,
                "price_1_usd": 52.00,
                "price_2_usd": 45.00,
                "price_3_usd": 39.50,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 60,
                "min_stock": 10,
            },
            {
                "sku": "SUM-PAP-004",
                "name": "Caja Rollo Papel Térmico 80mm x 70mm (50 Unidades)",
                "description": "Papel térmico de alta densidad libre de BPA para impresoras POS",
                "cost_usd": 34.00,
                "price_1_usd": 58.00,
                "price_2_usd": 52.00,
                "price_3_usd": 47.00,
                "unit": "cja",
                "tax_exempt": False,
                "stock": 85,
                "min_stock": 15,
            },
            {
                "sku": "TECH-UPS-005",
                "name": "UPS Respaldo Eléctrico 1000VA / 600W Regulador AVR",
                "description": "Protección eléctrica para servidores y cajas registradoras ante fluctuaciones",
                "cost_usd": 54.00,
                "price_1_usd": 92.00,
                "price_2_usd": 82.00,
                "price_3_usd": 75.00,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 4,
                "min_stock": 10,
            },
            {
                "sku": "ALI-HAR-006",
                "name": "Fardo Harina de Maíz Precocida 20 x 1Kg (Exento IVA)",
                "description": "Producto de cesta básica exento de Impuesto al Valor Agregado (E)",
                "cost_usd": 14.50,
                "price_1_usd": 19.80,
                "price_2_usd": 18.20,
                "price_3_usd": 17.10,
                "unit": "paq",
                "tax_exempt": True,
                "stock": 120,
                "min_stock": 25,
            },
            {
                "sku": "ALI-CAF-007",
                "name": "Café Molido Gourmet Selección Especial 500g",
                "description": "Café arábigo venezolano tostado y molido empaque al vacío",
                "cost_usd": 4.20,
                "price_1_usd": 7.50,
                "price_2_usd": 6.60,
                "price_3_usd": 5.95,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 150,
                "min_stock": 20,
            },
            {
                "sku": "TECH-LAP-008",
                "name": "Laptop Empresarial Core i7 16GB RAM 512GB NVMe",
                "description": "Equipo portátil de alto rendimiento para gerencia y contabilidad",
                "cost_usd": 520.00,
                "price_1_usd": 790.00,
                "price_2_usd": 735.00,
                "price_3_usd": 690.00,
                "unit": "unid",
                "tax_exempt": False,
                "stock": 2,
                "min_stock": 5,
            },
        ]

        product_objs = []
        for p_data in demo_products:
            existing_p = (
                await db.execute(
                    select(Product).where(Product.sku == p_data["sku"], Product.tenant_id == tenant_id)
                )
            ).scalars().first()

            cost_ves = Decimal(str(round(p_data["cost_usd"] * rate, 4)))
            p1_ves = Decimal(str(round(p_data["price_1_usd"] * rate, 4)))
            p2_ves = Decimal(str(round(p_data["price_2_usd"] * rate, 4)))
            p3_ves = Decimal(str(round(p_data["price_3_usd"] * rate, 4)))

            if not existing_p:
                new_p = Product(
                    sku=p_data["sku"],
                    name=p_data["name"],
                    description=p_data["description"],
                    cost=cost_ves,
                    average_cost=cost_ves,
                    price=p1_ves,
                    price_2=p2_ves,
                    price_3=p3_ves,
                    min_stock=Decimal(str(p_data["min_stock"])),
                    max_stock=Decimal("500"),
                    unit_of_measure=p_data["unit"],
                    tax_exempt=p_data["tax_exempt"],
                    tax_rate=Decimal("0.0000") if p_data["tax_exempt"] else Decimal("16.0000"),
                    tenant_id=tenant_id,
                )
                db.add(new_p)
                await db.flush()

                stock_rec = StockSummary(
                    product_id=new_p.id,
                    warehouse_id=main_wh_id,
                    quantity=Decimal(str(p_data["stock"])),
                    min_stock=Decimal(str(p_data["min_stock"])),
                    tenant_id=tenant_id,
                )
                db.add(stock_rec)

                mov = StockMovement(
                    product_id=new_p.id,
                    warehouse_id=main_wh_id,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.INITIAL_BALANCE,
                    quantity=Decimal(str(p_data["stock"])),
                    reference="Inventario Inicial Demo Venezuela",
                    document_number="INI-0001",
                    notes="Carga inicial automatizada de demostración",
                    tenant_id=tenant_id,
                    created_by_name="Sistema Demo",
                )
                db.add(mov)
                product_objs.append(new_p)
                created_counts["products"] += 1
            else:
                existing_p.price = p1_ves
                existing_p.price_2 = p2_ves
                existing_p.price_3 = p3_ves
                existing_p.min_stock = Decimal(str(p_data["min_stock"]))
                st_res = await db.execute(
                    select(StockSummary).where(
                        StockSummary.product_id == existing_p.id,
                        StockSummary.warehouse_id == main_wh_id,
                    )
                )
                st_rec = st_res.scalars().first()
                if st_rec:
                    st_rec.min_stock = Decimal(str(p_data["min_stock"]))
                    if p_data["sku"] in ("TECH-UPS-005", "TECH-LAP-008"):
                        st_rec.quantity = Decimal(str(p_data["stock"]))
                product_objs.append(existing_p)

        # 3.1 Movimientos de Cargo (CHARGE), Descargo (DISCHARGE), Notas de Despacho y Auditoría de Inventario
        existing_charge = (
            await db.execute(
                select(StockMovement).where(
                    StockMovement.tenant_id == tenant_id,
                    StockMovement.movement_subtype == MovementSubtype.CHARGE,
                )
            )
        ).scalars().first()
        if not existing_charge and product_objs:
            db.add_all([
                StockMovement(
                    product_id=product_objs[2].id,
                    warehouse_id=main_wh_id,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.CHARGE,
                    quantity=Decimal("5"),
                    reference="CARGO-0001",
                    document_number="CG-00001",
                    notes="Entrada por sobrante verificado en recepción de mercancía",
                    tenant_id=tenant_id,
                    created_by_name="Jefe de Almacén Demo",
                ),
                StockMovement(
                    product_id=product_objs[3].id,
                    warehouse_id=main_wh_id,
                    movement_type=MovementType.OUT,
                    movement_subtype=MovementSubtype.DISCHARGE,
                    quantity=Decimal("2"),
                    reference="DESCARGO-0001",
                    document_number="DG-00001",
                    notes="Descargo por deterioro de empaque externo en traslado interno",
                    tenant_id=tenant_id,
                    created_by_name="Jefe de Almacén Demo",
                ),
            ])

        existing_dispatch = (
            await db.execute(select(DispatchNote).where(DispatchNote.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_dispatch and product_objs:
            dn_wh = DispatchNote(
                source_warehouse_id=main_wh_id,
                destination_warehouse_id=sec_wh_id,
                status="IN_TRANSIT",
                reference="ND-TRASLADO-0001",
                tenant_id=tenant_id,
                created_by_name="Coordinador Logístico Demo",
            )
            db.add(dn_wh)
            await db.flush()
            db.add(
                DispatchNoteItem(
                    dispatch_note_id=dn_wh.id,
                    product_id=product_objs[0].id,
                    quantity=Decimal("5"),
                    tenant_id=tenant_id,
                )
            )
            created_counts["dispatch_notes"] = 1

        existing_audit = (
            await db.execute(select(InventoryAudit).where(InventoryAudit.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_audit and product_objs:
            aud = InventoryAudit(
                warehouse_id=main_wh_id,
                name="Auditoría Física Mensual — Almacén Principal Caracas",
                status="COMPLETED",
                notes="Conteo físico verificado al 100% con lectores de código QR/2D",
                tenant_id=tenant_id,
                created_by_name="Auditor Interno Demo",
            )
            db.add(aud)
            await db.flush()
            db.add_all([
                InventoryAuditDetail(
                    audit_id=aud.id,
                    product_id=product_objs[0].id,
                    expected_quantity=Decimal("45"),
                    counted_quantity=Decimal("45"),
                    difference=Decimal("0"),
                    tenant_id=tenant_id,
                ),
                InventoryAuditDetail(
                    audit_id=aud.id,
                    product_id=product_objs[4].id,
                    expected_quantity=Decimal("4"),
                    counted_quantity=Decimal("4"),
                    difference=Decimal("0"),
                    tenant_id=tenant_id,
                ),
            ])
            created_counts["audits"] = 1

        # 4. Clientes Venezolanos Realistas
        demo_customers = [
            {
                "tax_id": "J-00045891-2",
                "name": "Automercados Plaza's, C.A.",
                "phone": "+58 (212) 945-8811",
                "email": "compras@elplazas.com",
                "address": "Av. Principal de Los Ruices, Centro Empresarial, Caracas",
                "credit_limit": Decimal("5000.0000"),
                "credit_days": 30,
            },
            {
                "tax_id": "J-50129481-3",
                "name": "Inversiones Tecnológicas El Rosal 2026, C.A.",
                "phone": "+58 (414) 289-4410",
                "email": "administracion@inversioneselrosal.com.ve",
                "address": "Av. Venezuela, Torre América, Piso 5, El Rosal, Caracas",
                "credit_limit": Decimal("3500.0000"),
                "credit_days": 15,
            },
            {
                "tax_id": "J-30948120-5",
                "name": "Grupo Farmacéutico San Ignacio, C.A.",
                "phone": "+58 (241) 824-1190",
                "email": "facturacion@farmaignacio.com.ve",
                "address": "Av. Bolívar Norte, Urb. La Alegría, Valencia, Edo. Carabobo",
                "credit_limit": Decimal("2500.0000"),
                "credit_days": 15,
            },
            {
                "tax_id": "V-18452910-4",
                "name": "Carlos Eduardo Rodríguez Méndez",
                "phone": "+58 (412) 910-3321",
                "email": "crodriguez.ve@gmail.com",
                "address": "Urb. Altamira Sur, Calle 3, Res. Ávila, Caracas",
                "credit_limit": Decimal("500.0000"),
                "credit_days": 0,
            },
        ]

        customer_objs = []
        for c_data in demo_customers:
            existing_c = (
                await db.execute(
                    select(Customer).where(Customer.tax_id == c_data["tax_id"], Customer.tenant_id == tenant_id)
                )
            ).scalars().first()
            if not existing_c:
                new_c = Customer(tenant_id=tenant_id, **c_data)
                db.add(new_c)
                await db.flush()
                customer_objs.append(new_c)
                created_counts["customers"] += 1
            else:
                customer_objs.append(existing_c)

        # 5. Proveedores Venezolanos
        demo_suppliers = [
            {
                "tax_id": "J-00192834-1",
                "name": "Distribuidora Mayorista de Tecnología Caracas, C.A.",
                "email": "ventas@mayoristatecccs.com.ve",
                "phone": "+58 (212) 239-7710",
                "address": "Zona Industrial Boleíta Norte, Calle E, Edif. Tecno, Caracas",
                "contact_person": "Ing. Roberto Baute",
                "bank_name": "Banesco Banco Universal",
                "bank_account": "0134-0031-88-0311094821",
                "payment_terms": "credito_30",
                "credit_days": 30,
                "is_withholding_agent": True,
            },
            {
                "tax_id": "J-30192845-6",
                "name": "Papelera e Insumos Industriales Carabobo, C.A.",
                "email": "despachos@papeleracarabobo.com.ve",
                "phone": "+58 (241) 832-5501",
                "address": "Zona Industrial Castillito, San Diego, Edo. Carabobo",
                "contact_person": "Lic. María Gabriela Pérez",
                "bank_name": "Banco Mercantil",
                "bank_account": "0105-0082-11-1082948120",
                "payment_terms": "credito_15",
                "credit_days": 15,
                "is_withholding_agent": True,
            },
        ]

        supplier_objs = []
        for s_data in demo_suppliers:
            existing_s = (
                await db.execute(
                    select(Supplier).where(Supplier.tax_id == s_data["tax_id"], Supplier.tenant_id == tenant_id)
                )
            ).scalars().first()
            if not existing_s:
                new_s = Supplier(tenant_id=tenant_id, **s_data)
                db.add(new_s)
                await db.flush()
                supplier_objs.append(new_s)
                created_counts["suppliers"] += 1
            else:
                supplier_objs.append(existing_s)

        # 6. Cuentas Bancarias (Bolívares y Divisas) + Caja Registradora
        existing_banks = (
            await db.execute(select(BankAccount).where(BankAccount.tenant_id == tenant_id))
        ).scalars().all()
        if not existing_banks:
            b1 = BankAccount(
                bank_name="Banesco Banco Universal (Cuenta Corriente Fiscal VES)",
                account_number="0134-0342-19-3421098412",
                account_type="corriente",
                currency="VES",
                holder_name="APEX CORP VENEZUELA DEMO, C.A.",
                holder_tax_id="J-41258963-0",
                initial_balance=Decimal("185400.0000"),
                current_balance=Decimal("185400.0000"),
                tenant_id=tenant_id,
            )
            b2 = BankAccount(
                bank_name="Banco Mercantil (Cuenta Recaudadora Pago Móvil VES)",
                account_number="0105-0192-44-1192837465",
                account_type="corriente",
                currency="VES",
                holder_name="APEX CORP VENEZUELA DEMO, C.A.",
                holder_tax_id="J-41258963-0",
                initial_balance=Decimal("94200.0000"),
                current_balance=Decimal("94200.0000"),
                tenant_id=tenant_id,
            )
            b3 = BankAccount(
                bank_name="Banesco Custodia / Zelle Corporativo (USD)",
                account_number="USD-CUSTODIA-001",
                account_type="divisas",
                currency="USD",
                holder_name="APEX CORP VENEZUELA DEMO, C.A.",
                holder_tax_id="J-41258963-0",
                initial_balance=Decimal("6450.0000"),
                current_balance=Decimal("6450.0000"),
                tenant_id=tenant_id,
            )
            db.add_all([b1, b2, b3])
            created_counts["bank_accounts"] = 3

        existing_cash_reg = (
            await db.execute(select(CashRegister).where(CashRegister.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_cash_reg:
            db.add(
                CashRegister(
                    name="Caja Principal POS #01 — Sede Caracas",
                    computer_uid=f"POS-DEMO-T{tenant_id}-01",
                    is_active=1,
                    tenant_id=tenant_id,
                )
            )

        # 7. Ventas / Facturas Fiscales SENIAT de Demostración + CxC
        existing_sales = (
            await db.execute(select(Sale).where(Sale.tenant_id == tenant_id))
        ).scalars().all()
        first_sale_id = existing_sales[0].id if existing_sales else None
        if not existing_sales and product_objs and customer_objs:
            s1 = Sale(
                customer_id=customer_objs[0].id,
                warehouse_id=main_wh_id,
                subtotal=Decimal("360.0000"),
                tax_total=Decimal("68.1120"),
                igtf_amount=Decimal("12.5280"),
                discount_total=Decimal("0.0000"),
                total=Decimal("430.1280"),
                payment_method="cash",
                currency="USD",
                exchange_rate=Decimal(str(rate)),
                status="COMPLETED",
                fiscal_invoice_number="00000001",
                control_number="00-00000001",
                notes="Factura Fiscal Demo emitida con Precio 1 y pago en Divisas (IGTF 3%)",
                tenant_id=tenant_id,
                created_by_name="Administrador Demo",
            )
            db.add(s1)
            await db.flush()
            first_sale_id = s1.id
            db.add_all([
                SaleDetail(
                    sale_id=s1.id,
                    product_id=product_objs[0].id,
                    quantity=Decimal("2"),
                    unit_price=Decimal("115.0000"),
                    subtotal=Decimal("230.0000"),
                    tenant_id=tenant_id,
                ),
                SaleDetail(
                    sale_id=s1.id,
                    product_id=product_objs[1].id,
                    quantity=Decimal("1"),
                    unit_price=Decimal("130.0000"),
                    subtotal=Decimal("130.0000"),
                    tenant_id=tenant_id,
                ),
            ])

            s2 = Sale(
                customer_id=customer_objs[1].id,
                warehouse_id=main_wh_id,
                subtotal=Decimal("520.0000"),
                tax_total=Decimal("83.2000"),
                igtf_amount=Decimal("0.0000"),
                discount_total=Decimal("0.0000"),
                total=Decimal("603.2000"),
                payment_method="credit",
                currency="USD",
                exchange_rate=Decimal(str(rate)),
                status="COMPLETED",
                fiscal_invoice_number="00000002",
                control_number="00-00000002",
                notes="Venta al Mayor (Precio 2) a Crédito 15 días",
                tenant_id=tenant_id,
                created_by_name="Administrador Demo",
            )
            db.add(s2)
            await db.flush()
            db.add(
                SaleDetail(
                    sale_id=s2.id,
                    product_id=product_objs[3].id,
                    quantity=Decimal("10"),
                    unit_price=Decimal("52.0000"),
                    subtotal=Decimal("520.0000"),
                    tenant_id=tenant_id,
                )
            )
            db.add(
                AccountsReceivable(
                    sale_id=s2.id,
                    customer_id=customer_objs[1].id,
                    total_amount=Decimal("603.2000"),
                    remaining_amount=Decimal("403.2000"),
                    due_date=datetime.now(timezone.utc) + timedelta(days=15),
                    status=DebtStatus.PARTIAL,
                    notes="Abono inicial recibido de $200.00 USD; saldo pendiente a 15 días",
                    tenant_id=tenant_id,
                )
            )
            created_counts["sales"] = 2

        # 8. Presupuesto / Cotización, Nota de Entrega, Nota de Crédito y Nota de Débito
        existing_budgets = (
            await db.execute(select(Budget).where(Budget.tenant_id == tenant_id))
        ).scalars().all()
        if not existing_budgets and product_objs and customer_objs:
            b_demo = Budget(
                customer_id=customer_objs[2].id,
                subtotal=Decimal("980.0000"),
                tax_total=Decimal("156.8000"),
                total=Decimal("1136.8000"),
                currency="USD",
                status="PENDING",
                valid_until=(date.today() + timedelta(days=15)).isoformat(),
                notes="Cotización Corporativa con Tarifa Preferencial (Precio 2)",
                tenant_id=tenant_id,
                created_by_name="Ejecutivo de Ventas Demo",
            )
            db.add(b_demo)
            await db.flush()
            db.add(
                BudgetItem(
                    budget_id=b_demo.id,
                    product_id=product_objs[0].id,
                    quantity=Decimal("10"),
                    unit_price=Decimal("98.0000"),
                    subtotal=Decimal("980.0000"),
                    tenant_id=tenant_id,
                )
            )
            created_counts["budgets"] = 1

        existing_deliv = (
            await db.execute(select(DeliveryNote).where(DeliveryNote.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_deliv and product_objs and customer_objs:
            dn_sale = DeliveryNote(
                customer_id=customer_objs[0].id,
                sale_id=first_sale_id,
                status="DELIVERED",
                delivery_address=customer_objs[0].address,
                tenant_id=tenant_id,
                created_by_name="Despachos Demo",
            )
            db.add(dn_sale)
            await db.flush()
            db.add(
                DeliveryNoteItem(
                    delivery_note_id=dn_sale.id,
                    product_id=product_objs[0].id,
                    quantity=Decimal("2"),
                    tenant_id=tenant_id,
                )
            )
            created_counts["delivery_notes"] = 1

        existing_cn = (
            await db.execute(select(CreditNote).where(CreditNote.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_cn and product_objs and customer_objs:
            cn = CreditNote(
                number="NC-000001",
                customer_id=customer_objs[0].id,
                reference_invoice_id=first_sale_id,
                subtotal=Decimal("52.0000"),
                tax_amount=Decimal("8.3200"),
                total=Decimal("60.3200"),
                fiscal_number="NC-00000001",
                control_number="00-00000091",
                reason="Descuento pronto pago / ajuste comercial autorizado sobre factura fiscal",
                status="ACTIVE",
                affects_inventory=False,
                warehouse_id=main_wh_id,
                tenant_id=tenant_id,
                created_by_name="Facturación Demo",
            )
            db.add(cn)
            await db.flush()
            db.add(
                CreditNoteItem(
                    credit_note_id=cn.id,
                    product_id=product_objs[2].id,
                    quantity=Decimal("1"),
                    unit_price=Decimal("52.0000"),
                    subtotal=Decimal("52.0000"),
                    tenant_id=tenant_id,
                )
            )
            created_counts["credit_notes"] = 1

        existing_dn = (
            await db.execute(select(DebitNote).where(DebitNote.tenant_id == tenant_id))
        ).scalars().first()
        if not existing_dn and customer_objs:
            db.add(
                DebitNote(
                    number="ND-000001",
                    control_number="00-00000105",
                    type="Débito",
                    customer_id=customer_objs[1].id,
                    reference_invoice_id=first_sale_id,
                    amount=Decimal("35.0000"),
                    reason="Recargo por flete expreso asegurado Caracas - El Rosal",
                    status="UNPAID",
                    tenant_id=tenant_id,
                    created_by_name="Facturación Demo",
                )
            )
            created_counts["debit_notes"] = 1

        # 9. Orden de Compra con Retención de IVA (75% SENIAT) y CxP
        existing_purchases = (
            await db.execute(select(Purchase).where(Purchase.tenant_id == tenant_id))
        ).scalars().all()
        if not existing_purchases and product_objs and supplier_objs:
            p_demo = Purchase(
                supplier_id=supplier_objs[0].id,
                warehouse_id=main_wh_id,
                status=PurchaseStatus.COMPLETED,
                subtotal=Decimal("650.0000"),
                tax_total=Decimal("104.0000"),
                total=Decimal("754.0000"),
                reference="OC-DEMO-0001",
                invoice_number="FAC-00084921",
                control_number="00-00849210",
                iva_withholding=Decimal("78.0000"),
                islr_withholding=Decimal("13.0000"),
                payment_method="credit",
                exchange_rate=Decimal(str(rate)),
                currency="USD",
                notes="Orden de Compra con Comprobante de Retención de IVA (75%) SNAT/2015/0049",
                tenant_id=tenant_id,
                created_by_name="Compras Demo",
            )
            db.add(p_demo)
            await db.flush()
            db.add(
                PurchaseDetail(
                    purchase_id=p_demo.id,
                    product_id=product_objs[0].id,
                    quantity=Decimal("10"),
                    received_quantity=Decimal("10"),
                    cost_price=Decimal("65.0000"),
                    subtotal=Decimal("650.0000"),
                    tenant_id=tenant_id,
                )
            )
            db.add(
                AccountsPayable(
                    purchase_id=p_demo.id,
                    supplier_id=supplier_objs[0].id,
                    total_amount=Decimal("663.0000"),
                    remaining_amount=Decimal("663.0000"),
                    due_date=datetime.now(timezone.utc) + timedelta(days=30),
                    status=DebtStatus.OPEN,
                    notes="Factura proveedor neta de retenciones de IVA (75%) e ISLR",
                    tenant_id=tenant_id,
                )
            )
            created_counts["purchases"] = 1

        # 10. Contabilidad VEN-NIF: Plan Único de Cuentas y Asientos del Libro Diario
        existing_accs = (
            await db.execute(select(Account).where(Account.tenant_id == tenant_id))
        ).scalars().all()
        if not existing_accs:
            acc1 = Account(code="1.1.01.01", name="Caja y Bancos Nacionales (Banesco / Mercantil)", type="Activo", balance=Decimal("6450.0000"), tenant_id=tenant_id)
            acc2 = Account(code="1.1.02.01", name="Cuentas por Cobrar Comerciales Clientes", type="Activo", balance=Decimal("403.2000"), tenant_id=tenant_id)
            acc3 = Account(code="1.1.03.01", name="Inventario de Mercancías para la Venta", type="Activo", balance=Decimal("14850.0000"), tenant_id=tenant_id)
            acc4 = Account(code="2.1.01.01", name="Cuentas por Pagar Proveedores Nacionales", type="Pasivo", balance=Decimal("663.0000"), tenant_id=tenant_id)
            acc5 = Account(code="2.1.02.01", name="Débito Fiscal IVA (16% SENIAT)", type="Pasivo", balance=Decimal("151.3120"), tenant_id=tenant_id)
            acc6 = Account(code="3.1.01.01", name="Capital Social Suscrito y Pagado", type="Capital", balance=Decimal("20000.0000"), tenant_id=tenant_id)
            acc7 = Account(code="4.1.01.01", name="Ingresos por Ventas de Mercancías y Equipos", type="Ingreso", balance=Decimal("880.0000"), tenant_id=tenant_id)
            acc8 = Account(code="5.1.01.01", name="Costo de Ventas y Operación Comercial", type="Gasto", balance=Decimal("415.0000"), tenant_id=tenant_id)
            db.add_all([acc1, acc2, acc3, acc4, acc5, acc6, acc7, acc8])
            await db.flush()
            created_counts["accounts"] = 8

            je = JournalEntry(
                date=datetime.now(timezone.utc),
                reference="ASI-DEMO-0001",
                description="Asiento contable automático por facturación fiscal SENIAT #00000001 y #00000002",
                status=JournalEntryStatus.POSTED.value,
                currency="USD",
                exchange_rate=Decimal(str(rate)),
                tenant_id=tenant_id,
                created_by_name="Contabilidad Demo",
            )
            db.add(je)
            await db.flush()
            db.add_all([
                JournalEntryDetail(journal_entry_id=je.id, account_id=acc1.id, debit=Decimal("430.1280"), credit=Decimal("0.0000"), tenant_id=tenant_id),
                JournalEntryDetail(journal_entry_id=je.id, account_id=acc2.id, debit=Decimal("603.2000"), credit=Decimal("0.0000"), tenant_id=tenant_id),
                JournalEntryDetail(journal_entry_id=je.id, account_id=acc7.id, debit=Decimal("0.0000"), credit=Decimal("880.0000"), tenant_id=tenant_id),
                JournalEntryDetail(journal_entry_id=je.id, account_id=acc5.id, debit=Decimal("0.0000"), credit=Decimal("153.3280"), tenant_id=tenant_id),
            ])
            created_counts["journal_entries"] = 1

        # 11. Empleados y Nómina LOTTT Venezuela
        existing_emps = (
            await db.execute(select(Employee).where(Employee.id > 0))
        ).scalars().all()
        if not existing_emps:
            emp1 = Employee(
                first_name="Valentina",
                last_name="Mendoza Bolívar",
                national_id="V-20491823",
                rif="V-20491823-1",
                email="vmendoza@apexdemo.com.ve",
                phone="+58 (414) 321-8890",
                address="Urb. Los Dos Caminos, Caracas",
                job_title="Gerente de Administración y Finanzas",
                department="Administración",
                hire_date=date(2023, 2, 1),
                salary_usd=Decimal("450.0000"),
                salary_ves=Decimal(str(round(450.0 * rate, 2))),
                currency="USD",
                payment_frequency="BIWEEKLY",
                cestaticket_usd=Decimal("40.0000"),
                bank_name="Banesco",
                bank_account="0134-0031-12-0319283741",
                applies_sso=True,
                applies_rpe=True,
                applies_faov=True,
                is_active=True,
            )
            emp2 = Employee(
                first_name="Alejandro",
                last_name="Castillo Rivas",
                national_id="V-24819203",
                rif="V-24819203-7",
                email="acastillo@apexdemo.com.ve",
                phone="+58 (412) 554-1920",
                address="Urb. La Candelaria, Caracas",
                job_title="Coordinador de Almacén y Facturación POS",
                department="Operaciones",
                hire_date=date(2024, 1, 15),
                salary_usd=Decimal("280.0000"),
                salary_ves=Decimal(str(round(280.0 * rate, 2))),
                currency="USD",
                payment_frequency="BIWEEKLY",
                cestaticket_usd=Decimal("40.0000"),
                bank_name="Banco Mercantil",
                bank_account="0105-0019-98-1019283746",
                applies_sso=True,
                applies_rpe=True,
                applies_faov=True,
                is_active=True,
            )
            db.add_all([emp1, emp2])
            await db.flush()

            period = PayrollPeriod(
                code="NOM-2026-Q1",
                name="Primera Quincena del Mes (LOTTT)",
                start_date=date.today().replace(day=1),
                end_date=date.today().replace(day=15),
                period_type="BIWEEKLY",
                exchange_rate=Decimal(str(rate)),
                status="APPROVED",
            )
            db.add(period)
            await db.flush()

            total_sal = Decimal("0")
            total_cesta = Decimal("0")
            total_ded = Decimal("0")
            total_net = Decimal("0")

            for idx, emp in enumerate([emp1, emp2], start=1):
                base_ves = Decimal(str(round((float(emp.salary_usd) / 2.0) * rate, 2)))
                cesta_ves = Decimal(str(round((float(emp.cestaticket_usd) / 2.0) * rate, 2)))
                sso_ves = Decimal(str(round(float(base_ves) * 0.04, 2)))
                rpe_ves = Decimal(str(round(float(base_ves) * 0.005, 2)))
                faov_ves = Decimal(str(round(float(base_ves) * 0.01, 2)))
                earn_ves = base_ves + cesta_ves
                ded_ves = sso_ves + rpe_ves + faov_ves
                net_ves = earn_ves - ded_ves
                net_usd = Decimal(str(round(float(net_ves) / rate, 2)))

                db.add(
                    PayrollReceipt(
                        payroll_period_id=period.id,
                        employee_id=emp.id,
                        receipt_number=f"REC-{period.id:03d}-{idx:04d}",
                        base_salary_ves=base_ves,
                        cestaticket_ves=cesta_ves,
                        other_bonuses_ves=Decimal("0"),
                        total_earnings_ves=earn_ves,
                        sso_deduction_ves=sso_ves,
                        rpe_deduction_ves=rpe_ves,
                        faov_deduction_ves=faov_ves,
                        other_deductions_ves=Decimal("0"),
                        total_deductions_ves=ded_ves,
                        net_amount_ves=net_ves,
                        net_amount_usd=net_usd,
                        exchange_rate=Decimal(str(rate)),
                        status="PAID",
                    )
                )
                total_sal += base_ves
                total_cesta += cesta_ves
                total_ded += ded_ves
                total_net += net_ves

            period.total_salaries_ves = total_sal
            period.total_cestaticket_ves = total_cesta
            period.total_deductions_ves = total_ded
            period.total_net_ves = total_net
            created_counts["employees"] = 2

        # 12. Movimientos Globales Demo (para el Monitor en Vivo y Auditoría de Reportes)
        existing_movs = (
            await db.execute(select(SystemMovement).where(SystemMovement.tenant_id == tenant_id))
        ).scalars().all()
        if not existing_movs:
            db.add_all([
                SystemMovement(
                    tenant_id=tenant_id,
                    module="SALES",
                    operation="SALE",
                    entity_type="Sale",
                    reference="FAC-00000001",
                    description="Factura Fiscal SENIAT #00000001 emitida a Automercados Plaza's, C.A. (Tarifa P1 + IGTF 3%)",
                    amount=Decimal("430.1280"),
                    currency="USD",
                    user_name="Administrador Demo",
                    user_email="admin@apexdemo.com.ve",
                    ip_address="190.73.114.28",
                    user_agent="Chrome 131 / Windows 11 Pro (Caja Principal Caracas)",
                ),
                SystemMovement(
                    tenant_id=tenant_id,
                    module="SALES",
                    operation="SALE",
                    entity_type="Sale",
                    reference="FAC-00000002",
                    description="Factura Mayorista #00000002 a Crédito 15 días — Inversiones Tecnológicas El Rosal 2026, C.A.",
                    amount=Decimal("603.2000"),
                    currency="USD",
                    user_name="Administrador Demo",
                    user_email="admin@apexdemo.com.ve",
                    ip_address="190.73.114.28",
                    user_agent="Chrome 131 / Windows 11 Pro (Facturación Legal)",
                ),
                SystemMovement(
                    tenant_id=tenant_id,
                    module="PURCHASES",
                    operation="PURCHASE",
                    entity_type="Purchase",
                    reference="OC-DEMO-0001",
                    description="Orden de Compra OC-DEMO-0001 recibida con Retención IVA 75% (SNAT/2015/0049)",
                    amount=Decimal("754.0000"),
                    currency="USD",
                    user_name="Compras Demo",
                    user_email="compras@apexdemo.com.ve",
                    ip_address="186.185.42.19",
                    user_agent="Edge 131 / Windows 11 (Almacén Chacao)",
                ),
                SystemMovement(
                    tenant_id=tenant_id,
                    module="INVENTORY",
                    operation="CHARGE",
                    entity_type="Warehouse",
                    reference="ALM-CHACAO",
                    description="Configuración de Stock Mínimo y Alarma de Reposición en Almacén Principal Caracas",
                    quantity=Decimal("8"),
                    unit="ítems",
                    user_name="Administrador Demo",
                    user_email="admin@apexdemo.com.ve",
                    ip_address="190.73.114.28",
                    user_agent="Chrome 131 / Windows 11 Pro",
                ),
            ])

        await db.commit()
        return {
            "status": "success",
            "message": "Todos los módulos del ERP han sido poblados con datos de demostración venezolanos.",
            "exchange_rate_bcv": rate,
            "created": created_counts,
        }
