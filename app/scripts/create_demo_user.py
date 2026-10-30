"""
Script: create_demo_user.py
Crea un usuario DEMO para que clientes potenciales puedan explorar el ERP.

Credenciales Demo:
  Usuario:   demo
  Contrasena: Demo2025*
  Empresa:   DEMO COMPANY C.A.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from app.core.database import MasterSessionLocal, master_engine, Base, init_tenant_db
from app.core.security import get_password_hash
from app.domain.user import User
from app.domain.tenant import Tenant
import app.domain  # Load all models


DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo2025*"
DEMO_EMAIL    = "demo@apexerp.com"
DEMO_COMPANY  = "DEMO COMPANY C.A."


async def create_demo():
    # 1. Asegurar tablas master
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with MasterSessionLocal() as db:

        # 2. Buscar Tenant DEMO por nombre
        result = await db.execute(select(Tenant).where(Tenant.name == DEMO_COMPANY))
        tenant = result.scalars().first()

        if not tenant:
            demo_license = f"DEMO-{uuid.uuid4().hex[:8].upper()}"
            tenant = Tenant(
                name=DEMO_COMPANY,
                email=DEMO_EMAIL,
                license_key=demo_license,
                subscription_end=datetime.now(timezone.utc) + timedelta(days=3650),
                is_active=True,
                modules=["sales", "inventory", "purchases", "accounting",
                         "hr", "pos", "reports", "crm"],
            )
            db.add(tenant)
            await db.flush()  # Obtener el ID auto-generado
            print(f"[+] Tenant creado: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"[=] Tenant ya existe: {tenant.name} (ID: {tenant.id})")

        # 3. Crear / actualizar usuario DEMO
        result = await db.execute(select(User).where(User.username == DEMO_USERNAME))
        user = result.scalars().first()

        if not user:
            user = User(
                username=DEMO_USERNAME,
                email=DEMO_EMAIL,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                is_active=True,
                is_superuser=False,
                tenant_id=tenant.id,
                modules="sales,inventory,purchases,accounting,hr,pos,reports,crm",
            )
            db.add(user)
            await db.commit()
            print(f"[+] Usuario DEMO creado:")
        else:
            # Actualizar por si se quiere resetear la contrasena
            user.hashed_password = get_password_hash(DEMO_PASSWORD)
            user.is_active = True
            user.tenant_id = tenant.id
            await db.commit()
            print(f"[=] Usuario DEMO actualizado:")

        # 4. Inicializar schema tenant en PostgreSQL
        await init_tenant_db(tenant.id, DEMO_COMPANY)
        print(f"[+] Schema tenant_{tenant.id} inicializado en Neon")

    print()
    print("=" * 52)
    print("  DEMO LISTO - Credenciales para clientes:")
    print("=" * 52)
    print(f"  URL:        https://erp-frontend-8hz1.onrender.com")
    print(f"  Usuario:    {DEMO_USERNAME}")
    print(f"  Contrasena: {DEMO_PASSWORD}")
    print("=" * 52)


if __name__ == "__main__":
    asyncio.run(create_demo())
