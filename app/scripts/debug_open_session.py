import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.core.database import get_tenant_engine
from app.domain.cash import CashRegister, CashSession
from app.services.cash_service import CashService

async def debug_open():
    tenant_id = 3
    user_id = 6 # demo user
    engine = get_tenant_engine(tenant_id)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        try:
            print("Trying to call CashService.get_or_assign_register...")
            register = await CashService.get_or_assign_register(db, "debug-demo-uid-999", tenant_id)
            print(f"Successfully got/assigned register: ID={register.id}, Name={register.name}")
            
            print("Trying to open session for demo user (ID=6)...")
            from app.schemas.cash import CashSessionCreate
            session_in = CashSessionCreate(
                starting_cash=100.0,
                computer_uid="debug-demo-uid-999",
                register_id=register.id
            )
            
            session = await CashService.open_session(db, session_in, user_id, tenant_id)
            print(f"Successfully opened session! ID={session.id}, Status={session.status}")
            
        except Exception as e:
            print("\n!!! ERROR OCCURRED !!!")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_open())
