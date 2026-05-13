import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.domain.user import User

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"Email: {u.email}, Superuser: {u.is_superuser}, Tenant: {u.tenant_id}")

if __name__ == "__main__":
    asyncio.run(check_users())
