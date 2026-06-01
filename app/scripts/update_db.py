import asyncio
import os
from sqlalchemy import select, text
from app.core.database import MasterSessionLocal, master_engine, Base, get_tenant_engine
from app.domain.tenant import Tenant
from app.domain.cash import CashRegister, CashSession
from app.domain.sales import Sale

async def update_all_databases():
    print("Updating Master Database...")
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Running automatic database branding migration from NEXUS to APEX ERP...")
    try:
        async with MasterSessionLocal() as session:
            # 1. Update tenants table
            await session.execute(text("UPDATE tenants SET name = 'APEX MASTER CORP' WHERE name = 'NEXUS MASTER CORP'"))
            await session.execute(text("UPDATE tenants SET name = 'DEMO - APEX ERP' WHERE name = 'DEMO - NEXUS ERP'"))
            await session.execute(text("UPDATE tenants SET email = 'admin@apexerp.com' WHERE email = 'admin@nexuserp.com'"))
            await session.execute(text("UPDATE tenants SET email = 'demo@apexerp.com' WHERE email = 'demo@nexuserp.com'"))
            
            # 2. Update users table
            await session.execute(text("UPDATE users SET email = 'admin@apexerp.com' WHERE email = 'admin@nexuserp.com'"))
            await session.execute(text("UPDATE users SET email = 'demo@apexerp.com' WHERE email = 'demo@nexuserp.com'"))
            
            await session.commit()
            print("Successfully updated database records from NEXUS to APEX ERP!")
    except Exception as db_err:
        print(f"Error performing data rebranding migration: {db_err}")
    
    print("Updating Tenant Databases (PostgreSQL)...")
    try:
        async with MasterSessionLocal() as session:
            stmt = select(Tenant)
            result = await session.execute(stmt)
            tenants = result.scalars().all()
            
            for tenant in tenants:
                schema_name = f"tenant_{tenant.id}"
                print(f"Ensuring schema and tables for Tenant {tenant.id} ({tenant.name})...")
                
                # 1. Create Schema
                async with master_engine.begin() as conn:
                    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                
                # 2. Run create_all inside tenant engine schema
                engine = get_tenant_engine(tenant.id)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
        print("PostgreSQL tenant databases updated successfully!")
    except Exception as e:
        print(f"PostgreSQL tenant migration skipped or failed: {e}")
    
    print("Updating Tenant Databases (SQLite Fallback)...")
    for file in os.listdir("."):
        if file.endswith(".db") and not file.startswith("master"):
            try:
                parts = file.replace(".db", "").split("_")
                tenant_id = int(parts[-1])
                print(f"Updating SQLite file {file} (Tenant {tenant_id})...")
                engine = get_tenant_engine(tenant_id)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as e:
                print(f"Error updating SQLite file {file}: {e}")

if __name__ == "__main__":
    asyncio.run(update_all_databases())
