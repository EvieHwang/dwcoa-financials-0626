"""Budget read/write logic (R1-R6), as plain testable functions.

Business logic lives here, not in the route handler (constitution). The router
owns the HTTP surface, guards, and edge validation; this module owns the SQL and
the R1 entry shape. Money is integer cents throughout. The effective-timing rule
is delegated to `app.proration` so there is exactly one resolution.
"""
from __future__ import annotations

import sqlite3

from .proration import effective_timing


def _entry(row: sqlite3.Row) -> dict:
    """Build one R1 budget entry from a categories-LEFT-JOIN-budgets row."""
    amount = row["annual_amount"] if row["annual_amount"] is not None else 0
    timing = row["timing"]
    default = row["category_default_timing"]
    return {
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "category_type": row["category_type"],
        "annual_amount": amount,
        "timing": timing,
        "category_default_timing": default,
        "effective_timing": effective_timing(timing, default),
    }


def list_year_budgets(con: sqlite3.Connection, year: int) -> list[dict]:
    """Every budgetable line for the year, in the R1 entry shape (R1).

    Budgetable = every *active* category of type Income/Expense (zero-filled when
    it has no row for the year), **plus** any category that already has a budget
    row for the year (so migrated/now-inactive or Transfer/Internal lines that
    were budgeted stay visible/editable).
    """
    rows = con.execute(
        """
        SELECT c.id    AS category_id,
               c.name  AS category_name,
               c.type  AS category_type,
               c.timing AS category_default_timing,
               b.annual_amount AS annual_amount,
               b.timing        AS timing
        FROM categories c
        LEFT JOIN budgets b
               ON b.category_id = c.id AND b.year = ?
        WHERE (c.active = 1 AND c.type IN ('Income', 'Expense'))
           OR b.id IS NOT NULL
        ORDER BY c.type, c.name
        """,
        (year,),
    ).fetchall()
    return [_entry(row) for row in rows]


def get_entry(con: sqlite3.Connection, year: int, category_id: int) -> dict | None:
    """A single line in the R1 entry shape (used by upsert to echo the stored
    line). Returns None when no row exists for (year, category_id)."""
    row = con.execute(
        """
        SELECT c.id    AS category_id,
               c.name  AS category_name,
               c.type  AS category_type,
               c.timing AS category_default_timing,
               b.annual_amount AS annual_amount,
               b.timing        AS timing
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.year = ? AND b.category_id = ?
        """,
        (year, category_id),
    ).fetchone()
    return _entry(row) if row is not None else None


def category_exists(con: sqlite3.Connection, category_id: int) -> bool:
    return con.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone() is not None


def get_lock(con: sqlite3.Connection, year: int) -> tuple[bool, str | None]:
    row = con.execute(
        "SELECT locked, locked_at FROM budget_locks WHERE year = ?", (year,)
    ).fetchone()
    if row is None:
        return False, None
    return bool(row["locked"]), row["locked_at"]


def count_year(con: sqlite3.Connection, year: int) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM budgets WHERE year = ?", (year,)
    ).fetchone()[0]


def upsert_line(
    con: sqlite3.Connection,
    *,
    year: int,
    category_id: int,
    annual_amount: int,
    timing: str | None,
) -> None:
    """Insert or replace the unique (year, category_id) line, holding the
    UNIQUE(year, category_id) invariant. A None timing clears the override."""
    con.execute(
        "INSERT INTO budgets (year, category_id, annual_amount, timing) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(year, category_id) DO UPDATE SET "
        "annual_amount = excluded.annual_amount, timing = excluded.timing",
        (year, category_id, annual_amount, timing),
    )


def delete_line(con: sqlite3.Connection, *, year: int, category_id: int) -> int:
    """Delete the (year, category_id) line; return the count removed (0 if none —
    idempotent)."""
    cur = con.execute(
        "DELETE FROM budgets WHERE year = ? AND category_id = ?",
        (year, category_id),
    )
    return cur.rowcount


def copy_year(
    con: sqlite3.Connection,
    *,
    from_year: int,
    to_year: int,
    overwrite: bool,
) -> int:
    """Copy every from_year line into to_year, carrying amount AND timing
    override verbatim; return the count copied. With overwrite, to_year's set is
    replaced. The caller wraps this in a single transaction (atomic).
    """
    rows = con.execute(
        "SELECT category_id, annual_amount, timing FROM budgets WHERE year = ?",
        (from_year,),
    ).fetchall()
    if overwrite:
        con.execute("DELETE FROM budgets WHERE year = ?", (to_year,))
    for row in rows:
        con.execute(
            "INSERT INTO budgets (year, category_id, annual_amount, timing) "
            "VALUES (?, ?, ?, ?)",
            (to_year, row["category_id"], row["annual_amount"], row["timing"]),
        )
    return len(rows)


def set_lock(con: sqlite3.Connection, *, year: int, locked: bool) -> str | None:
    """Set the year's lock state; stamp locked_at when locking, clear it when
    unlocking. Returns the stored locked_at."""
    con.execute(
        "INSERT INTO budget_locks (year, locked, locked_at) "
        "VALUES (?, ?, CASE WHEN ? THEN datetime('now') ELSE NULL END) "
        "ON CONFLICT(year) DO UPDATE SET "
        "locked = excluded.locked, locked_at = excluded.locked_at",
        (year, 1 if locked else 0, 1 if locked else 0),
    )
    row = con.execute(
        "SELECT locked_at FROM budget_locks WHERE year = ?", (year,)
    ).fetchone()
    return row["locked_at"] if row is not None else None
