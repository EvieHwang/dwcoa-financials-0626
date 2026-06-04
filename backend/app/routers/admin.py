"""Admin endpoint (Story B): app config, admin role only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..db import get_connection
from ..dependencies import require_admin

router = APIRouter(prefix="/api/admin")


@router.get("/config")
def admin_config(request: Request, _role: str = Depends(require_admin)):
    con = get_connection(request.app.state.config.database_path)
    try:
        config = {
            row["key"]: row["value"]
            for row in con.execute("SELECT key, value FROM app_config")
        }
    finally:
        con.close()
    return {"app_config": config}
