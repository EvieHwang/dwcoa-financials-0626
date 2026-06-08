"""Dues router (slice 7): the `/api/dues` read endpoint.

One authenticated GET returning the association-wide, per-unit dues table for an
as-of date. Reuses foundation's `require_auth` (role server-side only; both roles
read) and `get_connection`. Read-only — no write path, so no transaction and no
cross-origin/CSRF guard (a GET changes no state).

`as_of` is validated explicitly at the edge and returned as 400 (the project's
manual-validation convention, not Pydantic's 422), mirroring `routers/dashboard.py`:
absent -> today; present -> a strict `YYYY-MM-DD` date, parameterized into SQL
(never interpolated).
"""
from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..db import get_connection
from ..dependencies import require_auth
from ..dues import build_dues

router = APIRouter()

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_as_of(raw: str | None) -> date:
    """Today when absent; a strict YYYY-MM-DD date otherwise; 400 on anything
    else."""
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


@router.get("/api/dues")
def dues(request: Request, _role: str = Depends(require_auth)):
    as_of = _parse_as_of(request.query_params.get("as_of"))
    con = get_connection(request.app.state.config.database_path)
    try:
        return build_dues(con, as_of)
    finally:
        con.close()
