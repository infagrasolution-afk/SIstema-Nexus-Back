from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "ERP Multi-Tenant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres Connection String from Render
    DATABASE_URL: str = "postgresql://admin:rvham9UEK8B8yhvKcRYk42BuMNrCaeVn@dpg-d95fdt5ckfvc73ba7d9g-a.virginia-postgres.render.com/erp_db_qoj0"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "render.com" in url and "ssl=require" not in url:
            url += "&ssl=require" if "?" in url else "?ssl=require"
        return url

    # JWT
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS — en producción configurar como variable de entorno
    # Ejemplo: ALLOWED_ORIGINS="https://tu-frontend.onrender.com,https://otro-origen.com"
    ALLOWED_ORIGINS: str = "*"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        import os
        # Solo valida en produccion (cuando DATABASE_URL es externa)
        if v == "supersecretkey_change_me_in_production":
            import warnings
            warnings.warn(
                "\u26a0️  ADVERTENCIA: SECRET_KEY usa el valor por defecto inseguro. "
                "Configura la variable de entorno SECRET_KEY en Render.",
                stacklevel=2
            )
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
