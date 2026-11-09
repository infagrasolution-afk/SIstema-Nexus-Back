"""
APEX ERP — Script Profesional de Respaldo y Protección de Base de Datos
Permite generar copias de seguridad completas o por empresa (tenant) en formato JSON comprimido (.json.gz).
Uso:
    python scripts/backup_db.py --all           # Respalda la base de datos completa
    python scripts/backup_db.py --tenant 2     # Respalda solo una empresa específica
"""
import os
import sys
import json
import gzip
import argparse
import asyncio
from datetime import datetime, date
from decimal import Decimal
import asyncpg

# Agregar ruta raíz al path para importar configuración
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))


def json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def normalize_asyncpg_url(url: str) -> str:
    """Asegura formato estándar para asyncpg con ssl activado si aplica."""
    clean = url.replace("postgresql+asyncpg://", "postgresql://")
    if "sslmode=require" not in clean and ("neon.tech" in clean or "render.com" in clean or "azure" in clean):
        clean += "&sslmode=require" if "?" in clean else "?sslmode=require"
    return clean


async def backup_database(tenant_filter: int = None):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_url = normalize_asyncpg_url(settings.DATABASE_URL)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"apex_backup_tenant_{tenant_filter}_{timestamp}.json.gz" if tenant_filter else f"apex_backup_full_{timestamp}.json.gz"
    output_path = os.path.join(BACKUP_DIR, filename)

    print(f"[*] Iniciando respaldo de APEX ERP...")
    print(f"[*] Destino: {output_path}")

    conn = await asyncpg.connect(db_url)
    backup_data = {
        "metadata": {
            "version": settings.VERSION,
            "created_at": datetime.now().isoformat(),
            "tenant_filter": tenant_filter,
            "system": "APEX ERP Venezuela"
        },
        "public": {},
        "tenants": {}
    }

    try:
        # 1. Respaldar tablas globales de public
        public_tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
              AND tablename NOT IN ('alembic_version')
            ORDER BY tablename
        """)

        for row in public_tables:
            tbl = row['tablename']
            if tenant_filter and tbl in ('refresh_tokens', 'app_error_logs'):
                continue
            records = await conn.fetch(f"SELECT * FROM public.{tbl}")
            backup_data["public"][tbl] = [dict(r) for r in records]
            print(f"  [+] Tabla public.{tbl}: {len(records)} registros respaldados.")

        # 2. Respaldar esquemas de tenants
        if tenant_filter:
            schemas = [f"tenant_{tenant_filter}"]
        else:
            schemas_records = await conn.fetch("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%'
                ORDER BY schema_name
            """)
            schemas = [r['schema_name'] for r in schemas_records]

        for sc in schemas:
            backup_data["tenants"][sc] = {}
            tenant_tables = await conn.fetch(f"""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = '{sc}'
                ORDER BY tablename
            """)
            for t_row in tenant_tables:
                t_tbl = t_row['tablename']
                t_records = await conn.fetch(f"SELECT * FROM {sc}.{t_tbl}")
                backup_data["tenants"][sc][t_tbl] = [dict(r) for r in t_records]
                print(f"  [+] {sc}.{t_tbl}: {len(t_records)} registros.")

        # Guardar en archivo comprimido con gzip
        json_bytes = json.dumps(backup_data, default=json_serializer, ensure_ascii=False, indent=2).encode('utf-8')
        with gzip.open(output_path, "wb") as f:
            f.write(json_bytes)

        size_kb = os.path.getsize(output_path) / 1024
        print(f"\n[OK] Respaldo completado exitosamente: {filename} ({size_kb:.1f} KB)")
        return output_path

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Respaldo de base de datos APEX ERP")
    parser.add_argument("--all", action="store_true", help="Respaldar todas las tablas y esquemas")
    parser.add_argument("--tenant", type=int, default=None, help="ID específico del tenant a respaldar")
    args = parser.parse_args()

    asyncio.run(backup_database(tenant_filter=args.tenant))
