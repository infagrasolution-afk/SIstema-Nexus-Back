"""Script rapido para desbloquear la cuenta demo."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.core.database import MasterSessionLocal
from app.domain.user import User


async def unlock_demo():
    async with MasterSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "demo"))
        user = result.scalars().first()
        if not user:
            print("Usuario 'demo' no encontrado")
            return
        
        print(f"Usuario: {user.username}")
        print(f"  is_locked: {user.is_locked}")
        print(f"  login_attempts: {user.login_attempts}")
        print(f"  is_active: {user.is_active}")
        
        if user.is_locked:
            user.is_locked = False
            user.login_attempts = 0
            user.locked_at = None
            await db.commit()
            print(">> Cuenta demo DESBLOQUEADA exitosamente")
        else:
            print(">> La cuenta demo NO estaba bloqueada")
        
        await db.refresh(user)
        print(f"Estado final: is_locked={user.is_locked}, attempts={user.login_attempts}")


if __name__ == "__main__":
    asyncio.run(unlock_demo())
