from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ERP Multi-Tenant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres Connection String from Render
    DATABASE_URL: str = "postgresql://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a/erp_db_x91k"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # asyncpg requires the scheme to be postgresql+asyncpg
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

    # JWT
    SECRET_KEY: str = "supersecretkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15 # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30 # 30 days

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
