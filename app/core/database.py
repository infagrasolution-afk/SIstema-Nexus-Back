from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
import os
import re
from app.core.config import settings

# Master Engine for Global Data (Tenants, Users)
MASTER_DATABASE_URL = "sqlite+aiosqlite:///./master.db"
master_engine = create_async_engine(MASTER_DATABASE_URL, echo=False, future=True)
MasterSessionLocal = async_sessionmaker(master_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Cache for tenant engines
tenant_engines = {}

def get_initials(name: str) -> str:
    """Converts 'Inversiones Infante' to 'I_I'"""
    # Remove special characters and split by spaces
    words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
    if not words:
        return "EXT"
    initials = "_".join([word[0].upper() for word in words])
    return initials

def get_tenant_engine(tenant_id: int, company_name: str = None):
    """
    Returns the engine for a specific tenant database.
    Format: INITIALS_ID.db
    """
    if tenant_id not in tenant_engines:
        # If company_name is provided (e.g. at creation), use it.
        # Otherwise, we'll try to find an existing file or use a generic one.
        prefix = get_initials(company_name) if company_name else "TEN"
        db_path = f"./{prefix}_{tenant_id}.db"
        
        # Check if a file with this ID already exists but with different initials
        # This is a fallback in case the name changed
        for file in os.listdir("."):
            if file.endswith(f"_{tenant_id}.db"):
                db_path = f"./{file}"
                break
                
        url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(url, echo=False, future=True)
        tenant_engines[tenant_id] = engine
        
    return tenant_engines[tenant_id]

async def get_master_db():
    async with MasterSessionLocal() as session:
        yield session

async def init_tenant_db(tenant_id: int, company_name: str):
    """Creates the database file and tables for a new tenant with formatted name."""
    engine = get_tenant_engine(tenant_id, company_name)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine
