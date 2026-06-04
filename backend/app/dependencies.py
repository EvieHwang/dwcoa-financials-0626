"""Shared FastAPI dependencies: role resolution and route guards.

Role is always derived server-side from the verified session token; nothing
the client asserts (header, body, query) is consulted (B4 / BC1).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from .auth import role_from_request


def current_role(request: Request) -> str | None:
    return role_from_request(request)


def require_auth(role: str | None = Depends(current_role)) -> str:
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return role


def require_admin(role: str | None = Depends(current_role)) -> str:
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return role
