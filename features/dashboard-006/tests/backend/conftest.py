"""Shared fixtures for the Dashboard backend test suite.

Written against the contracts in spec.md before /build implements the dashboard
aggregation module and the `/api/dashboard` router — so these tests are expected
to fail (ImportError / 404 / red) until that code exists. The backend package
path is resolved from this file's own location, never an absolute sandbox path.

Reuses foundation's env-driven `create_app` and auth fixtures, and adds direct-DB
helpers (insert budgets, insert transactions) so dashboard tests build their
worked examples without going through the very endpoint they verify.
"""
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pytest

# features/dashboard-006/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"

# Seeded account friendly-names (seed.py ACCOUNTS).
ACCOUNT_NAMES = ("Savings", "Checking", "Reserve Fund")


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
    # Origin reads as same-origin.
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


# --- direct DB helpers (independent of the dashboard endpoint) -------------

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


def first_category_of_type(db_path, type_):
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT id, name FROM categories WHERE type = ? ORDER BY id LIMIT 1",
            (type_,),
        ).fetchone()
        assert row is not None, f"no seeded category of type {type_!r}"
        return row["id"], row["name"]
    finally:
        con.close()


def income_category_ids(db_path):
    con = connect(db_path)
    try:
        return [
            r["id"]
            for r in con.execute(
                "SELECT id FROM categories WHERE type = 'Income' ORDER BY id"
            )
        ]
    finally:
        con.close()


def insert_budget(db_path, *, year, category_id, annual_amount, timing=None):
    """Insert/replace a budget row directly (integer cents)."""
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


def clear_budgets(db_path, year):
    con = connect(db_path)
    try:
        con.execute("DELETE FROM budgets WHERE year = ?", (year,))
        con.commit()
    finally:
        con.close()


def insert_txn(
    db_path,
    *,
    account_name,
    post_date,
    description="txn",
    debit=None,
    credit=None,
    balance=0,
    category_id=None,
    account_number="****0000",
    status="Posted",
):
    """Insert one transaction directly (all money integer cents)."""
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO transactions "
            "(account_number, account_name, post_date, description, debit, "
            "credit, status, balance, category_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_number,
                account_name,
                post_date,
                description,
                debit,
                credit,
                status,
                balance,
                category_id,
            ),
        )
        con.commit()
    finally:
        con.close()


def table_counts(db_path):
    """Row counts for the tables a write would touch — used to prove a GET is
    read-only (no mutation)."""
    con = connect(db_path)
    try:
        return {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("transactions", "budgets", "budget_locks", "app_config",
                      "categories")
        }
    finally:
        con.close()


def get_dashboard(client, as_of=None):
    """GET /api/dashboard, returning the parsed JSON (asserts 200)."""
    url = "/api/dashboard"
    if as_of is not None:
        url += f"?as_of={as_of}"
    res = client.get(url)
    assert res.status_code == 200, (res.status_code, res.text)
    return res.json()
