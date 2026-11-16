from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# ARQUITECTURA HÍBRIDA DE CONEXIONES (Single Pool Multi-Schema + Dedicated DB VIP)
# ─────────────────────────────────────────────────────────────────────────────
# 1. Por defecto (95% de empresas): Usa UN ÚNICO POOL GLOBAL (`master_engine`)
#    cambiando el esquema dinámicamente (`SET search_path TO tenant_X, public`)
#    sin abrir ni cerrar conexiones nuevas en cada clic.
# 2. Clientes Corporativos / VIP (`custom_database_url` configurado en Tenant):
#    Se conecta automáticamente a la Base de Datos PostgreSQL exclusiva del cliente.

MASTER_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI

master_engine = create_async_engine(
    MASTER_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,             # Conexiones persistentes listas en el pool único
    max_overflow=10,          # Conexiones extra para picos de concurrencia
    pool_recycle=1800,        # Reciclar cada 30 min
    pool_timeout=30,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0
    },
)

MasterSessionLocal = async_sessionmaker(
    bind=master_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# Caché en memoria para motores de clientes con Base de Datos Dedicada (Modo Híbrido VIP)
dedicated_engines: dict[str, AsyncEngine] = {}
dedicated_sessionmakers: dict[str, async_sessionmaker] = {}
# Caché en memoria de tenant_id -> custom_database_url (None si usa el pool único estándar)
tenant_custom_db_cache: dict[int, Optional[str]] = {}


def normalize_async_db_url(raw_url: str) -> str:
    """Asegura que una URL PostgreSQL use el driver asíncrono asyncpg."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_dedicated_engine(custom_url: str) -> AsyncEngine:
    norm_url = normalize_async_db_url(custom_url)
    if norm_url not in dedicated_engines:
        eng = create_async_engine(
            norm_url,
            echo=False,
            future=True,
            pool_size=5,
            max_overflow=3,
            pool_recycle=1800,
            pool_timeout=20,
            pool_pre_ping=True,
        )
        dedicated_engines[norm_url] = eng
        dedicated_sessionmakers[norm_url] = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return dedicated_engines[norm_url]


class HybridTenantEngine:
    """
    Adaptador Híbrido:
    - Si `custom_database_url` está vacío: reutiliza el único pool global (`master_engine`)
      fijando `SET search_path TO tenant_{tenant_id}, public`.
    - Si `custom_database_url` está definido: utiliza el motor dedicado de esa base de datos.
    """
    def __init__(self, tenant_id: int, custom_database_url: Optional[str] = None):
        self.tenant_id = int(tenant_id)
        self.schema_name = f"tenant_{self.tenant_id}"
        self.custom_database_url = (custom_database_url or "").strip() or None
        self._target_engine = (
            get_dedicated_engine(self.custom_database_url)
            if self.custom_database_url
            else master_engine
        )
        self.sync_engine = self._target_engine.sync_engine

    @asynccontextmanager
    async def begin(self):
        async with self._target_engine.begin() as conn:
            if not self.custom_database_url:
                await conn.execute(text(f"SET search_path TO {self.schema_name}, public"))
            yield conn

    @asynccontextmanager
    async def connect(self):
        async with self._target_engine.connect() as conn:
            if not self.custom_database_url:
                await conn.execute(text(f"SET search_path TO {self.schema_name}, public"))
            yield conn

    async def dispose(self):
        if self.custom_database_url and self._target_engine:
            await self._target_engine.dispose()


tenant_engines: dict[int, HybridTenantEngine] = {}


def set_tenant_custom_db_cache(tenant_id: int, custom_database_url: Optional[str]) -> None:
    tid = int(tenant_id)
    clean_url = (custom_database_url or "").strip() or None
    tenant_custom_db_cache[tid] = clean_url
    tenant_engines.pop(tid, None)


def get_tenant_engine(
    tenant_id: int,
    company_name: str = None,
    custom_database_url: Optional[str] = None,
) -> HybridTenantEngine:
    tid = int(tenant_id)
    effective_url = (custom_database_url or "").strip() or tenant_custom_db_cache.get(tid)
    if tid not in tenant_engines or tenant_engines[tid].custom_database_url != effective_url:
        tenant_engines[tid] = HybridTenantEngine(tid, effective_url)
    return tenant_engines[tid]


@asynccontextmanager
async def get_tenant_session_context(
    tenant_id: int,
    custom_database_url: Optional[str] = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Obtiene una sesión de base de datos en Modo Híbrido:
    - Si el cliente tiene `custom_database_url`, abre sesión contra su BD dedicada.
    - En caso contrario (estándar), toma una conexión del único pool global (`MasterSessionLocal`)
      y fija `SET search_path TO tenant_{tenant_id}, public`.
    """
    tid = int(tenant_id)
    effective_url = (custom_database_url or "").strip() or tenant_custom_db_cache.get(tid)

    if effective_url:
        get_dedicated_engine(effective_url)
        norm_url = normalize_async_db_url(effective_url)
        session_factory = dedicated_sessionmakers[norm_url]
        async with session_factory() as session:
            yield session
    else:
        schema_name = f"tenant_{tid}"
        async with MasterSessionLocal() as session:
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            yield session


async def dispose_all_engines():
    """Cierra limpiamente el pool global y cualquier motor dedicado al apagar el servidor."""
    tenant_engines.clear()
    for eng in list(dedicated_engines.values()):
        await eng.dispose()
    dedicated_engines.clear()
    dedicated_sessionmakers.clear()
    await master_engine.dispose()


async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Sesión sobre el esquema `public` reutilizando el único pool global."""
    async with MasterSessionLocal() as session:
        await session.execute(text("SET search_path TO public"))
        yield session


async def init_tenant_db(
    tenant_id: int,
    company_name: str = None,
    custom_database_url: Optional[str] = None,
):
    """
    Inicializa las tablas para un nuevo cliente en Modo Híbrido:
    - Si tiene `custom_database_url`, crea las tablas en su Base de Datos dedicada.
    - Si no tiene `custom_database_url`, crea el esquema `tenant_{id}` en la BD principal.
    """
    tid = int(tenant_id)
    clean_url = (custom_database_url or "").strip() or None
    set_tenant_custom_db_cache(tid, clean_url)
    engine = get_tenant_engine(tid, company_name, clean_url)

    if clean_url:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        schema_name = f"tenant_{tid}"
        async with master_engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await conn.execute(text(f"SET search_path TO {schema_name}, public"))
            await conn.run_sync(Base.metadata.create_all)

    return engine


from app.domain.error_log import AppErrorLog
from app.domain.security_audit_log import SecurityAuditLog
