import os
import secrets
import logging
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

logger = logging.getLogger("apex.config")

# Valores que NUNCA deben usarse como clave de firma de tokens
_INSECURE_SECRET_KEYS = {
    "",
    "supersecretkey_change_me_in_production",
    "changeme",
    "secret",
}

# Orígenes permitidos por defecto (frontend en producción + desarrollo local)
_DEFAULT_ORIGINS = (
    "https://erp-frontend-8hz1.onrender.com,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:4173,http://localhost:3000"
)


class Settings(BaseSettings):
    PROJECT_NAME: str = "APEX ERP API"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"

    # Entorno: "production" o "development".
    # Render define automáticamente la variable RENDER=true, por eso se detecta solo.
    ENVIRONMENT: str = "production" if os.getenv("RENDER") else "development"

    # ── Base de datos ─────────────────────────────────────────────────────────
    # SEGURIDAD: la URL de la base de datos NUNCA se escribe en el código.
    # Se toma de la variable de entorno DATABASE_URL (Render) o del archivo .env (local).
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def clean_database_url(cls, v: str) -> str:
        """Quita un 'DATABASE_URL=' pegado por error en Render y valida que exista."""
        v = (v or "").strip().strip('"').strip("'")
        if v.startswith("DATABASE_URL="):
            v = v.split("=", 1)[1]
        if not v:
            raise ValueError(
                "Falta la variable de entorno DATABASE_URL. "
                "Configúrala en Render (Environment) o en el archivo Backend/.env para desarrollo local."
            )
        return v

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        url = self.DATABASE_URL
        # Normalizar esquema para asyncpg
        if url.startswith("postgresql://") and "asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://") and "asyncpg" not in url:
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        # asyncpg no entiende sslmode/channel_binding: se traducen a ssl=require
        for param in ("sslmode=require", "channel_binding=require"):
            url = url.replace(f"&{param}", "").replace(f"?{param}&", "?").replace(f"?{param}", "")
        # Forzar SSL para proveedores en la nube (Render, Neon, Azure, Supabase)
        needs_ssl = any(h in url for h in ("render.com", "neon.tech", "azure.com", "supabase.co"))
        if needs_ssl and "ssl=require" not in url:
            url += "&ssl=require" if "?" in url else "?ssl=require"
        return url

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        v = (v or "").strip()
        if v in _INSECURE_SECRET_KEYS or len(v) < 32:
            # En lugar de usar una clave conocida (que permitiría falsificar sesiones),
            # se genera una clave aleatoria. Consecuencia: al reiniciar el servidor
            # todos los usuarios deben volver a iniciar sesión. Configura SECRET_KEY en Render.
            logger.warning(
                "SEGURIDAD: SECRET_KEY no está configurada o es débil (<32 caracteres). "
                "Se generó una clave aleatoria temporal. Configura SECRET_KEY en Render."
            )
            return secrets.token_urlsafe(64)
        return v

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Lista separada por comas. Ejemplo: https://mi-erp.com,https://www.mi-erp.com
    ALLOWED_ORIGINS: str = _DEFAULT_ORIGINS

    @property
    def cors_origins(self) -> List[str]:
        raw = self.ALLOWED_ORIGINS or ""
        origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        # "*" ya no se acepta: con credenciales es inseguro
        origins = [o for o in origins if o != "*"]
        return origins or [o.strip() for o in _DEFAULT_ORIGINS.split(",")]

    # ── Protección contra ataques ─────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 3          # intentos fallidos antes de bloquear la cuenta
    LOCKOUT_MINUTES: int = 15            # la cuenta se desbloquea sola pasado este tiempo
    LOGIN_RATE_LIMIT: int = 10           # intentos de login por IP...
    LOGIN_RATE_WINDOW_SECONDS: int = 300 # ...en esta ventana de tiempo
    GLOBAL_RATE_LIMIT: int = 600         # peticiones por IP por minuto (todas las rutas)
    MAX_REQUEST_BODY_MB: int = 15        # tamaño máximo de una petición (logos, importaciones CSV)

    # Documentación interactiva (/docs). Apagada en producción salvo que se active.
    ENABLE_DOCS: bool = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
