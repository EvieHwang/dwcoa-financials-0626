"""Shared fixtures for the Budgets backend test suite.

Written against the contracts in spec.md before /build implements the proration
engine, the budget read/write logic, and the `/api/budgets` router — so these
tests are expected to fail (ImportError / 404 / red) until that code exists. The
backend package path is resolved from this file's own location, never an
absolute sandbox path.

Reuses foundation's env-driven `create_app` and auth fixtures, and adds direct-DB
helpers so budget tests don't depend on the very endpoints they verify.
"""
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pytest

# features/budgets-005/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"


def bcrypt_hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt_hash(ADMIN_PW))
    monkeypatch.setenv("BOARD_PASSWORD_HASH", bcrypt_hash(BOARD_PW))
    monkeypatch.setenv("SESSION_SECRET", SESSION_SECRET)
    return {"db_path": db_path}


@pytest.fixture
def make_app(app_env):
    def _make():
        from app.main import create_app
        return create_app()
    return _make


@pytest.fixture
def client(make_app):
    from fastapi.testclient import TestClient
    # https base_url so the Secure session cookie is stored/sent and a missing
    # Origin reads as same-origin (CSRF guard allows it).
    with TestClient(make_app(), base_url="https://testserver") as c:
        yield c


def do_login(client, password):
    return client.post("/api/auth/login", json={"password": password})


@pytest.fixture
def admin_client(make_app):
    from fastapi.testclient import TestClient
    with TestClient(make_app(), base_url="https://testserver") as c:
        assert do_login(c, ADMIN_PW).status_code == 200
        yield c


@pytest.fixture
def viewer_client(make_app):
    from fastapi.testclient import TestClient
    with TestClient(make_app(), base_url="https://testserver") as c:
        assert do_login(c, BOARD_PW).status_code == 200
        yield c


# --- direct DB helpers (independent of the budgets endpoints) --------------

def connect(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def category_id(db_path, name):
    """Resolve a seeded category's id by name (seed runs on app startup)."""
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()
        assert row is not None, f"seeded category {name!r} not found"
        return row["id"]
    finally:
        con.close()


def category_id_by_type(db_path, type_):
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT id FROM categories WHERE type = ? ORDER BY id LIMIT 1",
            (type_,),
        ).fetchone()
        assert row is not None, f"no seeded category of type {type_!r}"
        return row["id"]
    finally:
        con.close()


def insert_budget(db_path, *, year, category_id, annual_amount, timing=None):
    """Insert/replace a budget row directly, bypassing the API under test."""
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO budgets (year, category_id, annual_amount, timing) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(year, category_id) DO UPDATE SET "
            "annual_amount = excluded.annual_amount, timing = excluded.timing",
            (year, category_id, annual_amount, timing),
        )
        con.commit()
    finally:
        con.close()


def get_budget_row(db_path, *, year, category_id):
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT year, category_id, annual_amount, timing FROM budgets "
            "WHERE year = ? AND category_id = ?",
            (year, category_id),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        con.close()


def count_budgets(db_path, year):
    con = connect(db_path)
    try:
        return con.execute(
            "SELECT COUNT(*) FROM budgets WHERE year = ?", (year,)
        ).fetchone()[0]
    finally:
        con.close()


def set_lock(db_path, *, year, locked):
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO budget_locks (year, locked, locked_at) "
            "VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(year) DO UPDATE SET locked = excluded.locked",
            (year, 1 if locked else 0),
        )
        con.commit()
    finally:
        con.close()
