import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import MasterSessionLocal
from app.domain.tenant import Tenant
from datetime import datetime

async def extend_licenses():
    print("Connecting to master database to update tenant licenses...")
    async with MasterSessionLocal() as db:
        # Fetch all tenants
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        
        print(f"Found {len(tenants)} tenants in database.")
        
        # Set subscription end to 2036-12-31 and make sure they are active
        target_date = datetime(2036, 12, 31, 23, 59, 59)
        for t in tenants:
            print(f"Updating Tenant: {t.name} (Current subscription: {t.subscription_end}, Current active: {t.is_active})")
            t.is_active = True
            t.subscription_end = target_date
        
        await db.commit()
        print("All tenant licenses have been successfully extended to 2036-12-31 and activated!")

if __name__ == "__main__":
    asyncio.run(extend_licenses())
