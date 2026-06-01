import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import MasterSessionLocal, Base, master_engine as engine
from app.core.security import get_password_hash
from app.domain.user import User
from app.domain.tenant import Tenant
import app.domain.inventory # Load models
import app.domain.sales
import app.domain.purchases

async def create_superuser():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with MasterSessionLocal() as db:
        # 1. Create a Primary Tenant if none exists
        result = await db.execute(select(Tenant).where(Tenant.id == 1))
        tenant = result.scalars().first()
        
        if not tenant:
            tenant = Tenant(
                id=1,
                name="APEX MASTER CORP",
                email="admin@apexerp.com",
                license_key=f"MASTER-{uuid.uuid4().hex[:8].upper()}",
                subscription_end=datetime.now() + timedelta(days=3650), # 10 years
                is_active=True
            )
            db.add(tenant)
            await db.flush()
            print(f"Created Master Tenant: {tenant.name}")
        
        # 2. Create Superuser
        username = "admin"
        password = "aa11..**"
        
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        if not user:
            user = User(
                username=username,
                email="admin@erp.com",
                hashed_password=get_password_hash(password),
                is_superuser=True,
                is_active=True,
                tenant_id=tenant.id
            )
            db.add(user)
            await db.commit()
            print(f"--- SUPERUSER CREATED ---")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print(f"Tenant ID: {tenant.id}")
        else:
            print(f"User {username} already exists.")

if __name__ == "__main__":
    asyncio.run(create_superuser())
