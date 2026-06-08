"""Shared fixtures for the Dues-by-unit backend test suite.

Written against the contracts in spec.md before /build implements the dues
aggregation module and the `/api/dues` router — so these tests are expected to
fail (ImportError / 404 / red) until that code exists. The backend package path
is resolved from this file's own location, never an absolute sandbox path.

Reuses foundation's env-driven `create_app` and auth fixtures, and adds direct-DB
helpers (insert budgets, transactions, and unit_past_dues baselines) so dues tests
build their worked examples without going through the endpoint they verify. All
money is integer cents; ownership is integer per-mille.
"""
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pytest

# features/dues-by-unit-007/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"

# The nine seeded units: number -> ownership per-mille (seed.py UNITS).
SEEDED_UNITS = {
    "101": 117, "102": 104, "103": 112,
    "201": 117, "202": 104, "203": 112,
    "301": 117, "302": 104, "303": 112,
}


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


def do_login(client, password):
    return client.post("/api/auth/login", json={"password": password})


@pytest.fixture
def client(make_app):
    from fastapi.testclient import TestClient

    # https base_url so the Secure session cookie is stored/sent and a missing
    # Origin reads as same-origin.
    with TestClient(make_app(), base_url="https://testserver") as c:
        yield c


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


# --- direct DB helpers (independent of the dues endpoint) ------------------

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


def set_category_active(db_path, name, active):
    con = connect(db_path)
    try:
        con.execute(
            "UPDATE categories SET active = ? WHERE name = ?",
            (1 if active else 0, name),
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


def insert_budget(db_path, *, year, category_name, annual_amount, timing=None):
    """Insert/replace a budget row by category name (integer cents)."""
    cat = category_id(db_path, category_name)
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO budgets (year, category_id, annual_amount, timing) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(year, category_id) DO UPDATE SET "
            "annual_amount = excluded.annual_amount, timing = excluded.timing",
            (year, cat, annual_amount, timing),
        )
        con.commit()
    finally:
        con.close()


def insert_past_due(db_path, *, unit_number, year, past_due_balance):
    """Insert/replace a unit_past_dues baseline row (integer cents)."""
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO unit_past_dues (unit_number, year, past_due_balance) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(unit_number, year) DO UPDATE SET "
            "past_due_balance = excluded.past_due_balance",
            (unit_number, year, past_due_balance),
        )
        con.commit()
    finally:
        con.close()


def insert_payment(db_path, *, unit_number, post_date, amount, account_name="Savings"):
    """Record a dues payment: a credit transaction categorized `Dues <unit>`."""
    cat = category_id(db_path, f"Dues {unit_number}")
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO transactions "
            "(account_number, account_name, post_date, description, debit, "
            "credit, status, balance, category_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("****0000", account_name, post_date, "dues payment", None,
             amount, "Posted", 0, cat),
        )
        con.commit()
    finally:
        con.close()


def insert_credit_to_category(db_path, *, category_name, post_date, amount,
                              account_name="Savings"):
    """Record a credit on an arbitrary category (to prove non-dues income is
    ignored)."""
    cat = category_id(db_path, category_name)
    con = connect(db_path)
    try:
        con.execute(
            "INSERT INTO transactions "
            "(account_number, account_name, post_date, description, debit, "
            "credit, status, balance, category_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("****0000", account_name, post_date, "credit", None,
             amount, "Posted", 0, cat),
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
            for t in ("transactions", "budgets", "unit_past_dues", "units",
                      "categories")
        }
    finally:
        con.close()


def get_dues(client, as_of=None):
    """GET /api/dues, returning parsed JSON (asserts 200)."""
    url = "/api/dues"
    if as_of is not None:
        url += f"?as_of={as_of}"
    res = client.get(url)
    assert res.status_code == 200, (res.status_code, res.text)
    return res.json()


def unit_row(payload, number):
    """The units[] entry for a given unit number, or None."""
    for u in payload["units"]:
        if u["unit"] == number:
            return u
    return None
