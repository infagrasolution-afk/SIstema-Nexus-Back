"""Script de diagnóstico y reparación de la cuenta demo."""
import asyncio
import ssl
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from passlib.context import CryptContext

DATABASE_URL = "postgresql+asyncpg://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a.virginia-postgres.render.com/erp_db_x91k"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def diagnose_and_fix():
    # Create SSL context for Render
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"ssl": ssl_ctx}
    )
    async with engine.connect() as conn:
        # 1. Buscar usuario demo
        result = await conn.execute(
            text("SELECT id, username, hashed_password, is_active, is_superuser, "
                 "login_attempts, is_locked, locked_at, tenant_id "
                 "FROM users WHERE username = 'demo'")
        )
        user = result.fetchone()

        if not user:
            print("❌ Usuario 'demo' NO EXISTE en la base de datos.")
            print("\n📋 Usuarios existentes:")
            all_users = await conn.execute(
                text("SELECT id, username, is_active, is_locked, login_attempts, tenant_id FROM users")
            )
            for u in all_users.fetchall():
                print(f"   ID={u[0]}, username='{u[1]}', active={u[2]}, locked={u[3]}, attempts={u[4]}, tenant={u[5]}")
            await engine.dispose()
            return

        print("✅ Usuario 'demo' encontrado:")
        print(f"   ID:              {user[0]}")
        print(f"   Username:        {user[1]}")
        print(f"   is_active:       {user[3]}")
        print(f"   is_superuser:    {user[4]}")
        print(f"   login_attempts:  {user[5]}")
        print(f"   is_locked:       {user[6]}")
        print(f"   locked_at:       {user[7]}")
        print(f"   tenant_id:       {user[8]}")

        # 2. Verificar contraseña
        hashed = user[2]
        password_ok = pwd_context.verify("demo123", hashed)
        print(f"\n🔑 Contraseña 'demo123' correcta: {password_ok}")

        if not password_ok:
            print("   ⚠️  El hash almacenado NO coincide con 'demo123'")
            print(f"   Hash actual: {hashed[:30]}...")

        # 3. Diagnosticar problemas
        problems = []
        if user[6]:  # is_locked
            problems.append("CUENTA BLOQUEADA")
        if not user[3]:  # not is_active
            problems.append("CUENTA INACTIVA")
        if not password_ok:
            problems.append("CONTRASEÑA NO COINCIDE")

        if not problems:
            print("\n✅ No se encontraron problemas. La cuenta debería funcionar correctamente.")
        else:
            print(f"\n⚠️  Problemas detectados: {', '.join(problems)}")
            print("\n🔧 Aplicando correcciones...")

            # Desbloquear + resetear intentos + activar + resetear password
            new_hash = pwd_context.hash("demo123")
            await conn.execute(
                text("""
                    UPDATE users 
                    SET is_locked = false, 
                        login_attempts = 0, 
                        locked_at = NULL,
                        is_active = true,
                        hashed_password = :new_hash
                    WHERE username = 'demo'
                """),
                {"new_hash": new_hash}
            )
            await conn.commit()
            print("   ✅ Cuenta desbloqueada")
            print("   ✅ Intentos de login reseteados a 0")
            print("   ✅ Cuenta activada")
            print("   ✅ Contraseña reseteada a 'demo123'")
            print("\n🎉 ¡Listo! Intenta iniciar sesión con demo / demo123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(diagnose_and_fix())
