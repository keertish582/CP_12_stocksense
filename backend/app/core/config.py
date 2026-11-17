from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "StockSense"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/stocksense_db"
    # Fallback to SQLite for local development/testing without docker/postgres
    FALLBACK_SQLITE_URL: str = "sqlite:///./stocksense.db"
    USE_SQLITE_FALLBACK: bool = True
    
    # Security
    JWT_SECRET_KEY: str = "stocksense-super-secret-dev-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours for dev/work session
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Business & Default Planning
    DEFAULT_WAREHOUSE_CODE: str = "WH-BLR-01"
    DEFAULT_WAREHOUSE_NAME: str = "Central Distribution Hub - Bengaluru"
    DEFAULT_COVERAGE_DAYS: int = 14
    MIN_FORECAST_HORIZON_DAYS: int = 30
    DEFAULT_LEAD_TIME_DAYS: int = 7
    DEFAULT_SAFETY_STOCK: int = 10
    
    # Timezone & Currency
    DISPLAY_TIMEZONE: str = "Asia/Kolkata"
    CURRENCY_CODE: str = "INR"
    CURRENCY_SYMBOL: str = "₹"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
