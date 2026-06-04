"""Health endpoint (E1 / EC4). Public; reflects real DB readiness.

`db.check_connection` is referenced through the module so the deploy gate's
contract can be exercised (and monkeypatched) honestly.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .. import db

router = APIRouter()


@router.get("/api/health")
def health(request: Request):
    db_path = request.app.state.config.database_path
    if db.check_connection(db_path):
        return {"status": "ok"}
    return JSONResponse({"status": "unhealthy"}, status_code=503)
