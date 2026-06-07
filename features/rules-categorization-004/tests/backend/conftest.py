"""Shared fixtures for the Rules-Categorization backend test suite.

Written against the contracts in spec.md before /build implements the
categorization engine, the migration, the rules router, the categorize-on-ingest
extension, the single-transaction fix, and the review-queue filter — so they are
expected to fail (ImportError / red) until the backend exists. The backend
package path is resolved from this file's own location, never an absolute sandbox
path.

Reuses foundation's app-factory / auth fixtures (same env-driven create_app), and
the slice-3 CSV/upload and direct-DB helpers, so engine and API tests stay
independent of one another's paths.
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pytest

# features/rules-categorization-004/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"

SEEDED_ACCOUNTS = {
    "****7145": "Savings",
    "****9242": "Checking",
    "****9226": "Reserve Fund",
}

BANK_HEADER = [
    "Account Number", "Post Date", "Check", "Description",
    "Debit", "Credit", "Status", "Balance",
]


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


# --- CSV / upload helpers (mirrors slice-3) --------------------------------

def bank_row(account, date, description, debit="", credit="", balance="0.00",
             check="", status="Posted"):
    return [account, date, check, description, debit, credit, status, balance]


def csv_text(rows, header=BANK_HEADER):
    buf = io.StringIO()
    w = csv.writer(buf)
    if header is not None:
        w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def upload(client, content, **kwargs):
    return client.post(
        "/api/transactions/upload",
        files={"file": ("history.csv", content, "text/csv")},
        **kwargs,
    )


# --- direct DB helpers -----------------------------------------------------

def connect(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def category_id_by_name(db_path, name):
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()
        return row["id"] if row else None
    finally:
        con.close()


def two_category_ids(db_path):
    """Two distinct seeded category ids, for rule-target / re-route tests."""
    con = connect(db_path)
    try:
        rows = con.execute("SELECT id FROM categories ORDER BY id LIMIT 2").fetchall()
        return rows[0]["id"], rows[1]["id"]
    finally:
        con.close()


def row_by_desc(db_path, description):
    con = connect(db_path)
    try:
        return con.execute(
            "SELECT * FROM transactions WHERE description = ?", (description,)
        ).fetchone()
    finally:
        con.close()


def insert_txn(db_path, *, account_number, account_name, post_date, description,
               debit=None, credit=None, balance=0, status="Posted",
               check_number=None, category_id=None, needs_review=0):
    """Insert a transaction directly so tests don't depend on the upload path.

    Only columns that exist before this feature's migration are named here plus
    `needs_review` (present since foundation). The categorization-source marker is
    deliberately *not* set, so a row inserted with a category_id here models a
    migrated/historical row (category set, source unset) — which the sweep must
    treat as frozen (R6).
    """
    con = connect(db_path)
    try:
        cur = con.execute(
            """
            INSERT INTO transactions (
                account_number, account_name, post_date, check_number,
                description, debit, credit, status, balance, category_id,
                needs_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_number, account_name, post_date, check_number, description,
             debit, credit, status, balance, category_id, needs_review),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def get_txn(db_path, txn_id):
    con = connect(db_path)
    try:
        return con.execute(
            "SELECT * FROM transactions WHERE id = ?", (txn_id,)
        ).fetchone()
    finally:
        con.close()
