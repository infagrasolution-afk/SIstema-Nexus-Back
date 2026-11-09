from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete
from typing import List
from app.api.deps import get_master_db, get_current_user
from app.domain.error_log import AppErrorLog
from app.domain.user import User
from app.schemas.error_log import AppErrorLogCreate, AppErrorLogResponse

router = APIRouter()

MAX_STORED_LOGS = 1000


@router.post("/error-logs", response_model=AppErrorLogResponse)
async def create_error_log(
    log_in: AppErrorLogCreate,
    db: AsyncSession = Depends(get_master_db)
):
    """
    Registra incidencias del frontend para soporte técnico con protección contra sobrecarga.
    """
    # Truncar cadenas para evitar abusos de almacenamiento
    safe_msg = (log_in.error_message or "")[:500]
    safe_stack = (log_in.error_stack or "")[:4000]
    safe_url = (log_in.url or "")[:300]
    safe_ua = (log_in.user_agent or "")[:300]

    new_log = AppErrorLog(
        tenant_id=log_in.tenant_id,
        user_id=log_in.user_id,
        username=log_in.username,
        error_message=safe_msg,
        error_stack=safe_stack,
        component=log_in.component,
        url=safe_url,
        user_agent=safe_ua
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)

    # Mantener la tabla bajo control de espacio
    count = (await db.execute(select(func.count(AppErrorLog.id)))).scalar() or 0
    if count > MAX_STORED_LOGS:
        # Eliminar los 100 más antiguos
        oldest_ids = select(AppErrorLog.id).order_by(AppErrorLog.created_at.asc()).limit(100)
        await db.execute(delete(AppErrorLog).where(AppErrorLog.id.in_(oldest_ids)))
        await db.commit()

    return new_log


@router.get("/error-logs", response_model=List[AppErrorLogResponse])
async def list_error_logs(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna la lista de incidencias registradas (Exclusivo Superadministrador SaaS)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso exclusivo para el equipo de soporte y administración central de APEX ERP."
        )

    result = await db.execute(
        select(AppErrorLog).order_by(desc(AppErrorLog.created_at)).limit(100)
    )
    return result.scalars().all()


@router.delete("/error-logs/{log_id}")
async def delete_error_log(
    log_id: int,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Elimina una incidencia resuelta."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso restringido a administradores centrales."
        )

    result = await db.execute(select(AppErrorLog).where(AppErrorLog.id == log_id))
    log_entry = result.scalars().first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Registro de incidencia no encontrado")

    await db.delete(log_entry)
    await db.commit()
    return {"message": f"Incidencia #{log_id} eliminada correctamente"}


@router.delete("/error-logs")
async def clear_all_error_logs(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Limpia el historial completo de incidencias."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso restringido a administradores centrales."
        )

    await db.execute(delete(AppErrorLog))
    await db.commit()
    return {"message": "Historial de incidencias depurado correctamente."}
