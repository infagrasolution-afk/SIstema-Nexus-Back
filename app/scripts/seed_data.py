import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import MasterSessionLocal, init_tenant_db, master_engine, Base
from app.domain.tenant import Tenant
from app.domain.user import User
from app.core.security import get_password_hash
from datetime import datetime, timedelta

async def seed():
    # 1. Initialize Master DB Tables
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with MasterSessionLocal() as db:
        # 2. Create Default Tenant in Master
        company_name = "APEX ERP Demo"
        tenant = Tenant(
            name=company_name,
            email="admin@erp.com",
            license_key="DEMO-12345",
            subscription_end=datetime.utcnow() + timedelta(days=365)
        )
        db.add(tenant)
        await db.flush()

        # 3. Create Admin User in Master
        admin = User(
            email="admin@erp.com",
            hashed_password=get_password_hash("admin123_password"),
            is_active=True,
            is_superuser=True,
            tenant_id=tenant.id
        )
        db.add(admin)
        await db.commit()
        
        # 4. Initialize the Tenant-Specific DB file (e.g., N_E_D_1.db)
        await init_tenant_db(tenant.id, company_name)
        
        print(f"Master and Tenant ({company_name}) databases initialized successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
