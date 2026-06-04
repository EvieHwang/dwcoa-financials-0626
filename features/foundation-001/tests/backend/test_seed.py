"""Story D3–D6 — reference data is seeded, idempotent, and money is integer cents."""
import sqlite3

from fastapi.testclient import TestClient

# 2025 annual budget, in integer cents, keyed by category name (from spec §Seed data)
EXPECTED_BUDGET_CENTS = {
    "Dues 101": 595475, "Dues 201": 595475, "Dues 301": 595475,
    "Dues 102": 529311, "Dues 202": 529311, "Dues 302": 529311,
    "Dues 103": 570027, "Dues 203": 570027, "Dues 303": 570027,
    "Interest income": 2600,
    "Reserve Contribution": 1800000,
    "Bulger Safe & Lock": 40000,
    "Cintas Fire Protection": 150000,
    "Common Area Cleaning": 270000,
    "Fire Alarm": 330000,
    "Grounds/Landscaping": 1200000,
    "Other": 750000,
    "Insurance Premiums": 450000,
    "Seattle City Light": 600000,
}


def _conn(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _count(db_path, table):
    con = _conn(db_path)
    try:
        return con.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    finally:
        con.close()


def test_reference_data_seeded(client, app_env):
    db = app_env["db_path"]
    assert _count(db, "units") == 9
    assert _count(db, "accounts") == 3
    con = _conn(db)
    try:
        cats = {r["name"] for r in con.execute("SELECT name FROM categories")}
    finally:
        con.close()
    assert {"Dues 101", "Interest income", "Grounds/Landscaping",
            "Reserve Contribution", "Transfers"} <= cats


def test_budget_amounts_in_cents(client, app_env):
    con = _conn(app_env["db_path"])
    try:
        rows = con.execute(
            """SELECT c.name AS name, b.annual_amount AS amt
               FROM budgets b JOIN categories c ON c.id = b.category_id
               WHERE b.year = 2025"""
        ).fetchall()
    finally:
        con.close()
    got = {r["name"]: r["amt"] for r in rows}
    for name, cents in EXPECTED_BUDGET_CENTS.items():
        assert got.get(name) == cents, f"{name}: expected {cents} cents, got {got.get(name)}"


def test_money_is_integer_cents(client, app_env):
    con = _conn(app_env["db_path"])
    try:
        rows = con.execute("SELECT annual_amount FROM budgets WHERE year = 2025").fetchall()
    finally:
        con.close()
    assert rows, "no 2025 budgets seeded"
    for r in rows:
        assert isinstance(r["annual_amount"], int), "budget amounts must be stored as integer cents"


def test_ownership_values(viewer_client):
    # ownership exposed by the API as a ratio, regardless of storage encoding
    data = viewer_client.get("/api/reference").json()
    units = {u["number"]: float(u["ownership_pct"]) for u in data["units"]}
    for n in ("101", "201", "301"):
        assert abs(units[n] - 0.117) < 1e-9
    for n in ("102", "202", "302"):
        assert abs(units[n] - 0.104) < 1e-9
    for n in ("103", "203", "303"):
        assert abs(units[n] - 0.112) < 1e-9


def test_ownership_stored_exactly(client, app_env):
    # D5: ownership stored as exact integer thousandths (per-mille), never binary float.
    con = _conn(app_env["db_path"])
    try:
        rows = con.execute("SELECT number, ownership_pct FROM units").fetchall()
    finally:
        con.close()
    by_unit = {r["number"]: r["ownership_pct"] for r in rows}
    for value in by_unit.values():
        assert isinstance(value, int), "ownership must be stored as an exact integer (per-mille)"
    assert by_unit["101"] == 117
    assert by_unit["102"] == 104
    assert by_unit["103"] == 112


def test_seed_idempotent(make_app, app_env):
    with TestClient(make_app(), base_url="https://testserver"):
        pass
    units_after_first = _count(app_env["db_path"], "units")
    budgets_after_first = _count(app_env["db_path"], "budgets")
    with TestClient(make_app(), base_url="https://testserver"):
        pass
    assert _count(app_env["db_path"], "units") == units_after_first == 9
    assert _count(app_env["db_path"], "budgets") == budgets_after_first
