"""Auth endpoints: login, logout, me (Story A).

State-changing POSTs are CSRF-guarded (same-origin) and JSON-only. Failed
logins are rate-limited per client IP. No secret is ever placed in the
response body or logged.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from .. import auth as auth_mod
from ..config import SESSION_COOKIE
from ..dependencies import require_auth

router = APIRouter(prefix="/api/auth")


class LoginBody(BaseModel):
    password: str


def _reject_cross_origin(request: Request) -> None:
    if auth_mod.is_cross_origin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cross-origin request rejected"
        )


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    _reject_cross_origin(request)

    limiter = request.app.state.rate_limiter
    key = auth_mod.client_key(request)
    if limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts; try again later",
        )

    config = request.app.state.config
    role = auth_mod.role_for_password(body.password, config)
    if role is None:
        limiter.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    # Successful login: do not count toward the limit; clear prior failures.
    limiter.reset(key)
    token = auth_mod.issue_token(role, config.session_secret)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"role": role}


@router.post("/logout")
def logout(request: Request, response: Response):
    _reject_cross_origin(request)
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(role: str = Depends(require_auth)):
    return {"role": role}
