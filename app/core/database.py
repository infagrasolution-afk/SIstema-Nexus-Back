from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# UN ÚNICO POOL GLOBAL DE CONEXIONES EN EL BACKEND (Single Connection Pool)
# ─────────────────────────────────────────────────────────────────────────────
# Todas las peticiones (tanto del esquema 'public' como de cada 'tenant_X')
# reutilizan las conexiones persistentes de este único pool global, evitando
# abrir y cerrar conexiones TCP/SSL en cada clic o multiplicar pools por empresa.
MASTER_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

master_engine = create_async_engine(
    MASTER_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,             # Conexiones persistentes listas para usar sin reconectar
    max_overflow=10,          # Conexiones adicionales en picos de alta concurrencia
    pool_recycle=1800,        # Reciclar conexiones cada 30 min para evitar cortes de red
    pool_timeout=30,          # Tiempo máximo de espera por conexión libre
    pool_pre_ping=True,       # Verifica que la conexión esté viva antes de usarla
    connect_args={
        # Desactivar caché de sentencias preparadas de asyncpg al cambiar search_path
        # dinámicamente sobre el mismo pool único de conexiones
        "statement_cache_size": 0
    },
)

# Único fábrica de sesiones reutilizable en memoria para todo el backend
MasterSessionLocal = async_sessionmaker(
    bind=master_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


class SinglePoolTenantEngine:
    """
    Adaptador ligero que reutiliza el único pool global (`master_engine`)
    ajustando el `search_path` al esquema `tenant_{tenant_id}, public`.
    No crea ningún pool ni motor adicional.
    """
    def __init__(self, tenant_id: int):
        self.tenant_id = int(tenant_id)
        self.schema_name = f"tenant_{self.tenant_id}"
        self.sync_engine = master_engine.sync_engine

    @asynccontextmanager
    async def begin(self):
        async with master_engine.begin() as conn:
            await conn.execute(text(f"SET search_path TO {self.schema_name}, public"))
            yield conn

    @asynccontextmanager
    async def connect(self):
        async with master_engine.connect() as conn:
            await conn.execute(text(f"SET search_path TO {self.schema_name}, public"))
            yield conn

    async def dispose(self):
        # No cerramos el pool global cuando se libera un adaptador individual
        pass


# Caché ligero de adaptadores (todos apuntan al mismo master_engine)
tenant_engines: dict[int, SinglePoolTenantEngine] = {}


def get_tenant_engine(tenant_id: int, company_name: str = None) -> SinglePoolTenantEngine:
    """
    Retorna el adaptador del tenant respaldado por el único pool global (`master_engine`).
    """
    tid = int(tenant_id)
    if tid not in tenant_engines:
        tenant_engines[tid] = SinglePoolTenantEngine(tid)
    return tenant_engines[tid]


@asynccontextmanager
async def get_tenant_session_context(tenant_id: int) -> AsyncGenerator[AsyncSession, None]:
    """
    Obtiene una sesión del único pool global (`MasterSessionLocal`) y fija el
    `search_path` de PostgreSQL al esquema de la empresa (`tenant_{tenant_id}, public`).
    """
    schema_name = f"tenant_{int(tenant_id)}"
    async with MasterSessionLocal() as session:
        await session.execute(text(f"SET search_path TO {schema_name}, public"))
        yield session


async def dispose_all_engines():
    """Cierra limpiamente el único pool global de conexiones al apagar el servidor."""
    tenant_engines.clear()
    await master_engine.dispose()


async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Sesión sobre el esquema `public` reutilizando el único pool global."""
    async with MasterSessionLocal() as session:
        await session.execute(text("SET search_path TO public"))
        yield session


async def init_tenant_db(tenant_id: int, company_name: str = None):
    """Crea el esquema y las tablas para un nuevo tenant usando el único pool global."""
    schema_name = f"tenant_{int(tenant_id)}"
    engine = get_tenant_engine(tenant_id, company_name)

    async with master_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        await conn.execute(text(f"SET search_path TO {schema_name}, public"))
        await conn.run_sync(Base.metadata.create_all)

    return engine


# Registro de modelos globales en Base.metadata
from app.domain.error_log import AppErrorLog
