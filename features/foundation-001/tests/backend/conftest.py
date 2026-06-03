"""Shared fixtures for the Foundation backend test suite.

These tests are written against the contracts in spec.md before /build
implements them, so they are expected to fail (ImportError / red) until the
backend exists. The path to the backend package is resolved from this file's
own location, never an absolute sandbox path.
"""
import sys
from pathlib import Path

import bcrypt
import pytest

# features/foundation-001/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"
COOKIE = "dwcoa_session"


def bcrypt_hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """Set the four required config vars to known test values."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt_hash(ADMIN_PW))
    monkeypatch.setenv("BOARD_PASSWORD_HASH", bcrypt_hash(BOARD_PW))
    monkeypatch.setenv("SESSION_SECRET", SESSION_SECRET)
    return {"db_path": db_path}


@pytest.fixture
def make_app(app_env):
    """Factory that builds a fresh app reading the current env."""
    def _make():
        from app.main import create_app
        return create_app()
    return _make


@pytest.fixture
def client(make_app):
    from fastapi.testclient import TestClient
    # https base_url so the httpx cookie jar stores/sends the Secure session cookie
    with TestClient(make_app(), base_url="https://testserver") as c:
        yield c


def do_login(client, password):
    return client.post("/api/auth/login", json={"password": password})


@pytest.fixture
def admin_client(client):
    assert do_login(client, ADMIN_PW).status_code == 200
    return client


@pytest.fixture
def viewer_client(client):
    assert do_login(client, BOARD_PW).status_code == 200
    return client
