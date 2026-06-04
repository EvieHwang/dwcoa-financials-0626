"""Shared fixtures for the legacy-migration backend test suite.

These tests are written against spec.md before /build implements the importer,
the budget_locks migration, and the seed changes, so they are expected to fail
(ImportError / red) until the backend exists. The backend package path is
resolved from this file's own location, never an absolute sandbox path.

The real production `dwcoa.db` holds private financial data and is never
committed. Instead, `legacy_db` builds a *synthetic legacy-schema* SQLite file
in a temp dir, populated with rows that exercise the edge cases the importer
must handle. The importer transforms this fixture; assertions inspect the output.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

# features/legacy-migration-002/tests/backend/conftest.py -> repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# --- Legacy schema (mirrors the live production dwcoa.db) -------------------
# REAL money, ownership as a fraction, the deprecated units.past_due_balance
# column, budget_locks WITH locked_by, and a legacy reporting view.
LEGACY_SCHEMA = """
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    masked_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    default_account TEXT,
    timing TEXT NOT NULL DEFAULT 'monthly',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    ownership_pct REAL NOT NULL,
    past_due_balance REAL NOT NULL DEFAULT 0
);
CREATE TABLE unit_past_dues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_number TEXT NOT NULL,
    year INTEGER NOT NULL,
    past_due_balance REAL NOT NULL DEFAULT 0,
    UNIQUE(unit_number, year)
);
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    annual_amount REAL NOT NULL DEFAULT 0,
    timing TEXT,
    UNIQUE(year, category_id)
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    post_date TEXT NOT NULL,
    check_number TEXT,
    description TEXT NOT NULL,
    debit REAL,
    credit REAL,
    status TEXT NOT NULL DEFAULT 'Posted',
    balance REAL NOT NULL,
    category_id INTEGER,
    auto_category_id INTEGER,
    confidence INTEGER,
    needs_review INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE categorize_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 90,
    priority INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE budget_locks (
    year INTEGER PRIMARY KEY,
    locked INTEGER NOT NULL DEFAULT 0,
    locked_at TEXT,
    locked_by TEXT
);
CREATE VIEW v_unit_summary AS
    SELECT u.id, u.number AS unit, u.ownership_pct FROM units u ORDER BY u.number;
