"""Dues aggregation logic (slice 7), as plain testable functions.

Derives each unit's dues obligation from the **operating budget** and its
ownership share, tracks payments recorded against that unit's `Dues <number>`
income category, carries the prior year's balance forward from a 1/1/2025
baseline, and presents per-unit outstanding balances. Business logic lives here,
not in the route handler (constitution). Every function takes an open
`sqlite3.Connection` and integer/`date` args and returns integer-cent Python
structures — no floats anywhere (constitution: "Money").

Deliberate divergences from the dashboard (slice 6):
- **Full-annual expected, never prorated.** `annual_dues` does not depend on the
  as-of date; the proration engine is *not* used here. Only the requested year's
  `paid` is capped at the as-of date.
- **Hard separation from income/interest.** The operating-budget basis is the
  Expense side only (active Expense categories); nothing here reads, derives, or
  writes the income budget or an interest split.
"""
from __future__ import annotations

import sqlite3
from datetime import date

EXPENSE = "Expense"

# First year dues are computed; pre-2025 history is reference-only (decision).
BASE_YEAR = 2025


def operating_budget(con: sqlite3.Connection, year: int) -> int:
    """Total annual operating budget for `year`, in integer cents: the sum of
    that year's budget rows on **active Expense** categories. 0 when none.
    Income-category budgets and inactive/non-Expense categories never count."""
    row = con.execute(
        """
        SELECT COALESCE(SUM(b.annual_amount), 0) AS total
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.year = ? AND c.type = ? AND c.active = 1
        """,
        (year, EXPENSE),
    ).fetchone()
    return int(row["total"])


def annual_dues(operating_budget_cents: int, ownership_per_mille: int) -> int:
    """A unit's full-annual dues: its ownership share of the operating budget,
    rounded to the nearest cent by integer round-half-up (no float). Computed
    independently per unit; the nine shares are not reconciled to sum exactly to
    the operating budget (a cent or two of drift is accepted — decision)."""
    return (operating_budget_cents * ownership_per_mille + 500) // 1000


def unit_paid(
    con: sqlite3.Connection, unit_number: str, year: int, as_of: date
) -> int:
    """Sum of `credit` over transactions categorized `Dues <unit_number>` with
    `post_date` in calendar year `year` and `post_date <= as_of`. Integer cents,
    0 when none. Only the unit's own dues category counts."""
    row = con.execute(
        """
        SELECT COALESCE(SUM(t.credit), 0) AS paid
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE c.name = ?
          AND t.post_date >= ?
          AND t.post_date <= ?
        """,
        (f"Dues {unit_number}", f"{year}-01-01", as_of.isoformat()),
    ).fetchone()
    return int(row["paid"])


def carry_in(
    con: sqlite3.Connection, unit_number: str, ownership_per_mille: int, year: int
) -> int:
    """The balance carried into `year` (can be negative — a credit).

    - `year <= BASE_YEAR`: the unit's `unit_past_dues` baseline row (0 if none).
    - `year > BASE_YEAR`: starting from 0, for each prior year `y` in
      `[BASE_YEAR, year)`:
      `balance += past_due_balance(y) + annual_dues(y) - paid_full_year(y)`,
      where prior-year payments are counted for the **whole** year (capped at
      that year's Dec 31), independent of the requested as-of date.
    """
    if year <= BASE_YEAR:
        return _past_due_balance(con, unit_number, year)

    balance = 0
    for y in range(BASE_YEAR, year):
        op = operating_budget(con, y)
        dues = annual_dues(op, ownership_per_mille)
        paid_full_year = unit_paid(con, unit_number, y, date(y, 12, 31))
        balance += _past_due_balance(con, unit_number, y) + dues - paid_full_year
    return balance


def _past_due_balance(con: sqlite3.Connection, unit_number: str, year: int) -> int:
    """The unit's `unit_past_dues` baseline for `year`, 0 when no row."""
    row = con.execute(
        "SELECT past_due_balance FROM unit_past_dues "
        "WHERE unit_number = ? AND year = ?",
        (unit_number, year),
    ).fetchone()
    return int(row["past_due_balance"]) if row is not None else 0


def _empty_totals() -> dict:
    return {
        "carryover": 0,
        "annual_dues": 0,
        "expected_total": 0,
        "paid": 0,
        "outstanding": 0,
    }


def build_dues(con: sqlite3.Connection, as_of: date) -> dict:
    """Assemble the full dues payload for `as_of` (the frozen API shape).

    For a pre-2025 year, dues are not tracked: `dues_tracked=false`, empty units,
    zero totals, still a `200`. For 2025+, one entry per unit with its ownership,
    carryover, annual dues, expected, paid, and outstanding, plus footing totals.
    """
    year = as_of.year
    if year < BASE_YEAR:
        return {
            "as_of_date": as_of.isoformat(),
            "year": year,
            "dues_tracked": False,
            "operating_budget": 0,
            "units": [],
            "totals": _empty_totals(),
        }

    op = operating_budget(con, year)
    rows = con.execute(
        "SELECT number, ownership_pct FROM units ORDER BY number"
    ).fetchall()

    units: list[dict] = []
    for row in rows:
        number = row["number"]
        pm = int(row["ownership_pct"])
        dues = annual_dues(op, pm)
        carryover = carry_in(con, number, pm, year)
        paid = unit_paid(con, number, year, as_of)
        expected_total = carryover + dues
        units.append(
            {
                "unit": number,
                "ownership_per_mille": pm,
                "carryover": carryover,
                "annual_dues": dues,
                "expected_total": expected_total,
                "paid": paid,
                "outstanding": expected_total - paid,
            }
        )

    totals = {
        field: sum(u[field] for u in units)
        for field in (
            "carryover",
            "annual_dues",
            "expected_total",
            "paid",
            "outstanding",
        )
    }

    return {
        "as_of_date": as_of.isoformat(),
        "year": year,
        "dues_tracked": True,
        "operating_budget": op,
        "units": units,
        "totals": totals,
    }
