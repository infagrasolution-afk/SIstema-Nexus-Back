import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.core.database import get_tenant_engine
from app.domain.cash import CashRegister, CashSession
from app.domain.user import User

async def check_data():
    tenant_id = 3
    engine = get_tenant_engine(tenant_id)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        print("--- CASH REGISTERS ---")
        stmt = select(CashRegister)
        res = await db.execute(stmt)
        registers = res.scalars().all()
        for r in registers:
            print(f"ID={r.id}, Name={r.name}, computer_uid={r.computer_uid}")
            
        print("\n--- CASH SESSIONS ---")
        stmt = select(CashSession)
        res = await db.execute(stmt)
        sessions = res.scalars().all()
        for s in sessions:
            print(f"ID={s.id}, Register_ID={s.register_id}, User_ID={s.user_id}, Status={s.status}")

if __name__ == "__main__":
    asyncio.run(check_data())
