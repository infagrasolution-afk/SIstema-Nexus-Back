import asyncio
import os
from app.core.database import MasterSessionLocal, master_engine, Base, get_tenant_engine
from app.domain.cash import CashRegister, CashSession
from app.domain.sales import Sale

async def update_all_databases():
    print("Updating Master Database...")
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Updating Tenant Databases...")
    for file in os.listdir("."):
        if file.endswith(".db") and not file.startswith("master"):
            # Extract tenant_id from filename (e.g. TEN_1.db)
            try:
                parts = file.replace(".db", "").split("_")
                tenant_id = int(parts[-1])
                print(f"Updating {file} (Tenant {tenant_id})...")
                engine = get_tenant_engine(tenant_id)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as e:
                print(f"Error updating {file}: {e}")

if __name__ == "__main__":
    asyncio.run(update_all_databases())
