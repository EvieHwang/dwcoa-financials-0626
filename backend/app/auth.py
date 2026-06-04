"""Auth & session: password verification, signed-token sessions, role guards,
CSRF same-origin defense, and a failed-attempt rate limiter.

Role is *only ever* derived from a valid JWT signature (BC1). No secret value
(password, hash, signing key, raw token) is logged anywhere (BC9).
"""
from __future__ import annotations

import datetime as dt
import time
from typing import Optional
from urllib.parse import urlparse

import bcrypt
import jwt
from fastapi import Request

from .config import SESSION_COOKIE, Config

JWT_ALGORITHM = "HS256"
SESSION_TTL = dt.timedelta(hours=12)


# --- password verification -------------------------------------------------

def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time bcrypt verification. Never logs either argument."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def role_for_password(password: str, config: Config) -> Optional[str]:
    """Return 'admin' / 'viewer' for a matching password, else None."""
    if verify_password(password, config.admin_password_hash):
        return "admin"
    if verify_password(password, config.board_password_hash):
        return "viewer"
    return None


# --- signed-token session --------------------------------------------------

def issue_token(role: str, secret: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"role": role, "exp": now + SESSION_TTL, "iat": now}
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def role_from_token(token: str, secret: str) -> Optional[str]:
    """Verify the token and return its role, or None for any invalid token.

    An expired or signature-invalid token is treated as no session (EC3),
    never as a server error.
    """
    try:
        claims = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    role = claims.get("role")
    if role in ("admin", "viewer"):
        return role
    return None


def role_from_request(request: Request) -> Optional[str]:
    """Resolve the verified role from the session cookie only."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    config: Config = request.app.state.config
    return role_from_token(token, config.session_secret)


# --- CSRF same-origin guard (A8 / BC8) -------------------------------------

def _same_origin(origin: str, request: Request) -> bool:
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        return False
    return (parsed.scheme, parsed.netloc) == (request.url.scheme, request.url.netloc)


def is_cross_origin(request: Request) -> bool:
    """True when a state-changing request carries a foreign Origin/Referer.

    Requests with neither header (non-browser clients / same-origin
    navigation) are treated as same-origin and allowed.
    """
    origin = request.headers.get("origin")
    if origin is not None:
        return not _same_origin(origin, request)
    referer = request.headers.get("referer")
    if referer is not None:
        return not _same_origin(referer, request)
    return False


# --- failed-attempt rate limiter (EC2) -------------------------------------

class RateLimiter:
    """In-memory, per-app-instance limiter that counts *failed* attempts per
    client IP within a rolling window. Successful logins never count, and the
    window expiry guarantees a correct password is never locked out forever.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        self._failures[key] = recent
        return recent

    def is_blocked(self, key: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        return len(self._recent(key, now)) >= self.max_attempts

    def record_failure(self, key: str, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        self._recent(key, now).append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"
