"""Application configuration, read from the environment at app-build time.

The three security-critical secrets are required: the app refuses to start
without them rather than booting with an insecure default (EC1 / BC3).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Default SQLite location is the Fly volume mount; configurable via env (E4).
DEFAULT_DATABASE_PATH = "/data/dwcoa.db"

# Required secrets — absence is a hard startup failure (EC1).
REQUIRED_SECRETS = ("ADMIN_PASSWORD_HASH", "BOARD_PASSWORD_HASH", "SESSION_SECRET")

SESSION_COOKIE = "dwcoa_session"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    database_path: str
    admin_password_hash: str
    board_password_hash: str
    session_secret: str
    static_dir: str
    login_max_attempts: int
    login_window_seconds: int


def load_config() -> Config:
    """Read config from the environment, failing fast on missing secrets."""
    missing = [name for name in REQUIRED_SECRETS if not os.environ.get(name)]
    if missing:
        # Never include the values — only the names of what's missing.
        raise ConfigError(
            "Missing required configuration: " + ", ".join(sorted(missing))
        )

    static_default = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

    return Config(
        database_path=os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH),
        admin_password_hash=os.environ["ADMIN_PASSWORD_HASH"],
        board_password_hash=os.environ["BOARD_PASSWORD_HASH"],
        session_secret=os.environ["SESSION_SECRET"],
        static_dir=os.environ.get("STATIC_DIR", static_default),
        login_max_attempts=int(os.environ.get("LOGIN_MAX_ATTEMPTS", "10")),
        login_window_seconds=int(os.environ.get("LOGIN_WINDOW_SECONDS", "300")),
    )
