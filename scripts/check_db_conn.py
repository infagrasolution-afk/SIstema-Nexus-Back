import asyncio
import ssl
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncpg
from app.core.config import settings

async def test_conn():
    print(f"Testing DATABASE_URL from settings:")
    raw_url = settings.DATABASE_URL
    print(f"RAW URL: {raw_url.split('@')[-1] if '@' in raw_url else raw_url}")
    print(f"SQLALCHEMY_DATABASE_URI: {settings.SQLALCHEMY_DATABASE_URI.split('@')[-1]}")

    # Test 1: Standard asyncpg with ssl=True
    # Parse asyncpg url
    url_for_asyncpg = raw_url.replace("postgresql://", "").replace("postgresql+asyncpg://", "")
    user_pass, host_port_db = url_for_asyncpg.split("@")
    user, password = user_pass.split(":")
    
    if "/" in host_port_db:
        host_port, db = host_port_db.split("/", 1)
        db = db.split("?")[0]
    else:
        host_port = host_port_db
        db = "postgres"
        
    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host = host_port
        port = 5432

    print(f"\n[1] Testing direct asyncpg connection to host={host}, port={port}, db={db}, user={user}...")
    
    # Try with ssl context
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    for ssl_mode_name, ssl_val in [("ssl=require (custom context)", ssl_ctx), ("ssl=True", True), ("ssl=None", None)]:
        try:
            print(f"   Attempting with {ssl_mode_name}...")
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=db,
                    ssl=ssl_val,
                    timeout=10
                ),
                timeout=12
            )
            print(f"   --> SUCCESS with {ssl_mode_name}!")
            val = await conn.fetchval("SELECT current_user, current_database(), version();")
            print(f"   Database returned: {val}")
            
            # Check users table
            users = await conn.fetch("SELECT id, username, email, is_superuser, is_active, is_locked FROM users;")
            print(f"   Users found in database ({len(users)}):")
            for u in users:
                print(f"     - ID={u['id']}, username='{u['username']}', email='{u['email']}', is_superuser={u['is_superuser']}, is_active={u['is_active']}, is_locked={u['is_locked']}")
            
            await conn.close()
            return
        except Exception as e:
            print(f"   --> FAILED with {ssl_mode_name}: {type(e).__name__}: {e}")

    # Also test second URL from fix_demo.py if settings URL failed
    alt_url = "postgresql+asyncpg://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a.virginia-postgres.render.com/erp_db_x91k"
    print(f"\n[2] Testing alternative URL (erp_db_x91k)...")
    try:
        url2 = alt_url.replace("postgresql+asyncpg://", "")
        up2, hp2 = url2.split("@")
        u2, p2 = up2.split(":")
        host_port2, db2 = hp2.split("/")
        h2 = host_port2.split(":")[0]
        conn2 = await asyncpg.connect(user=u2, password=p2, host=h2, port=5432, database=db2, ssl=ssl_ctx, timeout=10)
        print("   --> SUCCESS connecting to erp_db_x91k!")
        users2 = await conn2.fetch("SELECT id, username, email, is_superuser, is_active, is_locked FROM users;")
        print(f"   Users in erp_db_x91k ({len(users2)}):")
        for u in users2:
            print(f"     - ID={u['id']}, username='{u['username']}', email='{u['email']}'")
        await conn2.close()
    except Exception as e:
        print(f"   --> Alternative URL failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
