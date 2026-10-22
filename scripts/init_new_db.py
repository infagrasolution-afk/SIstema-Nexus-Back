# -*- coding: utf-8 -*-
"""
Script completo para inicializar la nueva base de datos en Render.
Crea esquemas, tablas, tenant master, superuser admin, usuario demo, y KPRISHOP.
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime, timedelta

# Forzar encoding UTF-8 en consola Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add the backend root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from app.core.database import MasterSessionLocal, Base, master_engine, get_tenant_engine
from app.core.security import get_password_hash
from app.domain.user import User
from app.domain.tenant import Tenant
import app.domain.inventory
import app.domain.sales
import app.domain.purchases
import app.domain.cash
import app.domain.refresh_token
import app.domain.error_log


async def init_database():
    print("=" * 60)
    print(">>> INICIALIZANDO NUEVA BASE DE DATOS APEX ERP")
    print("=" * 60)

    # --- 1. Create all tables in public schema ---
    print("\n[1/6] Creando tablas en esquema publico...")
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   OK - Tablas creadas exitosamente")

    async with MasterSessionLocal() as db:
        # --- Check what already exists ---
        existing_tenants = (await db.execute(select(Tenant))).scalars().all()
        existing_users = (await db.execute(select(User))).scalars().all()
        print(f"\n   Estado actual: {len(existing_tenants)} tenants, {len(existing_users)} usuarios")

        # --- 2. Create/ensure Master Tenant ---
        print("\n[2/6] Verificando tenant maestro...")
        result = await db.execute(select(Tenant).where(Tenant.id == 1))
        master_tenant = result.scalars().first()

        if not master_tenant:
            # Insert with explicit ID and fix sequence after
            await db.execute(text(
                """INSERT INTO tenants (id, name, email, license_key, subscription_end, is_active, modules)
                   VALUES (1, 'APEX MASTER CORP', 'infagrasolution@gmail.com', 
                           :license_key, :sub_end, true,
                           '{"inventory": true, "sales": true, "purchases": true, "accounting": true, "treasury": true, "wms": true, "reports": true, "fiscal": true}')
                   ON CONFLICT (id) DO NOTHING"""
            ), {
                "license_key": f"MASTER-{uuid.uuid4().hex[:8].upper()}",
                "sub_end": datetime.now() + timedelta(days=3650)
            })
            # Fix sequence to avoid duplicate key issues
            await db.execute(text("SELECT setval('tenants_id_seq', (SELECT COALESCE(MAX(id), 0) FROM tenants))"))
            await db.flush()
            print("   OK - Tenant maestro creado: APEX MASTER CORP (ID: 1)")
        else:
            print(f"   YA EXISTE - {master_tenant.name} (ID: {master_tenant.id})")

        # --- 3. Create Demo Tenant ---
        print("\n[3/6] Creando tenant demo...")
        result = await db.execute(select(Tenant).where(Tenant.name.ilike("%demo%")))
        demo_tenant = result.scalars().first()

        if not demo_tenant:
            demo_tenant = Tenant(
                name="DEMO - APEX ERP",
                email="demo@apexerp.com",
                license_key=f"DEMO-{uuid.uuid4().hex[:8].upper()}",
                subscription_end=datetime.now() + timedelta(days=3650),
                is_active=True,
                modules='{"inventory": true, "sales": true, "purchases": true, "accounting": true, "treasury": true, "wms": true, "reports": true, "fiscal": true}'
            )
            db.add(demo_tenant)
            await db.flush()
            print(f"   OK - Tenant demo creado: {demo_tenant.name} (ID: {demo_tenant.id})")
        else:
            print(f"   YA EXISTE - {demo_tenant.name} (ID: {demo_tenant.id})")

        # --- 3b. Create KPRISHOP Tenant ---
        print("\n[3b/6] Creando tenant KPRISHOP...")
        result = await db.execute(select(Tenant).where(Tenant.name.ilike("%kprishop%")))
        kprishop_tenant = result.scalars().first()

        if not kprishop_tenant:
            kprishop_tenant = Tenant(
                name="KPRISHOP",
                email="admin@kprishop.com",
                license_key=f"KPRI-{uuid.uuid4().hex[:8].upper()}",
                subscription_end=datetime(2027, 5, 28, 23, 59, 59),
                is_active=True,
                modules='{"inventory": true, "sales": true, "purchases": true, "accounting": true, "treasury": true, "wms": true, "reports": true, "fiscal": true}'
            )
            db.add(kprishop_tenant)
            await db.flush()
            print(f"   OK - Tenant KPRISHOP creado: {kprishop_tenant.name} (ID: {kprishop_tenant.id})")
        else:
            print(f"   YA EXISTE - {kprishop_tenant.name} (ID: {kprishop_tenant.id})")

        # --- 4. Create Superuser Admin ---
        print("\n[4/6] Creando superusuario admin...")
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            db.add(User(
                username="admin",
                email="infagrasolution@gmail.com",
                hashed_password=get_password_hash("aa11..**"),
                is_superuser=True, is_active=True, is_locked=False,
                login_attempts=0, tenant_id=1
            ))
            await db.flush()
            print("   OK - admin / aa11..**  (SUPERADMIN, tenant: APEX MASTER)")
        else:
            print("   YA EXISTE")

        # --- 5. Create Demo User ---
        print("\n[5/6] Creando usuario demo...")
        result = await db.execute(select(User).where(User.username == "demo"))
        if not result.scalars().first():
            db.add(User(
                username="demo",
                email="demo@apexerp.com",
                hashed_password=get_password_hash("demo123"),
                is_superuser=True, is_active=True, is_locked=False,
                login_attempts=0, tenant_id=demo_tenant.id
            ))
            await db.flush()
            print(f"   OK - demo / demo123  (tenant: {demo_tenant.name})")
        else:
            print("   YA EXISTE")

        # --- 5b. Create KPRISHOP Users (3 users) ---
        print("\n[5b/6] Creando usuarios KPRISHOP...")
        kprishop_users = [
            {"username": "kprishop", "email": "admin@kprishop.com", "password": "kprishop123", "is_superuser": False},
            {"username": "kprishop2", "email": "user2@kprishop.com", "password": "kprishop123", "is_superuser": False},
            {"username": "kprishop3", "email": "user3@kprishop.com", "password": "kprishop123", "is_superuser": False},
        ]
        for u_data in kprishop_users:
            result = await db.execute(select(User).where(User.username == u_data["username"]))
            if not result.scalars().first():
                db.add(User(
                    username=u_data["username"],
                    email=u_data["email"],
                    hashed_password=get_password_hash(u_data["password"]),
                    is_superuser=u_data["is_superuser"],
                    is_active=True, is_locked=False,
                    login_attempts=0, tenant_id=kprishop_tenant.id
                ))
                await db.flush()
                print(f"   OK - {u_data['username']} / {u_data['password']}  (tenant: KPRISHOP)")
            else:
                print(f"   YA EXISTE - {u_data['username']}")

        await db.commit()
        print("\n   COMMIT exitoso!")

    # --- 6. Create tenant schemas ---
    print("\n[6/6] Creando esquemas de tenants...")
    async with MasterSessionLocal() as db:
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()

        for t in tenants:
            schema_name = f"tenant_{t.id}"
            print(f"   Esquema '{schema_name}' para {t.name}...")
            async with master_engine.begin() as conn:
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

            engine = get_tenant_engine(t.id, t.name)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print(f"   OK - '{schema_name}' listo")

    print("\n" + "=" * 60)
    print(">>> BASE DE DATOS INICIALIZADA EXITOSAMENTE!")
    print("=" * 60)
    print("\nCredenciales:")
    print("   Superadmin:     admin / aa11..**")
    print("   Demo:           demo / demo123")
    print("   KPRISHOP #1:    kprishop / kprishop123")
    print("   KPRISHOP #2:    kprishop2 / kprishop123")
    print("   KPRISHOP #3:    kprishop3 / kprishop123")
    print("")
    print("NOTA: Los usuarios de KPRISHOP tienen claves temporales.")
    print("Puedes cambiarlas luego desde el panel de admin.")
    print("=" * 60)

    await master_engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
