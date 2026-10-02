"""Test production security startup constraints.

In production:
- Refuse to start with default SECRET_KEY
- Refuse to start with default/localhost DATABASE_URL
"""

import pytest

from app.core.config import Settings
from app.main import check_production_security


def test_production_refuses_default_secret_key(monkeypatch):
    from app.core import config

    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="insecure_dev_secret_key_minimum_32_characters_long",
        DATABASE_URL="postgresql+psycopg://app_user:strongpassword@ep-neon-prod.pooler.neon.tech/predict_ai?sslmode=require",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    with pytest.raises(RuntimeError, match="Insecure or default SECRET_KEY detected"):
        check_production_security()


def test_production_refuses_short_secret_key(monkeypatch):
    from app.core import config

    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="too_short_key",
        DATABASE_URL="postgresql+psycopg://app_user:strongpassword@ep-neon-prod.pooler.neon.tech/predict_ai?sslmode=require",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    with pytest.raises(RuntimeError, match="Insecure or default SECRET_KEY detected"):
        check_production_security()


def test_production_refuses_default_or_localhost_database_url(monkeypatch):
    from app.core import config

    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_secure_production_secret_key_at_least_32_chars!",
        DATABASE_URL="postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    with pytest.raises(RuntimeError, match="Default or localhost DATABASE_URL detected"):
        check_production_security()


def test_production_accepts_valid_config(monkeypatch):
    from app.core import config

    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_secure_production_secret_key_at_least_32_chars!",
        DATABASE_URL="postgresql+psycopg://app_user:strongpassword@ep-neon-prod.pooler.neon.tech/predict_ai?sslmode=require",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    # Must not raise
    check_production_security()
