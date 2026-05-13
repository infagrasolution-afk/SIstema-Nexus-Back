import asyncio
from app.core.database import MasterSessionLocal, init_tenant_db
from app.domain.tenant import Tenant
from app.domain.user import User
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import os

async def test_create_inversiones_infante():
    print("--- Iniciando creación de 'Inversiones Infante' ---")
    
    async with MasterSessionLocal() as db:
        company_name = "Inversiones Infante"
        
        # 1. Crear la empresa en Master
        tenant = Tenant(
            name=company_name,
            email="contacto@infante.com",
            license_key="INFANTE-2026",
            subscription_end=datetime.utcnow() + timedelta(days=365)
        )
        db.add(tenant)
        await db.flush() # Para obtener el ID (debería ser 2)

        # 2. Crear su usuario administrador
        admin = User(
            email="admin@infante.com",
            hashed_password=get_password_hash("infante123"),
            is_active=True,
            is_superuser=False, # Es admin de su empresa, no del SaaS
            tenant_id=tenant.id
        )
        db.add(admin)
        await db.commit()
        
        # 3. Disparar la creación de su base de datos privada
        print(f"Generando base de datos para ID {tenant.id}...")
        await init_tenant_db(tenant.id, company_name)
        
    print("\n--- ¡Empresa creada con éxito! ---")
    print("Listando archivos de base de datos actuales:")
    os.system("ls *.db")

if __name__ == "__main__":
    asyncio.run(test_create_inversiones_infante())
