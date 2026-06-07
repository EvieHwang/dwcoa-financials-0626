"""Budgets router (slice 5): the `/api/budgets` HTTP surface — list, upsert,
copy, lock, delete — wiring foundation's guards to the `app.budgets` logic.

Reuses foundation's `require_auth`/`require_admin` (role is server-side only),
the `is_cross_origin` same-origin (CSRF) defense, and `get_connection` (FK
enforcement on). Reads need any session; writes need admin + same-origin. Every
multi-statement write runs in a single transaction (rollback on error) so a
failed write never leaves a partial year.

Validation is done explicitly at the edge and returned as 400 (the project's
manual-validation convention), not FastAPI/Pydantic's default 422: handlers read
the year query and the JSON body loosely and validate the documented cases
themselves. `annual_amount` must be a JSON integer (a float like 100.5 fails);
`year` must parse to an integer in 2000-2100; lock violations are 403; a
copy-into-non-empty without overwrite is 409 — all before any write.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import auth as auth_mod
from .. import budgets as budgets_logic
from ..db import get_connection
from ..dependencies import require_admin, require_auth
from ..proration import TIMINGS

router = APIRouter(prefix="/api/budgets")

YEAR_MIN = 2000
YEAR_MAX = 2100


def _reject_cross_origin(request: Request) -> None:
    if auth_mod.is_cross_origin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin request rejected",
        )


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _is_int(value: Any) -> bool:
    # JSON `true`/`false` parse to Python bool (an int subclass); reject those.
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_year(value: Any) -> int:
    """Parse a year from a query string or JSON value; 400 unless it is an
    integer (or integer-valued string) within 2000-2100."""
    if isinstance(value, bool) or value is None:
        raise _bad("Invalid year")
    if isinstance(value, int):
        year = value
    elif isinstance(value, str):
        try:
            year = int(value)
        except ValueError:
            raise _bad("Invalid year")
    else:
        raise _bad("Invalid year")
    if not (YEAR_MIN <= year <= YEAR_MAX):
        raise _bad("Year out of range")
    return year


async def _json_object(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise _bad("Invalid JSON body")
    if not isinstance(body, dict):
        raise _bad("Body must be a JSON object")
    return body


def _require_unlocked(con, year: int) -> None:
    locked, _ = budgets_logic.get_lock(con, year)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Year {year} is locked",
        )


@router.get("")
def list_budgets(request: Request, _role: str = Depends(require_auth)):
    year = _validate_year(request.query_params.get("year"))
    con = get_connection(request.app.state.config.database_path)
    try:
        locked, locked_at = budgets_logic.get_lock(con, year)
        entries = budgets_logic.list_year_budgets(con, year)
    finally:
        con.close()
    return {
        "year": year,
        "locked": locked,
        "locked_at": locked_at,
        "budgets": entries,
    }


@router.post("")
async def upsert_budget(request: Request, _role: str = Depends(require_admin)):
    _reject_cross_origin(request)
    body = await _json_object(request)

    year = _validate_year(body.get("year"))
    category_id = body.get("category_id")
    if not _is_int(category_id):
        raise _bad("category_id must be an integer")
    annual_amount = body.get("annual_amount")
    if not _is_int(annual_amount) or annual_amount < 0:
        raise _bad("annual_amount must be a non-negative integer (cents)")
    # Omitted OR explicit null clears the override; a present value must be valid.
    timing = body.get("timing")
    if timing is not None and timing not in TIMINGS:
        raise _bad("timing must be one of monthly/quarterly/annual")

    con = get_connection(request.app.state.config.database_path)
    try:
        if not budgets_logic.category_exists(con, category_id):
            raise _bad("Unknown category")
        _require_unlocked(con, year)
        try:
            budgets_logic.upsert_line(
                con,
                year=year,
                category_id=category_id,
                annual_amount=annual_amount,
                timing=timing,
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
        return budgets_logic.get_entry(con, year, category_id)
    finally:
        con.close()


@router.post("/copy")
async def copy_budgets(request: Request, _role: str = Depends(require_admin)):
    _reject_cross_origin(request)
    body = await _json_object(request)

    from_year = _validate_year(body.get("from_year"))
    to_year = _validate_year(body.get("to_year"))
    if from_year == to_year:
        raise _bad("from_year and to_year must differ")
    overwrite = bool(body.get("overwrite", False))

    con = get_connection(request.app.state.config.database_path)
    try:
        # A locked target refuses the copy regardless of overwrite (R5); the
        # source being locked does not matter — it is only read.
        _require_unlocked(con, to_year)
        if budgets_logic.count_year(con, from_year) == 0:
            raise _bad("Source year has no budgets to copy")
        if budgets_logic.count_year(con, to_year) > 0 and not overwrite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Year {to_year} already has budgets; "
                    "pass overwrite to replace them"
                ),
            )
        try:
            count = budgets_logic.copy_year(
                con, from_year=from_year, to_year=to_year, overwrite=overwrite
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    finally:
        con.close()
    return {"from_year": from_year, "to_year": to_year, "count": count}


@router.post("/lock")
async def lock_budget(request: Request, _role: str = Depends(require_admin)):
    _reject_cross_origin(request)
    body = await _json_object(request)

    year = _validate_year(body.get("year"))
    locked = body.get("locked")
    if not isinstance(locked, bool):
        raise _bad("locked must be a boolean")

    con = get_connection(request.app.state.config.database_path)
    try:
        try:
            locked_at = budgets_logic.set_lock(con, year=year, locked=locked)
            con.commit()
        except Exception:
            con.rollback()
            raise
    finally:
        con.close()
    return {"year": year, "locked": locked, "locked_at": locked_at}


@router.delete("")
def delete_budget(request: Request, _role: str = Depends(require_admin)):
    _reject_cross_origin(request)
    year = _validate_year(request.query_params.get("year"))
    raw_cat = request.query_params.get("category_id")
    if raw_cat is None:
        raise _bad("category_id is required")
    try:
        category_id = int(raw_cat)
    except ValueError:
        raise _bad("category_id must be an integer")

    con = get_connection(request.app.state.config.database_path)
    try:
        _require_unlocked(con, year)
        try:
            count = budgets_logic.delete_line(
                con, year=year, category_id=category_id
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    finally:
        con.close()
    return {"count": count}
