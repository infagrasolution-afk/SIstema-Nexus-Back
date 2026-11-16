"""
Modelo de Bitácora Forense de Seguridad e Integridad (`security_audit_logs`).
Registra de forma inmutable cada acción de creación, modificación, eliminación,
inicio de sesión o emisión fiscal en el ERP, incluyendo Usuario, Empresa, Dirección IP,
Dispositivo/Navegador (User-Agent), Ruta, Método y Datos enviados.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Identificación de Empresa y Usuario
    tenant_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(150), nullable=True, index=True)

    # Rastreo de Red y Dispositivo
    ip_address = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(350), nullable=True)

    # Detalle de la Operación
    module = Column(String(80), nullable=False, index=True)
    action = Column(String(120), nullable=False)
    http_method = Column(String(16), nullable=False)
    endpoint_path = Column(String(255), nullable=False)
    status_code = Column(Integer, nullable=True)

    # Cuerpo / Payload resumido y sanitizado (sin claves ni tokens)
    payload_summary = Column(Text, nullable=True)

