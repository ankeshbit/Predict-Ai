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
        DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require",
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
        DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require",
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
        DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    # Must not raise
    check_production_security()


def test_production_aborts_on_model_bundle_version_mismatch(monkeypatch):
    """Production startup must abort if verify_all detects library version mismatch (strict_versions=True)."""
    from app.core import config
    from app.main import verify_active_model_artifacts
    from app.ml.verify_artifacts import ArtifactVerificationError

    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a_very_secure_production_secret_key_at_least_32_chars!",
        DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require",
    )
    monkeypatch.setattr(config, "settings", prod_settings)
    monkeypatch.setattr("app.main.settings", prod_settings)

    # In production, verify_active_model_artifacts enforces strict_versions=True.
    # Any library or Python version mismatch must raise ArtifactVerificationError.
    with pytest.raises(ArtifactVerificationError, match="library version mismatch"):
        verify_active_model_artifacts()

