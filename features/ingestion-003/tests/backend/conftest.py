"""Shared fixtures for the Ingestion backend test suite.

Written against the contracts in spec.md before /build implements the ingestion
module, the transactions router, and the dashboard UI — so they are expected to
fail (ImportError / red) until the backend exists. The backend package path is
resolved from this file's own location, never an absolute sandbox path.

Reuses foundation's app-factory / auth fixtures (same env-driven create_app),
and adds CSV-building and direct-DB helpers so list tests don't depend on the
upload path and upload tests don't depend on the list path.
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

import bcrypt
import pytest

# features/ingestion-003/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PW = "admin-secret-pw"
BOARD_PW = "board-secret-pw"
SESSION_SECRET = "test-session-secret-key-0123456789"

# The accounts foundation seeds (masked_number -> name). The upload path maps
# against these; an account number outside this set is "unknown" (R7).
SEEDED_ACCOUNTS = {
    "****7145": "Savings",
    "****9242": "Checking",
    "****9226": "Reserve Fund",
}
UNKNOWN_ACCT = "****0000"

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
    # https base_url so the cookie jar stores/sends the Secure session cookie,
    # and so a missing Origin header reads as same-origin (CSRF guard allows it).
    with TestClient(make_app(), base_url="https://testserver") as c:
        yield c


def do_login(client, password):
    return client.post("/api/auth/login", json={"password": password})


# admin_client / viewer_client build their *own* TestClient (their own cookie
# jar) rather than logging in on the shared `client` fixture. Otherwise a test
# that asks for both `viewer_client` and `client` would receive the same logged-in
# instance for `client`, making the "anonymous request -> 401" assertion in
# test_upload_requires_admin unobservable. All three apps point at the same
# DATABASE_PATH (migrations + seed are idempotent), so DB state is shared.
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


# --- CSV / upload helpers --------------------------------------------------

def bank_row(account, date, description, debit="", credit="", balance="0.00",
             check="", status="Posted"):
    """Build one CSV data row in the bank export's column order."""
    return [account, date, check, description, debit, credit, status, balance]


def csv_text(rows, header=BANK_HEADER):
    """Render header + data rows to CSV text the way a bank export would."""
    buf = io.StringIO()
    w = csv.writer(buf)
    if header is not None:
        w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def upload(client, content, **kwargs):
    """POST CSV content as a multipart file to the ingestion endpoint."""
    return client.post(
        "/api/transactions/upload",
        files={"file": ("history.csv", content, "text/csv")},
        **kwargs,
    )


# --- direct DB helpers (independent of the upload path) --------------------

def connect(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def count_transactions(db_path):
    con = connect(db_path)
    try:
        return con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    finally:
        con.close()


def insert_txn(db_path, *, account_number, account_name, post_date, description,
               debit=None, credit=None, balance=0, status="Posted",
               check_number=None, category_id=None):
    """Insert a transaction directly, so list/category tests don't rely on upload."""
    con = connect(db_path)
    try:
        cur = con.execute(
            """
            INSERT INTO transactions (
                account_number, account_name, post_date, check_number,
                description, debit, credit, status, balance, category_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_number, account_name, post_date, check_number, description,
             debit, credit, status, balance, category_id),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def first_category_id(db_path):
    """Any seeded category id, for exercising category-preservation."""
    con = connect(db_path)
    try:
        return con.execute("SELECT id FROM categories ORDER BY id LIMIT 1").fetchone()[0]
    finally:
        con.close()
