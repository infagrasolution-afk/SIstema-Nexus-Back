import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a.virginia-postgres.render.com/erp_db_x91k"

async def verify_krishop():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, sku, name FROM products WHERE tenant_id = 2"))
        rows = res.fetchall()
        print(f"Cantidad de productos en KPRISHOP: {len(rows)}")
        for row in rows:
            print(f"- SKU: {row[1]}, Nombre: {row[2]}")

if __name__ == "__main__":
    asyncio.run(verify_krishop())
