"""
Pytest fixtures for backend tests
"""

import os

import pytest

# Ensure fast timeout in tests so DB connection attempts don't stall
os.environ.setdefault("DB_CONNECT_TIMEOUT", "2")

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
