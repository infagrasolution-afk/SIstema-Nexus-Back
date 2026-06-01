from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings
from app.domain.error_log import AppErrorLog

# Master Engine for Global Data (Tenants, Users)
MASTER_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI
master_engine = create_async_engine(
    MASTER_DATABASE_URL, 
    echo=False, 
    future=True,
    pool_size=10,             # Keep up to 10 active connections in pool
    max_overflow=5,           # Allow up to 5 additional overflow connections
    pool_recycle=1800,        # Recycle connections older than 30 mins to avoid stale connections
    pool_timeout=30,          # Fail fast after 30s of waiting for a connection
    pool_pre_ping=True        # Pre-ping to discard dead/closed connections automatically
)
MasterSessionLocal = async_sessionmaker(master_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Cache for tenant engines
tenant_engines = {}

def get_tenant_engine(tenant_id: int, company_name: str = None):
    """
    Returns an engine configured to use the specific schema for a tenant.
    In PostgreSQL, we use a single database with multiple schemas (e.g., schema 'tenant_1').
    """
    if tenant_id not in tenant_engines:
        schema_name = f"tenant_{tenant_id}"
        
        # Connect to the main database but set the search_path to the tenant's schema
        url = settings.SQLALCHEMY_DATABASE_URI
        
        # asyncpg specific arguments to set the search path automatically on connect
        engine = create_async_engine(
            url, 
            echo=False, 
            future=True,
            connect_args={"server_settings": {"search_path": f"{schema_name}, public"}},
            pool_size=5,              # Smaller pool size per tenant to prevent database connection exhaustion
            max_overflow=2,           # Allow minimal overflow
            pool_recycle=1800,        # Recycle connections
            pool_timeout=15,          # Shorter timeout for fast response
            pool_pre_ping=True        # Check connection health before using
        )
        tenant_engines[tenant_id] = engine
        
    return tenant_engines[tenant_id]

async def get_master_db():
    async with MasterSessionLocal() as session:
        yield session

async def init_tenant_db(tenant_id: int, company_name: str):
    """Creates the schema and tables for a new tenant."""
    schema_name = f"tenant_{tenant_id}"
    
    # 1. Create the schema using the master engine
    async with master_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        
    # 2. Create the tables inside the new schema using the tenant engine
    engine = get_tenant_engine(tenant_id, company_name)
    async with engine.begin() as conn:
        # Base.metadata.create_all will respect the search_path set in the engine
        await conn.run_sync(Base.metadata.create_all)
        
    return engine
