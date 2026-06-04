"""R8 — a versioned migration adds budget_locks, idempotently."""
import sqlite3


def _tables(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()


def test_budget_locks_created(tmp_path):
    from app.migrations import run_migrations

    db = tmp_path / "m.db"
    run_migrations(str(db))
    assert "budget_locks" in _tables(db)

    con = sqlite3.connect(str(db))
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(budget_locks)")}
    finally:
        con.close()
    assert {"year", "locked", "locked_at"} <= cols


def test_budget_locks_migration_idempotent(tmp_path):
    from app.migrations import run_migrations

    db = tmp_path / "m.db"
    run_migrations(str(db))
    before = _tables(db)
    run_migrations(str(db))  # second run must not error or change schema
    assert _tables(db) == before


def test_budget_locks_version_recorded(tmp_path):
    from app.migrations import run_migrations

    db = tmp_path / "m.db"
    run_migrations(str(db))
    con = sqlite3.connect(str(db))
    try:
        versions = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
    finally:
        con.close()
    # foundation is version 1; budget_locks adds a later version.
    assert 1 in versions
    assert max(versions) >= 2
