"""Reference endpoint (Story C): seeded units, accounts, active categories.

Auth required, any role. Ownership crosses the API boundary as the decimal
ratio (stored exactly as integer per-mille; never a binary float in storage).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..db import get_connection
from ..dependencies import require_auth

router = APIRouter()


@router.get("/api/reference")
def reference(request: Request, _role: str = Depends(require_auth)):
    con = get_connection(request.app.state.config.database_path)
    try:
        units = [
            {"number": row["number"], "ownership_pct": row["ownership_pct"] / 1000}
            for row in con.execute(
                "SELECT number, ownership_pct FROM units ORDER BY number"
            )
        ]
        accounts = [
            {"name": row["name"], "masked_number": row["masked_number"]}
            for row in con.execute(
                "SELECT name, masked_number FROM accounts ORDER BY name"
            )
        ]
        categories = [
            {"name": row["name"], "type": row["type"]}
            for row in con.execute(
                "SELECT name, type FROM categories WHERE active = 1 ORDER BY id"
            )
        ]
    finally:
        con.close()
    return {"units": units, "accounts": accounts, "categories": categories}
