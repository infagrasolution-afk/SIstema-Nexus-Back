from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "ERP Multi-Tenant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Connection String - Neon.tech (Free, no expiration)
    # En Render: sobreescribir con variable de entorno DATABASE_URL
    # IMPORTANTE: en el campo "Value" de Render pegar SOLO la URL, sin "DATABASE_URL="
    DATABASE_URL: str = "postgresql://neondb_owner:npg_I0Mxlav1AwqY@ep-mute-leaf-b5kmmegr-pooler.c-7.us-east-2.aws.neon.tech/neondb"

    @field_validator("DATABASE_URL")
    @classmethod
    def clean_database_url(cls, v: str) -> str:
        """Remove a leading 'DATABASE_URL=' if the value was pasted incorrectly in Render."""
        if v.startswith("DATABASE_URL="):
            return v.split("=", 1)[1]
        return v

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        url = self.DATABASE_URL
        # Normalizar esquema para asyncpg
        if url.startswith("postgresql://") and "asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://") and "asyncpg" not in url:
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        # Forzar SSL para Render y Neon
        needs_ssl = ("render.com" in url or "neon.tech" in url)
        if needs_ssl and "ssl=require" not in url:
            url += "&ssl=require" if "?" in url else "?ssl=require"
        # Quitar channel_binding (no soportado por asyncpg)
        url = url.replace("&channel_binding=require", "").replace("?channel_binding=require&", "?").replace("?channel_binding=require", "")
        return url

    # JWT
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    ALLOWED_ORIGINS: str = "*"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if v == "supersecretkey_change_me_in_production":
            import warnings
            warnings.warn(
                "ADVERTENCIA: SECRET_KEY usa el valor por defecto inseguro. "
                "Configura la variable de entorno SECRET_KEY en Render.",
                stacklevel=2
            )
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