"""

# Categories: ids 1..5. Note id 1 is named "Interest" (the legacy production
# name) which differs from the foundation seed's "Interest income" — the
# importer must carry the legacy name, not the seed's.
LEGACY_CATEGORIES = [
    (1, "Interest", "Income", "Any", "monthly"),
    (2, "Grounds/Landscaping", "Expense", "Checking", "monthly"),
    (3, "Insurance Premiums", "Expense", "Checking", "monthly"),
    (4, "Reserve Fund", "Expense", "Reserve Fund", "annual"),
    (5, "Dues 101", "Income", "Savings", "monthly"),
]

# Units: ownership as fractions; deprecated past_due_balance set non-zero to
# confirm it is dropped (not carried) on import.
LEGACY_UNITS = [
    (1, "101", 0.117, 3981.85),
    (2, "102", 0.104, 0.0),
    (3, "103", 0.112, 0.0),
    (4, "302", 0.104, 0.0),
]

# Real past-due values, including the unit-302 correction (625.44).
LEGACY_UNIT_PAST_DUES = [
    (1, "101", 2025, 3981.85),
    (2, "302", 2025, 625.44),
]

# Multi-year budgets; one row (id 2) has NULL timing to confirm NULL passthrough.
LEGACY_BUDGETS = [
    (1, 2024, 2, 12000.00, "monthly"),
    (2, 2024, 3, 4500.00, None),
    (3, 2025, 2, 12500.00, "monthly"),
    (4, 2025, 3, 4600.00, "monthly"),
    (5, 2025, 1, 26.00, "monthly"),
]

# Transactions across two years: credit-only, debit-only, a negative balance,
# and NULL on the unused side. 832.06 is a deliberate float-artifact value.
# columns: id, acct_no, acct_name, post_date, check_no, desc, debit, credit,
#          status, balance, category_id, auto_category_id, confidence, needs_review
LEGACY_TRANSACTIONS = [
    (100, "****7145", "Savings", "2024-01-02", "", "External Deposit J ERNAST", None, 832.06, "Posted", 840.71, 5, 5, 100, 0),
    (101, "****9242", "Checking", "2024-01-02", "", "NWEDI Insurance", 336.00, None, "Posted", 504.71, 3, 3, 100, 0),
    (102, "****9242", "Checking", "2024-06-15", "", "MCCARY Landscaping", 125.85, None, "Posted", -50.25, 2, 2, 100, 0),
    (103, "****7145", "Savings", "2025-03-01", "", "Dividend/Interest", None, 26.00, "Posted", 49.75, 1, 1, 90, 0),
]

LEGACY_RULES = [
    (1, "MCCARY", 2, 100, 100, 1),
    (2, "Dividend/Interest", 1, 100, 100, 1),
]

LEGACY_APP_CONFIG = [
    ("current_year", "2026"),
    ("last_upload_at", "2026-05-19T00:54:07.162920"),
]

# 2024 and 2025 locked; locked_by populated to confirm it is dropped on import.
LEGACY_BUDGET_LOCKS = [
    (2024, 1, "2026-02-01 03:47:07", "treasurer"),
    (2025, 1, "2026-02-12 02:45:35", "treasurer"),
]

LEGACY_ACCOUNTS = [
    (1, "****7145", "Savings"),
    (2, "****9242", "Checking"),
    (3, "****9226", "Reserve Fund"),
]


def _build_legacy_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript(LEGACY_SCHEMA)
        con.executemany("INSERT INTO accounts VALUES (?,?,?)", LEGACY_ACCOUNTS)
        con.executemany(
            "INSERT INTO categories (id,name,type,default_account,timing) VALUES (?,?,?,?,?)",
            LEGACY_CATEGORIES,
        )
        con.executemany(
            "INSERT INTO units (id,number,ownership_pct,past_due_balance) VALUES (?,?,?,?)",
            LEGACY_UNITS,
        )
        con.executemany(
            "INSERT INTO unit_past_dues (id,unit_number,year,past_due_balance) VALUES (?,?,?,?)",
            LEGACY_UNIT_PAST_DUES,
        )
        con.executemany(
            "INSERT INTO budgets (id,year,category_id,annual_amount,timing) VALUES (?,?,?,?,?)",
            LEGACY_BUDGETS,
        )
        con.executemany(
            "INSERT INTO transactions "
            "(id,account_number,account_name,post_date,check_number,description,"
            "debit,credit,status,balance,category_id,auto_category_id,confidence,needs_review) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            LEGACY_TRANSACTIONS,
        )
        con.executemany(
            "INSERT INTO categorize_rules (id,pattern,category_id,confidence,priority,active) "
            "VALUES (?,?,?,?,?,?)",
            LEGACY_RULES,
        )
        con.executemany("INSERT INTO app_config (key,value) VALUES (?,?)", LEGACY_APP_CONFIG)
        con.executemany(
            "INSERT INTO budget_locks (year,locked,locked_at,locked_by) VALUES (?,?,?,?)",
            LEGACY_BUDGET_LOCKS,
        )
        con.commit()
    finally:
        con.close()


@pytest.fixture
def legacy_db(tmp_path):
    """Path to a freshly built synthetic legacy-schema source DB."""
    path = tmp_path / "legacy.db"
    _build_legacy_db(path)
    return path


@pytest.fixture
def imported_db(legacy_db, tmp_path):
    """Run the importer and return the path to the new-schema output DB."""
    from app.legacy_import import build_target

    out = tmp_path / "out.db"
    build_target(str(legacy_db), str(out))
    return out


def connect(path):
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    return con
