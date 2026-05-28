from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "ERP Multi-Tenant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres Connection String from Render
    DATABASE_URL: str = "postgresql://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a.virginia-postgres.render.com/erp_db_x91k"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # asyncpg requires the scheme to be postgresql+asyncpg
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

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
