"""
api/config.py
-------------
Centralised configuration using pydantic-settings.
All values can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "Spectrum Anomaly Detection API"
    APP_VERSION: str = "2.0.0"
    ENV: str = "development"
    DEBUG: bool = False

    # ── JWT ──────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_USE_STRONG_RANDOM_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./spectrum.db"

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # ── Model ────────────────────────────────────────────────────────
    MODEL_PATH: str = "ai_model/best_model.keras"
    MODEL_CLASSES: list = ["Normal", "Jamming", "Drone"]

    # ── AI Agent / Ollama ────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"

    # ── Alert Thresholds ─────────────────────────────────────────────
    ALERT_CONFIDENCE_THRESHOLD: float = 0.75

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list = ["http://localhost:8501", "http://localhost:3000", "*"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
