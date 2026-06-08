"""Account router (slice 8): the `/api/account` read endpoint.

One authenticated GET returning a single unit's homeowner statement for an as-of
date. Reuses foundation's `require_auth` (role server-side only; both roles read)
and `get_connection`, and the exact `as_of` edge-validation shape from
`routers/dues.py`. Read-only — no write path, so no transaction and no
cross-origin/CSRF guard (a GET changes no state).

Unit selection is a convenience, not an authorization boundary (declaration): any
authenticated caller may read any unit. The `unit` value is validated against the
seeded units and passed only as a bound parameter — never string-interpolated.
"""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..account import build_account
from ..db import get_connection
from ..dependencies import require_auth

router = APIRouter()

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_as_of(raw: str | None) -> date:
    """Today when absent; a strict YYYY-MM-DD date otherwise; 400 on anything
    else (the project's manual-validation convention, mirroring routers/dues.py)."""
    if raw is None:
        return date.today()
    if not _ISO_DATE.match(raw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid as_of date"
        )
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid as_of date"
        )


@router.get("/api/account")
def account(request: Request, _role: str = Depends(require_auth)):
    unit = request.query_params.get("unit")
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unit is required"
        )
    as_of = _parse_as_of(request.query_params.get("as_of"))

    con = get_connection(request.app.state.config.database_path)
    try:
        row = con.execute(
            "SELECT ownership_pct FROM units WHERE number = ?", (unit,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown unit"
            )
        return build_account(con, unit, int(row["ownership_pct"]), as_of)
    finally:
        con.close()
