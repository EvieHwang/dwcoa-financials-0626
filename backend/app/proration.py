"""Centralized YTD budget-timing proration (R7).

The one place mid-year "budget expected through a date" is computed. Pure: no
I/O, no DB, deterministic given its arguments. Money is integer cents throughout
and the arithmetic is exact decimal (never binary float) so results never drift.
Dashboard (006) imports this; Budgets (005) owns and tests it.

`prorated_ytd` steps by *period reached*: a period contributes its full share the
moment the as-of date enters it (an annual line counts in full from January 1; a
quarterly line steps at quarter boundaries; a monthly line accrues month by
month). The effective-timing rule (`effective_timing`) is the single
override-beats-default resolution used by R1 and every caller of the engine.
"""
from __future__ import annotations

import math
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

TIMINGS = ("monthly", "quarterly", "annual")


def effective_timing(override: str | None, category_default: str) -> str:
    """The line's timing: its per-line override when set, else the category
    default. This is the resolution R1 returns and the engine's callers apply
    before prorating (so a caller can never silently prorate the default when an
    override exists)."""
    return override if override is not None else category_default


def prorated_ytd(
    annual_cents: int,
    timing: str,
    as_of: date,
    budget_year: int,
) -> int:
    """Budget expected through `as_of`, in integer cents, stepped by period.

    - `as_of.year < budget_year` -> 0 (the year hasn't started), every timing.
    - `as_of.year > budget_year` -> full `annual_cents`, every timing.
    - within the budget year, with month `m` (1-12):
        monthly   -> round(annual_cents * m / 12)
        quarterly -> round(annual_cents * ceil(m/3) / 4)
        annual    -> annual_cents in full (from January 1)

    Rounding is half-up to the nearest cent, on exact decimal arithmetic.
    """
    if as_of.year < budget_year:
        return 0
    if as_of.year > budget_year:
        return int(annual_cents)

    if timing == "annual":
        return int(annual_cents)

    month = as_of.month
    if timing == "monthly":
        numerator, denominator = month, 12
    elif timing == "quarterly":
        numerator, denominator = math.ceil(month / 3), 4
    else:
        raise ValueError(f"unknown timing {timing!r}")

    value = (Decimal(int(annual_cents)) * numerator / denominator).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return int(value)
