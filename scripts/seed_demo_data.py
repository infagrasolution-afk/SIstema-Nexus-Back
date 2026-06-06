import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add parent path to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.core.database import get_tenant_engine, async_sessionmaker, AsyncSession
from app.domain.inventory import Category, Product, Warehouse, StockSummary
from app.domain.sales import Customer, TaxRate, Sale, SaleDetail
from app.domain.purchases import Supplier

async def seed():
    tenant_id = 3
    print("Connecting to PostgreSQL database schema for tenant_3...")
    # Create session for tenant_3
    engine = get_tenant_engine(tenant_id)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with Session() as db:
        print("Ensuring database columns exist...")
        try:
            # PostgreSQL supports ADD COLUMN IF NOT EXISTS
            await db.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS fiscal_invoice_number VARCHAR"))
            await db.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS printer_serial VARCHAR"))
            await db.commit()
            print("Columns fiscal_invoice_number and printer_serial verified/added successfully.")
        except Exception as e:
            await db.rollback()
            print(f"Error checking/adding columns: {e}")

        # Clean previous seed data to avoid mixed currencies and stale records
        print("Cleaning previous seed data for tenant_3...")
        try:
            await db.execute(text("DELETE FROM sale_details WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM sales WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM stock_movements WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM stock_summary WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM products WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM customers WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.execute(text("DELETE FROM suppliers WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await db.commit()
            print("Previous seed data cleaned successfully.")
        except Exception as e:
            await db.rollback()
            print(f"Error cleaning seed data: {e}")

        print("Seeding Category...")
        # Get or create Category
        res = await db.execute(select(Category).where(Category.tenant_id == tenant_id))
        category = res.scalars().first()
        if not category:
            category = Category(name="Tecnología", description="Equipos electrónicos y accesorios", tenant_id=tenant_id)
            db.add(category)
            await db.commit()
            await db.refresh(category)
            print(f"Created category: {category.name}")
            
        print("Seeding Warehouse...")
        # Get or create Warehouse
        res = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id))
        warehouse = res.scalars().first()
        if not warehouse:
            warehouse = Warehouse(name="Almacén Principal", address="Sede Central", is_active=True, tenant_id=tenant_id)
            db.add(warehouse)
            await db.commit()
            await db.refresh(warehouse)
            print(f"Created warehouse: {warehouse.name}")

        print("Seeding TaxRate...")
        # Get or create TaxRate
        res = await db.execute(select(TaxRate).where(TaxRate.tenant_id == tenant_id))
        tax_rate = res.scalars().first()
        if not tax_rate:
            tax_rate = TaxRate(name="IVA 16%", rate=16.0, tenant_id=tenant_id)
            db.add(tax_rate)
            await db.commit()
            await db.refresh(tax_rate)
            print(f"Created tax rate: {tax_rate.name}")

        print("Seeding 10 Suppliers...")
        suppliers_data = [
            ("Distribuidora Global C.A.", "J-30123456-1", "contacto@distglobal.com", "+58 212-5551234", "Av. Francisco de Miranda, Caracas"),
            ("Tecnología Mayorista S.A.", "J-30234567-2", "ventas@tecnomayor.com", "+58 212-5552345", "Zona Industrial La Yaguara, Caracas"),
            ("Suministros Industriales 2020", "J-30345678-3", "info@sumind2020.com", "+58 241-5553456", "Zona Industrial Valencia, Carabobo"),
            ("Alimentos y Bebidas del Centro", "J-30456789-4", "pedidos@alcentro.com", "+58 243-5554567", "Av. Bolívar, Maracay, Aragua"),
            ("Corporación Importadora Express", "J-30567890-5", "admin@corpimport.com", "+58 261-5555678", "Av. Bella Vista, Maracaibo, Zulia"),
            ("Papelería y Oficina El Lápiz", "J-30678901-6", "ventas@ellapiz.com", "+58 251-5556789", "Carrera 19, Barquisimeto, Lara"),
            ("Equipos Médicos de Oriente", "J-30789012-7", "contacto@medoriente.com", "+58 281-5557890", "Av. Intercomunal, Barcelona, Anzoátegui"),
            ("Consorcio Textil Venezolano", "J-30890123-8", "info@contextven.com", "+58 212-5558901", "La Candelaria, Caracas"),
            ("Ferretería El Tornillo C.A.", "J-30901234-9", "ventas@eltornillo.com", "+58 276-5559012", "Av. 5 de Julio, San Cristóbal, Táchira"),
            ("Químicos del Caribe S.A.", "J-31012345-0", "contacto@quimcaribe.com", "+58 286-5550123", "Zona Industrial Matanzas, Puerto Ordaz, Bolívar"),
        ]
        
        suppliers = []
        for name, tax_id, email, phone, address in suppliers_data:
            # Check if tax_id exists
            res = await db.execute(select(Supplier).where(Supplier.tax_id == tax_id, Supplier.tenant_id == tenant_id))
            supp = res.scalars().first()
            if not supp:
                supp = Supplier(name=name, tax_id=tax_id, email=email, phone=phone, address=address, tenant_id=tenant_id)
                db.add(supp)
                await db.commit()
                await db.refresh(supp)
                print(f"Created Supplier: {name}")
            suppliers.append(supp)

        print("Seeding 10 Customers...")
        customers_data = [
            ("Juan Carlos Pérez", "V-12345678", "juan.perez@gmail.com", "+58 412-1112233", "Chacao, Caracas"),
            ("María Alejandra Gómez", "V-15678901", "maria.gomez@hotmail.com", "+58 414-2223344", "El Hatillo, Caracas"),
            ("Pedro José Rodríguez", "V-8765432", "pedro.rod@yahoo.com", "+58 416-3334455", "San Bernardino, Caracas"),
            ("Comercializadora Fénix C.A.", "J-40123456-7", "compras@fenixca.com", "+58 212-4445566", "Av. Libertador, Caracas"),
            ("Inversiones El Sol R.L.", "J-40234567-8", "info@inver-elsol.com", "+58 241-5556677", "Naguanagua, Carabobo"),
            ("Ana Karina Mendoza", "V-18901234", "ana.mendoza@gmail.com", "+58 424-6667788", "Lechería, Anzoátegui"),
            ("Supermercado Mi Futuro", "J-40345678-9", "gerencia@mifuturo.com", "+58 261-7778899", "Av. Delicias, Maracaibo, Zulia"),
            ("Carlos Eduardo Silva", "V-9876543", "carlos.silva@outlook.com", "+58 412-8889900", "Mérida, Estado Mérida"),
            ("Constructora El Pilar S.A.", "J-40456789-0", "proyectos@elpilar.com", "+58 251-9990011", "Cabudare, Lara"),
            ("Laura Cristina Díaz", "V-21345678", "laura.diaz@gmail.com", "+58 414-0001122", "San Diego, Carabobo"),
        ]
        
        customers = []
        for name, tax_id, email, phone, address in customers_data:
            res = await db.execute(select(Customer).where(Customer.tax_id == tax_id, Customer.tenant_id == tenant_id))
            cust = res.scalars().first()
            if not cust:
                cust = Customer(name=name, tax_id=tax_id, email=email, phone=phone, address=address, tenant_id=tenant_id)
                db.add(cust)
                await db.commit()
                await db.refresh(cust)
                print(f"Created Customer: {name}")
            customers.append(cust)

        print("Seeding 10 Products...")
        products_data = [
            ("Laptop Dell Inspiron 15", "PROD-DELL-15", "Laptop Dell 15.6 pulgadas, Core i5, 8GB RAM, 256GB SSD", 650.0, 500.0),
            ("Smartphone Samsung Galaxy S23", "PROD-SAMS-S23", "Samsung Galaxy S23, 128GB, Color Negro", 850.0, 680.0),
            ("Monitor LG UltraGear 27", "PROD-LG-27", "Monitor Gaming LG 27 pulgadas, IPS 144Hz", 280.0, 210.0),
            ("Teclado Mecánico Redragon", "PROD-RED-K552", "Teclado mecánico retroiluminado RGB, Switch Blue", 45.0, 32.0),
            ("Mouse Inalámbrico Logitech", "PROD-LOGI-M185", "Mouse óptico inalámbrico, batería 12 meses", 20.0, 12.0),
            ("Auriculares Sony WH-1000XM4", "PROD-SONY-XM4", "Auriculares inalámbricos con cancelación de ruido", 320.0, 240.0),
            ("Impresora Multifuncional HP", "PROD-HP-DESK", "Impresora HP DeskJet inyección térmica de tinta", 110.0, 85.0),
            ("Disco Duro Externo 1TB", "PROD-TOSH-1TB", "Disco duro portátil Toshiba Canvio 1TB USB 3.0", 65.0, 48.0),
            ("Tarjeta Madre ASUS Rog Strix", "PROD-ASUS-ROG", "Placa base ASUS ROG Strix B550-F Gaming", 195.0, 150.0),
            ("Fuente de Poder EVGA 600W", "PROD-EVGA-600", "Fuente de alimentación EVGA 600W 80 Plus Bronze", 75.0, 55.0),
        ]
        
        products = []
        rate = 36.5
        for name, sku, desc, price, cost in products_data:
            res = await db.execute(select(Product).where(Product.sku == sku, Product.tenant_id == tenant_id))
            prod = res.scalars().first()
            if not prod:
                price_bs = price * rate
                cost_bs = cost * rate
                prod = Product(
                    name=name, sku=sku, description=desc, price=price_bs, cost=cost_bs, average_cost=cost_bs,
                    category_id=category.id, unit_of_measure="unid", tenant_id=tenant_id,
                    track_batches=False, track_expiry=False, track_serials=False
                )
                db.add(prod)
                await db.commit()
                await db.refresh(prod)
                print(f"Created Product: {name}")
            products.append(prod)

        print("Seeding Stock Summary...")
        for prod in products:
            res = await db.execute(select(StockSummary).where(StockSummary.product_id == prod.id, StockSummary.warehouse_id == warehouse.id, StockSummary.tenant_id == tenant_id))
            summary = res.scalars().first()
            if not summary:
                summary = StockSummary(
                    product_id=prod.id, warehouse_id=warehouse.id, quantity=50.0, tenant_id=tenant_id
                )
                db.add(summary)
                await db.commit()
                print(f"Added stock for {prod.name}")

        print("Seeding 10 Sales...")
        # Check if sales already exist
        res = await db.execute(select(Sale).where(Sale.tenant_id == tenant_id))
        sales_exist = len(res.scalars().all())
        
        if sales_exist < 10:
            for i in range(10):
                cust = customers[i % len(customers)]
                prod1 = products[i % len(products)]
                prod2 = products[(i + 1) % len(products)]
                
                subtotal = prod1.price + prod2.price
                tax_total = subtotal * (tax_rate.rate / 100)
                total = subtotal + tax_total
                
                pm = "cash" if i % 3 == 0 else ("card" if i % 3 == 1 else "transfer")
                date_offset = datetime.utcnow() - timedelta(days=i)
                
                sale = Sale(
                    customer_id=cust.id,
                    subtotal=subtotal,
                    tax_total=tax_total,
                    total=total,
                    payment_method=pm,
                    currency="USD",
                    exchange_rate=36.5,
                    is_accounted=False,
                    status="COMPLETED",
                    tenant_id=tenant_id,
                    created_at=date_offset
                )
                db.add(sale)
                await db.commit()
                await db.refresh(sale)
                
                detail1 = SaleDetail(
                    sale_id=sale.id,
                    product_id=prod1.id,
                    quantity=1.0,
                    unit_price=prod1.price,
                    tax_rate_id=tax_rate.id,
                    subtotal=prod1.price,
                    tenant_id=tenant_id
                )
                detail2 = SaleDetail(
                    sale_id=sale.id,
                    product_id=prod2.id,
                    quantity=1.0,
                    unit_price=prod2.price,
                    tax_rate_id=tax_rate.id,
                    subtotal=prod2.price,
                    tenant_id=tenant_id
                )
                db.add(detail1)
                db.add(detail2)
                await db.commit()
                print(f"Created Sale #{sale.id} for {cust.name}")

        print("All Seeding Completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
