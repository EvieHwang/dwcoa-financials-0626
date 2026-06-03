"""Authentication utilities."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt
import jwt

# Token expiration time
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: Plain text password
        password_hash: Bcrypt hash to check against

    Returns:
        True if password matches
    """
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def get_jwt_secret() -> str:
    """Get JWT secret from environment."""
    secret = os.environ.get('JWT_SECRET', '')
    if not secret:
        # Fallback for local development
        secret = 'dev-secret-do-not-use-in-production'
    return secret


def create_token(role: str) -> Tuple[str, datetime]:
    """Create a JWT token.

    Args:
        role: User role ('admin' or 'board')

    Returns:
        Tuple of (token string, expiration datetime)
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {
        'role': role,
        'exp': expires_at,
        'iat': datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm='HS256')
    return token, expires_at


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_role_from_token(token: str) -> Optional[str]:
    """Get the role from a token.

    Args:
        token: JWT token string

    Returns:
        Role string ('admin' or 'board'), or None if invalid
    """
    payload = verify_token(token)
    if payload:
        return payload.get('role')
    return None


def authenticate(password: str) -> Optional[Tuple[str, str, datetime]]:
    """Authenticate with a password and return token.

    Args:
        password: Plain text password

    Returns:
        Tuple of (token, role, expires_at), or None if invalid
    """
    admin_hash = os.environ.get('ADMIN_PASSWORD_HASH', '')
    board_hash = os.environ.get('BOARD_PASSWORD_HASH', '')

    # Check admin password first
    if admin_hash and verify_password(password, admin_hash):
        token, expires_at = create_token('admin')
        return token, 'admin', expires_at

    # Check board password
    if board_hash and verify_password(password, board_hash):
        token, expires_at = create_token('board')
        return token, 'board', expires_at

    return None


def require_auth(headers: dict) -> Optional[dict]:
    """Check authorization header and return token payload.

    Args:
        headers: Request headers dict

    Returns:
        Token payload dict, or None if not authorized
    """
    auth_header = headers.get('authorization', headers.get('Authorization', ''))
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]  # Remove 'Bearer ' prefix
    return verify_token(token)


def require_admin(headers: dict) -> bool:
    """Check if request has admin authorization.

    Args:
        headers: Request headers dict

    Returns:
        True if admin authorized
    """
    payload = require_auth(headers)
    return payload is not None and payload.get('role') == 'admin'
