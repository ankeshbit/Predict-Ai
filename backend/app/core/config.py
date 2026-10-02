"""
Application configuration via Pydantic Settings
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "insecure_dev_secret_key_minimum_32_characters_long"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Neon PostgreSQL database connections
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai"
    DATABASE_URL_DIRECT: str = "postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai"
    DB_CONNECT_TIMEOUT: int = 10  # Seconds; ~10s for Neon cold start, override to 2 in tests

    # CORS configuration
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Rate limiting configuration
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_SCORING: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "120/minute"

    # Model artifacts directory
    MODEL_ARTIFACTS_DIR: str = "model_artifacts"

    # Initial admin seed
    INITIAL_ADMIN_EMAIL: str = "admin@predicore.internal"
    INITIAL_ADMIN_PASSWORD: str = "AdminSecurePass123!"
    INITIAL_ENGINEER_EMAIL: str = "engineer@predicore.internal"
    INITIAL_ENGINEER_PASSWORD: str = "EngineerSecurePass123!"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
