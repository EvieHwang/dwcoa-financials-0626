"""Canonical exact-money conversion, shared by the legacy importer and ingestion.

Monetary amounts are stored as integer cents end to end — never binary floats
(constitution: "Money"). Conversion goes through the value's *exact* decimal
string and rounds half away from zero, so float artifacts
(`832.06 * 100 == 83205.99999999999`) can never shift the result.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def dollars_to_cents(value: float | int | str | Decimal) -> int:
    """Exact integer cents from a numeric or decimal-string dollar amount.

    The caller passes an already-cleaned value (no currency symbols/commas);
    `Decimal` raises on anything it cannot parse, which the caller turns into a
    row-level error.
    """
    cents = (Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(cents)
