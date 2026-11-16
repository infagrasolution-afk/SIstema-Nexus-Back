"""
Contexto Forense por Petición (Request Audit Context) usando contextvars.
Permite que cualquier servicio o logger (como MovementLogger) conozca automáticamente
la Dirección IP real, el Navegador/Dispositivo (User-Agent), el Endpoint y el Usuario
que disparó la operación sin tener que pasar el objeto `Request` manualmente a cada función.
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any

_audit_ctx: ContextVar[Dict[str, Any]] = ContextVar("apex_audit_ctx", default={})


def set_audit_context(
    *,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> None:
    current = dict(_audit_ctx.get() or {})
    if ip_address is not None:
        current["ip_address"] = ip_address
    if user_agent is not None:
        current["user_agent"] = user_agent
    if method is not None:
        current["method"] = method
    if path is not None:
        current["path"] = path
    if user_id is not None:
        current["user_id"] = user_id
    if username is not None:
        current["username"] = username
    if tenant_id is not None:
        current["tenant_id"] = tenant_id
    _audit_ctx.set(current)


def get_audit_context() -> Dict[str, Any]:
    return dict(_audit_ctx.get() or {})


def clear_audit_context() -> None:
    _audit_ctx.set({})

