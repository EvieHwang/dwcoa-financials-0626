"""Per-unit homeowner statement assembler (slice 8), as plain testable functions.

The "My Account" statement is, by design, *provably equal to the board's view*
for a single unit: its current-year and prior-year figures are not re-derived —
they come from the same `app.dues` functions Dues by Unit (007) uses. The only new
integer-cent math this module adds is **payment guidance** (turning the remaining
balance into a monthly target, with year-boundary and paid-up edge states) and the
**recent-payments** window. Business logic lives here, not in the route handler
(constitution). Money is integer cents end to end — no floats anywhere.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from .dues import (
    BASE_YEAR,
    annual_dues,
    carry_in,
    operating_budget,
    unit_paid,
)


def _round_half_up_div(numerator: int, denominator: int) -> int:
    """Integer round-half-up of `numerator / denominator` (denominator > 0),
    matching `app.dues.annual_dues`' rounding style — no float."""
    return (2 * numerator + denominator) // (2 * denominator)


def months_remaining(as_of: date) -> int:
    """Months left in the as-of year under the "snap at the 15th" rule:
    `(12 - month + 1)` when the as-of day <= 15, else `(12 - month)`. So Jan 1 and
    Jan 15 -> 12, Jan 16 -> 11, Mar 1 -> 10, Mar 16 -> 9, Dec 15 -> 1, Dec 16 -> 0.
    Never negative."""
    base = 12 - as_of.month
    return base + 1 if as_of.day <= 15 else base


def payment_guidance(
    annual_dues_cents: int, remaining_cents: int, as_of: date
) -> dict:
    """The new integer-cent guidance layer (no DB access).

    - `standard_monthly` = round-half-up(annual_dues / 12), always present.
    - `months_remaining` = the 15th rule above.
    - `status` / `suggested_monthly`, resolved in this order:
      credit (< 0) -> paid_in_full (== 0) -> due_by_year_end (> 0, no months
      remain — never a divide by zero) -> owes (> 0, months remain;
      `suggested_monthly` = round-half-up(remaining / months_remaining)).
    """
    months = months_remaining(as_of)
    standard_monthly = _round_half_up_div(annual_dues_cents, 12)

    if remaining_cents < 0:
        status, suggested = "credit", None
    elif remaining_cents == 0:
        status, suggested = "paid_in_full", None
    elif months == 0:
        status, suggested = "due_by_year_end", None
    else:
        status = "owes"
        suggested = _round_half_up_div(remaining_cents, months)

    return {
        "standard_monthly": standard_monthly,
        "months_remaining": months,
        "suggested_monthly": suggested,
        "status": status,
    }


def recent_payments(
    con: sqlite3.Connection, unit_number: str, year: int, as_of: date
) -> list[dict]:
    """The unit's own `Dues <unit_number>` credits in the calendar years `year-1`
    and `year`, with `post_date <= as_of`, newest first by date. Each entry is
    `{"date": "YYYY-MM-DD", "amount": <cents>}`. No other unit's or category's
    credits; same-date relative order is unspecified."""
    rows = con.execute(
        """
        SELECT t.post_date AS post_date, t.credit AS credit
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE c.name = ?
          AND t.post_date >= ?
          AND t.post_date <= ?
        ORDER BY t.post_date DESC
        """,
        (f"Dues {unit_number}", f"{year - 1}-01-01", as_of.isoformat()),
    ).fetchall()
    return [{"date": r["post_date"], "amount": int(r["credit"])} for r in rows]


def _not_tracked(unit_number: str, ownership_per_mille: int, as_of: date) -> dict:
    return {
        "unit": unit_number,
        "ownership_per_mille": ownership_per_mille,
        "as_of_date": as_of.isoformat(),
        "year": as_of.year,
        "dues_tracked": False,
        "current_year": None,
        "prior_year": None,
        "payment_guidance": None,
        "recent_payments": [],
    }


def build_account(
    con: sqlite3.Connection,
    unit_number: str,
    ownership_per_mille: int,
    as_of: date,
) -> dict:
    """Assemble the full per-unit statement payload (the frozen API shape).

    Current-year and prior-year amounts delegate to `app.dues` (engine reuse, not
    re-derivation); this function adds only the prior-year display breakdown,
    payment guidance, and the recent-payments window. A pre-2025 as-of date reports
    not-tracked (mirrors `GET /api/dues`).
    """
    year = as_of.year
    if year < BASE_YEAR:
        return _not_tracked(unit_number, ownership_per_mille, as_of)

    p = ownership_per_mille
    carryover = carry_in(con, unit_number, p, year)
    dues = annual_dues(operating_budget(con, year), p)
    total_due = carryover + dues
    paid_ytd = unit_paid(con, unit_number, year, as_of)
    remaining = total_due - paid_ytd

    current_year = {
        "year": year,
        "carryover": carryover,
        "annual_dues": dues,
        "total_due": total_due,
        "paid_ytd": paid_ytd,
        "remaining_balance": remaining,
    }

    prior = year - 1
    prior_available = prior >= BASE_YEAR
    if prior_available:
        prior_dues = annual_dues(operating_budget(con, prior), p)
        prior_paid = unit_paid(con, unit_number, prior, date(prior, 12, 31))
    else:
        prior_dues = None
        prior_paid = None

    prior_year = {
        "year": prior,
        "data_available": prior_available,
        "annual_dues_budgeted": prior_dues,
        "total_paid": prior_paid,
        # The current year's carryover *is* the balance carried forward; surfaced
        # in both blocks (present even when the prior year predates tracking).
        "balance_carried_forward": carryover,
    }

    return {
        "unit": unit_number,
        "ownership_per_mille": p,
        "as_of_date": as_of.isoformat(),
        "year": year,
        "dues_tracked": True,
        "current_year": current_year,
        "prior_year": prior_year,
        "payment_guidance": payment_guidance(dues, remaining, as_of),
        "recent_payments": recent_payments(con, unit_number, year, as_of),
    }
