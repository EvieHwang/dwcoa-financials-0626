"""Offline, one-time importer: legacy production dwcoa.db -> new-schema DB.

A pure, tested transform-and-load (no business logic, no runtime surface). It
reads the legacy SQLite database, converts its representation into the new
schema, and writes a ready-to-deploy SQLite file for the Fly volume, preserving
primary keys so every foreign-key reference stays intact.

The two converters (`to_cents`, `to_permille`) are the highest-value surface:
they convert via decimal arithmetic on the value's exact decimal string so
binary-float artifacts can never shift the result, rounding half away from zero.

See `backend/docs/legacy-import.md` for the operator runbook (R11).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .db import get_connection
from .migrations import run_migrations

# --- Converters (R1 / R2) ---------------------------------------------------


def to_cents(value: float | None) -> int | None:
    """Map a legacy dollar `REAL` (or None) to exact integer cents (or None).

    Half rounds away from zero. Uses the value's exact decimal string so binary
    float artifacts (832.06 * 100 == 83205.99999999999) never shift the result.
    """
    if value is None:
        return None
    cents = (Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(cents)


def to_permille(value: float) -> int:
    """Map a legacy ownership fraction `REAL` (0.117) to integer per-mille (117)."""
    permille = (Decimal(str(value)) * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(permille)


# --- Expected legacy source shape (R7) --------------------------------------
# Mirrors an empirical dump of the *live* production dwcoa.db, NOT the stale
# vendored reference/.../schema.sql. The importer validates the source against
# this up front and aborts loudly on any mismatch, so it can never silently skip
# a column or table (e.g. trusting a reference schema that lacks categories.timing).
EXPECTED_SOURCE_SCHEMA: dict[str, set[str]] = {
    "accounts": {"id", "masked_number", "name"},
    "categories": {"id", "name", "type", "default_account", "timing", "active"},
    "units": {"id", "number", "ownership_pct", "past_due_balance"},
    "unit_past_dues": {"id", "unit_number", "year", "past_due_balance"},
    "budgets": {"id", "year", "category_id", "annual_amount", "timing"},
    "transactions": {
        "id", "account_number", "account_name", "post_date", "check_number",
        "description", "debit", "credit", "status", "balance",
        "category_id", "auto_category_id", "confidence", "needs_review",
    },
    "categorize_rules": {
        "id", "pattern", "category_id", "confidence", "priority", "active",
    },
    "app_config": {"key", "value"},
    "budget_locks": {"year", "locked", "locked_at", "locked_by"},
}


class LegacyImportError(RuntimeError):
    """Raised on any precondition or load failure; the target is never left partial."""


def _validate_source_schema(con: sqlite3.Connection) -> None:
    """Raise LegacyImportError unless every expected table/column is present."""
    for table, expected_cols in EXPECTED_SOURCE_SCHEMA.items():
        info = con.execute(f"PRAGMA table_info({table})").fetchall()
        if not info:
            raise LegacyImportError(
                f"source schema mismatch: missing table '{table}'"
            )
        present = {row[1] for row in info}
        missing = expected_cols - present
        if missing:
            raise LegacyImportError(
                f"source schema mismatch: table '{table}' missing column(s) "
                f"{sorted(missing)} — refusing to silently skip data"
            )


def _has_transaction_data(path: Path) -> bool:
    """True if `path` is a DB that already holds transaction rows."""
    try:
        con = sqlite3.connect(str(path))
    except sqlite3.Error:
        return False
    try:
        row = con.execute("SELECT COUNT(*) FROM transactions").fetchone()
        return bool(row and row[0] > 0)
    except sqlite3.Error:
        return False
    finally:
        con.close()


def _remove_db_files(path: Path) -> None:
    """Remove a SQLite file and any sidecar journal/WAL files."""
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            p.unlink()


def _load(src: sqlite3.Connection, dst: sqlite3.Connection) -> None:
    """Transform-and-load every table, parents before children, PKs preserved."""
    # accounts
    for r in src.execute("SELECT id, masked_number, name FROM accounts"):
        dst.execute(
            "INSERT INTO accounts (id, masked_number, name) VALUES (?, ?, ?)",
            (r["id"], r["masked_number"], r["name"]),
        )

    # categories — name/type/timing carried verbatim (legacy names, not seed's)
    for r in src.execute(
        "SELECT id, name, type, default_account, timing, active, created_at "
        "FROM categories"
    ):
        dst.execute(
            "INSERT INTO categories "
            "(id, name, type, default_account, timing, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["id"], r["name"], r["type"], r["default_account"], r["timing"],
             r["active"], r["created_at"]),
        )

    # units — ownership fraction -> per-mille; deprecated past_due_balance dropped
    for r in src.execute("SELECT id, number, ownership_pct FROM units"):
        dst.execute(
            "INSERT INTO units (id, number, ownership_pct) VALUES (?, ?, ?)",
            (r["id"], r["number"], to_permille(r["ownership_pct"])),
        )

    # unit_past_dues — balance -> cents
    for r in src.execute(
        "SELECT id, unit_number, year, past_due_balance FROM unit_past_dues"
    ):
        dst.execute(
            "INSERT INTO unit_past_dues (id, unit_number, year, past_due_balance) "
            "VALUES (?, ?, ?, ?)",
            (r["id"], r["unit_number"], r["year"], to_cents(r["past_due_balance"])),
        )

    # budgets — annual_amount -> cents; timing carried verbatim (incl. NULL)
    for r in src.execute(
        "SELECT id, year, category_id, annual_amount, timing FROM budgets"
    ):
        dst.execute(
            "INSERT INTO budgets (id, year, category_id, annual_amount, timing) "
            "VALUES (?, ?, ?, ?, ?)",
            (r["id"], r["year"], r["category_id"], to_cents(r["annual_amount"]),
             r["timing"]),
        )

    # transactions — debit/credit/balance -> cents (NULLs and signs preserved)
    for r in src.execute(
        "SELECT id, account_number, account_name, post_date, check_number, "
        "description, debit, credit, status, balance, category_id, "
        "auto_category_id, confidence, needs_review FROM transactions"
    ):
        dst.execute(
            "INSERT INTO transactions "
            "(id, account_number, account_name, post_date, check_number, "
            "description, debit, credit, status, balance, category_id, "
            "auto_category_id, confidence, needs_review) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (r["id"], r["account_number"], r["account_name"], r["post_date"],
             r["check_number"], r["description"], to_cents(r["debit"]),
             to_cents(r["credit"]), r["status"], to_cents(r["balance"]),
             r["category_id"], r["auto_category_id"], r["confidence"],
             r["needs_review"]),
        )

    # categorize_rules
    for r in src.execute(
        "SELECT id, pattern, category_id, confidence, priority, active, created_at "
        "FROM categorize_rules"
    ):
        dst.execute(
            "INSERT INTO categorize_rules "
            "(id, pattern, category_id, confidence, priority, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["id"], r["pattern"], r["category_id"], r["confidence"],
             r["priority"], r["active"], r["created_at"]),
        )

    # app_config — carried verbatim
    for r in src.execute("SELECT key, value, updated_at FROM app_config"):
        dst.execute(
            "INSERT INTO app_config (key, value, updated_at) VALUES (?, ?, ?)",
            (r["key"], r["value"], r["updated_at"]),
        )

    # budget_locks — carried minus the unused locked_by column
    for r in src.execute("SELECT year, locked, locked_at FROM budget_locks"):
        dst.execute(
            "INSERT INTO budget_locks (year, locked, locked_at) VALUES (?, ?, ?)",
            (r["year"], r["locked"], r["locked_at"]),
        )


def build_target(source_path: str, target_path: str, force: bool = False) -> None:
    """Build a new-schema target DB from the legacy source (R3-R7).

    All-or-nothing: validates the source up front, refuses to clobber a target
    that already holds transaction data (unless `force`), and removes any partial
    target it created if the load fails. A failed run never leaves a readable
    partial DB.
    """
    src_path = Path(source_path)
    tgt_path = Path(target_path)

    # Preconditions — never touch the target until the source is validated.
    if not src_path.exists():
        raise LegacyImportError(f"source database not found: {source_path}")
    try:
        src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise LegacyImportError(f"source database unreadable: {source_path} ({exc})")
    src.row_factory = sqlite3.Row
    try:
        _validate_source_schema(src)

        # Clobber guard (R7): refuse an occupied target unless forced.
        if tgt_path.exists():
            if _has_transaction_data(tgt_path) and not force:
                raise LegacyImportError(
                    f"target already contains transaction data: {target_path} "
                    f"(pass force=True / --force to rebuild)"
                )
            _remove_db_files(tgt_path)

        # Create the target schema *through* the foundation migration path
        # (includes the budget_locks migration), then load. Atomic: on any
        # failure, remove whatever partial target we created.
        try:
            run_migrations(str(tgt_path))
            dst = get_connection(str(tgt_path))
            try:
                _load(src, dst)
                dst.commit()
            finally:
                dst.close()
        except Exception:
            _remove_db_files(tgt_path)
            raise
    finally:
        src.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.legacy_import",
        description="One-time importer: legacy dwcoa.db -> new-schema SQLite DB.",
    )
    parser.add_argument("--source", required=True, help="path to legacy dwcoa.db")
    parser.add_argument("--target", required=True, help="path to write the new-schema DB")
    parser.add_argument(
        "--force", action="store_true",
        help="rebuild even if the target already contains transaction data",
    )
    args = parser.parse_args(argv)
    try:
        build_target(args.source, args.target, force=args.force)
    except LegacyImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"wrote new-schema DB to {args.target}")


if __name__ == "__main__":
    main()
