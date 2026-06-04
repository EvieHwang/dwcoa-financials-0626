"""SQLite connection helpers and the health-probe seam.

`check_connection` is the readiness probe `/api/health` depends on (EC4/BC5);
it is referenced as a module attribute so tests can monkeypatch it.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection with row access by name and FK enforcement on."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def check_connection(db_path: str) -> bool:
    """True when the database file is reachable and answers a trivial query."""
    try:
        con = sqlite3.connect(db_path)
        try:
            con.execute("SELECT 1").fetchone()
        finally:
            con.close()
        return True
    except Exception:
        return False
