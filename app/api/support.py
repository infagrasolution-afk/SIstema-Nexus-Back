from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.api.deps import get_master_db, get_current_user
from app.domain.error_log import AppErrorLog
from app.domain.user import User
from app.schemas.error_log import AppErrorLogCreate, AppErrorLogResponse

router = APIRouter()

@router.post("/error-logs", response_model=AppErrorLogResponse)
async def create_error_log(
    log_in: AppErrorLogCreate,
    db: AsyncSession = Depends(get_master_db)
):
    """
    Endpoint público para registrar errores que experimentan los clientes en el frontend.
    """
    new_log = AppErrorLog(
        tenant_id=log_in.tenant_id,
        user_id=log_in.user_id,
        username=log_in.username,
        error_message=log_in.error_message,
        error_stack=log_in.error_stack,
        component=log_in.component,
        url=log_in.url,
        user_agent=log_in.user_agent
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    return new_log

@router.get("/error-logs", response_model=List[AppErrorLogResponse])
async def list_error_logs(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna la lista completa de errores registrados para soporte técnico (Solo Superusuarios/Administradores del SaaS).
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere cuenta de Superadministrador SaaS.")
    
    result = await db.execute(
        select(AppErrorLog).order_by(desc(AppErrorLog.created_at)).limit(100)
    )
    return result.scalars().all()
