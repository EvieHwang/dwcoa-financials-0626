"""Versioned, idempotent schema migrations applied at startup (D1/D2).

A `schema_migrations` table records applied versions; each migration runs at
most once. Re-running against an already-migrated database is a no-op.

Money is stored as exact integer cents and ownership as exact integer
per-mille (thousandths) — never binary floats (D5/BC7).
"""
from __future__ import annotations

import sqlite3

from .db import get_connection

# Each entry: (version, SQL). Versions apply in ascending order, once each.
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            masked_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK (type IN ('Income', 'Expense', 'Transfer', 'Internal')),
            default_account TEXT,
            timing TEXT NOT NULL DEFAULT 'monthly'
                CHECK (timing IN ('monthly', 'quarterly', 'annual')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- ownership_pct stored as exact integer per-mille (0.117 -> 117).
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL UNIQUE,
            ownership_pct INTEGER NOT NULL CHECK (ownership_pct > 0 AND ownership_pct <= 1000)
        );

        CREATE TABLE IF NOT EXISTS unit_past_dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_number TEXT NOT NULL,
            year INTEGER NOT NULL,
            past_due_balance INTEGER NOT NULL DEFAULT 0,
            UNIQUE(unit_number, year),
            FOREIGN KEY (unit_number) REFERENCES units(number)
        );

        -- annual_amount stored as exact integer cents.
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            annual_amount INTEGER NOT NULL DEFAULT 0,
            timing TEXT CHECK (timing IN ('monthly', 'quarterly', 'annual')),
            UNIQUE(year, category_id)
        );

        -- debit/credit/balance stored as exact integer cents.
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT NOT NULL,
            account_name TEXT NOT NULL,
            post_date TEXT NOT NULL,
            check_number TEXT,
            description TEXT NOT NULL,
            debit INTEGER,
            credit INTEGER,
            status TEXT NOT NULL DEFAULT 'Posted',
            balance INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER REFERENCES categories(id),
            auto_category_id INTEGER REFERENCES categories(id),
            confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
            needs_review INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS categorize_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            confidence INTEGER NOT NULL DEFAULT 90 CHECK (confidence >= 0 AND confidence <= 100),
            priority INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(post_date);
        CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_name);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
        CREATE INDEX IF NOT EXISTS idx_rules_active ON categorize_rules(active, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_budgets_year ON budgets(year);
        """,
    ),
    (
        2,
        # budget_locks: the legacy app's in-year safeguard against accidental
        # budget edits. This feature lands the table and carries lock state over;
        # enforcement (rejecting edits to a locked year) is restored in Budgets.
        # The legacy `locked_by` column is intentionally dropped — there are no
        # per-user identities in this app.
        """
        CREATE TABLE IF NOT EXISTS budget_locks (
            year INTEGER PRIMARY KEY,
            locked INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT
        );
        """,
    ),
    (
        3,
        # Rules-categorization (slice 4): additive, idempotent (guarded by the
        # schema_migrations version gate, so the un-guardable ADD COLUMNs run at
        # most once). It (a) adds nullable rule-condition columns, (b) adds a
        # nullable per-transaction categorization-source marker, (c) inserts the
        # transfer rule ONLY into an already-populated categorize_rules (the
        # migrated-production case — on a fresh DB the table is empty here and the
        # seed owns the transfer rule, so this never pre-empts the seed's
        # empty-table base-rule insert; see R8 ordering), and (d) flags the
        # uncategorized migrated backlog into the review queue while leaving
        # categorized history frozen.
        """
        ALTER TABLE categorize_rules ADD COLUMN account TEXT;
        ALTER TABLE categorize_rules ADD COLUMN amount_min INTEGER;
        ALTER TABLE categorize_rules ADD COLUMN amount_max INTEGER;

        ALTER TABLE transactions ADD COLUMN category_source TEXT;

        INSERT INTO categorize_rules
            (pattern, category_id, confidence, priority, active,
             account, amount_min, amount_max)
        SELECT 'Transfer', c.id, 100, 200, 1, NULL, NULL, NULL
        FROM categories c
        WHERE c.name = 'Transfers'
          AND EXISTS (SELECT 1 FROM categorize_rules)
          AND NOT EXISTS (
              SELECT 1 FROM categorize_rules r WHERE r.category_id = c.id
          );

        UPDATE transactions SET needs_review = 1 WHERE category_id IS NULL;
        """,
    ),
]


def _ensure_tracking(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_versions(con: sqlite3.Connection) -> set[int]:
    rows = con.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def run_migrations(db_path: str) -> None:
    """Apply any unapplied migrations in order. Idempotent and safe to re-run."""
    con = get_connection(db_path)
    try:
        _ensure_tracking(con)
        applied = _applied_versions(con)
        for version, sql in sorted(MIGRATIONS, key=lambda m: m[0]):
            if version in applied:
                continue
            con.executescript(sql)
            con.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
            con.commit()
    finally:
        con.close()
