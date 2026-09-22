from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Laptop Allocation Management System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database (SQLite by default; set DATABASE_URL for MySQL or PostgreSQL)
    DATABASE_URL: str = "sqlite:///./laptop_allocation.db"

    # Security / JWT
    SECRET_KEY: str = "change-me-in-production-9f8f0e2a4b6c8d0e1f2a3b4c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS — comma-separated list of allowed frontend origins
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def is_mysql(self) -> bool:
        return self.DATABASE_URL.startswith("mysql")

    @property
    def database_dialect(self) -> str:
        if self.is_postgres:
            return "postgresql"
        if self.is_mysql:
            return "mysql"
        return "sqlite"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
