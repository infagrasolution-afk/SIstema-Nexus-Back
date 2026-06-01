from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.domain.cash import CashRegister, CashSession, SessionStatus
from app.domain.sales import Sale
from app.schemas.cash import CashSessionCreate, CashSessionClose
from fastapi import HTTPException, status

class CashService:
    @staticmethod
    async def get_or_assign_register(db: AsyncSession, computer_uid: str, tenant_id: int) -> CashRegister:
        # 1. Try to find a register already assigned to this computer globally (since computer_uid is globally unique)
        stmt = select(CashRegister).where(
            CashRegister.computer_uid == computer_uid
        )
        result = await db.execute(stmt)
        register = result.scalar_one_or_none()
        
        if register:
            if register.tenant_id != tenant_id:
                register.tenant_id = tenant_id
                await db.commit()
                await db.refresh(register)
            return register
            
        # 2. If not, find the next available register number for this tenant
        stmt = select(func.count(CashRegister.id)).where(CashRegister.tenant_id == tenant_id)
        count_res = await db.execute(stmt)
        next_num = count_res.scalar() + 1
        
        register = CashRegister(
            name=f"Caja {next_num}",
            computer_uid=computer_uid,
            tenant_id=tenant_id
        )
        db.add(register)
        await db.commit()
        await db.refresh(register)
        return register

    @staticmethod
    async def open_session(db: AsyncSession, session_in: CashSessionCreate, user_id: int, tenant_id: int) -> CashSession:
        register = await CashService.get_or_assign_register(db, session_in.computer_uid, tenant_id)
        
        # Check if register has an open session
        stmt = select(CashSession).where(
            CashSession.register_id == register.id,
            CashSession.status == SessionStatus.OPEN,
            CashSession.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        existing_session = result.scalar_one_or_none()
        
        if existing_session:
            if existing_session.user_id != user_id:
                # Get user name for better error message
                from app.domain.user import User
                u_stmt = select(User).where(User.id == existing_session.user_id)
                u_res = await db.execute(u_stmt)
                u = u_res.scalar_one_or_none()
                user_name = u.email if u else "Otro usuario"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{register.name} ocupada por {user_name}. Se requiere arqueo y cierre para continuar."
                )
            existing_session.register = register # Eagerly assign to prevent lazyload crash
            return existing_session # Already open for this user
            
        new_session = CashSession(
            register_id=register.id,
            user_id=user_id,
            starting_cash=session_in.starting_cash,
            status=SessionStatus.OPEN,
            tenant_id=tenant_id
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        new_session.register = register # Eagerly assign to prevent lazyload crash
        return new_session

    @staticmethod
    async def close_session(db: AsyncSession, session_id: int, close_in: CashSessionClose, tenant_id: int) -> CashSession:
        stmt = select(CashSession).where(CashSession.id == session_id, CashSession.tenant_id == tenant_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session or session.status == SessionStatus.CLOSED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada o ya cerrada")
            
        # Calculate expected cash
        # Sum of cash sales (payment_method='cash') in this session
        stmt = select(func.sum(Sale.total)).where(
            Sale.cash_session_id == session.id,
            Sale.payment_method == "cash",
            Sale.tenant_id == tenant_id
        )
        res = await db.execute(stmt)
        cash_sales = res.scalar() or 0.0
        
        session.expected_cash = session.starting_cash + cash_sales
        session.actual_cash = close_in.actual_cash
        session.closing_time = datetime.utcnow()
        session.status = SessionStatus.CLOSED
        
        await db.commit()
        await db.refresh(session)
        
        # Eagerly load register to avoid serialization lazyload error
        r_stmt = select(CashRegister).where(CashRegister.id == session.register_id)
        r_res = await db.execute(r_stmt)
        session.register = r_res.scalar_one()
        
        return session

    @staticmethod
    async def get_current_session(db: AsyncSession, computer_uid: str, tenant_id: int) -> CashSession:
        register = await CashService.get_or_assign_register(db, computer_uid, tenant_id)
        
        stmt = select(CashSession).where(
            CashSession.register_id == register.id,
            CashSession.status == SessionStatus.OPEN,
            CashSession.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session:
            session.register = register # Eagerly assign to prevent lazyload crash
        return session
