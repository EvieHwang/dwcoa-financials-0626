"""Story D1–D2 / E4 — schema migrations create the full schema, idempotently."""
import sqlite3

from fastapi.testclient import TestClient

EXPECTED_TABLES = {
    "transactions",
    "categories",
    "budgets",
    "units",
    "accounts",
    "categorize_rules",
    "unit_past_dues",
    "app_config",
}


def _table_names(db_path):
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        con.close()
    return {r[0] for r in rows}


def test_all_tables_created(client, app_env):
    # client fixture has started the app -> migrations have run
    names = _table_names(app_env["db_path"])
    assert EXPECTED_TABLES <= names, f"missing: {EXPECTED_TABLES - names}"


def test_db_path_from_env(client, app_env):
    assert app_env["db_path"].exists()


def test_migrations_idempotent(make_app, app_env):
    with TestClient(make_app(), base_url="https://testserver"):
        pass
    before = _table_names(app_env["db_path"])
    # second startup against the already-migrated DB must not error or change schema
    with TestClient(make_app(), base_url="https://testserver"):
        pass
    after = _table_names(app_env["db_path"])
    assert before == after
    assert EXPECTED_TABLES <= after
