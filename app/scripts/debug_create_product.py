import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.core.database import get_tenant_engine
from app.domain.inventory import Product
from app.schemas.inventory import ProductCreate

async def debug_create():
    tenant_id = 3
    engine = get_tenant_engine(tenant_id)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        try:
            print("Attempting to create product...")
            product_in = ProductCreate(
                name="Producto de Prueba",
                sku="TEST-SKU-9999",
                price=10.5,
                cost=5.0,
                track_batches=False,
                track_expiry=False,
                min_stock=1.0,
                max_stock=100.0,
                unit_of_measure="unit",
                category_id=None
            )
            
            new_product = Product(**product_in.model_dump(), tenant_id=tenant_id)
            db.add(new_product)
            await db.commit()
            print("Successfully committed product!")
            
        except Exception as e:
            print("\n!!! ERROR OCCURRED !!!")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_create())
