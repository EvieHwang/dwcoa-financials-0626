# @frozen — the public budget read/upsert/delete contract: GET/POST/DELETE
# /api/budgets, their request/response shapes, validation, and exact integer
# cents. The frontend editor and dashboard consume this surface.
"""R1 (read), R2 (upsert), R6 (delete)."""
from conftest import (
    category_id,
    category_id_by_type,
    count_budgets,
    get_budget_row,
    insert_budget,
    set_category_active,
)

# An unseeded year: seed.py only seeds 2025, so this year starts with no budget
# rows — letting the zero-fill / uniqueness / count assertions mean what they say.
YEAR = 2030


# --- R1: read ---------------------------------------------------------------

def test_list_zero_fills_unbudgeted_categories(admin_client, app_env):
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    assert body["year"] == YEAR
    assert body["locked"] is False
    by_name = {b["category_name"]: b for b in body["budgets"]}
    # An Expense category with no row for the year shows zeros + inherited timing.
    grounds = by_name["Grounds/Landscaping"]
    assert grounds["annual_amount"] == 0
    assert grounds["timing"] is None
    assert grounds["effective_timing"] == grounds["category_default_timing"]


def test_list_returns_stored_cents_and_override(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Insurance Premiums")
    insert_budget(db, year=YEAR, category_id=cid, annual_amount=450000,
                  timing="quarterly")
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    line = next(b for b in body["budgets"] if b["category_id"] == cid)
    assert line["annual_amount"] == 450000          # exact cents
    assert line["timing"] == "quarterly"            # the override
    assert line["effective_timing"] == "quarterly"  # override wins


def test_list_excludes_transfer_internal_without_rows(admin_client, app_env):
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    types = {b["category_type"] for b in body["budgets"]}
    assert types <= {"Income", "Expense"}


def test_list_includes_only_budgetable_then_rows(admin_client, app_env):
    # A budget row on a non-Income/Expense category still surfaces (migrated data
    # must stay visible/editable) even though such types are otherwise excluded.
    db = app_env["db_path"]
    internal = category_id_by_type(db, "Internal")
    insert_budget(db, year=YEAR, category_id=internal, annual_amount=5000)
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    assert any(b["category_id"] == internal for b in body["budgets"])


def test_list_excludes_inactive_category_without_row(admin_client, app_env):
    # An Income/Expense category that is inactive AND has no row for the year is
    # excluded (only *active* budgetable categories are zero-filled).
    db = app_env["db_path"]
    cid = category_id(db, "Fire Alarm")
    set_category_active(db, category_id=cid, active=False)
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    assert all(b["category_id"] != cid for b in body["budgets"])


def test_list_includes_inactive_category_with_row(admin_client, app_env):
    # ...but if that inactive category has a row for the year, it stays visible.
    db = app_env["db_path"]
    cid = category_id(db, "Fire Alarm")
    insert_budget(db, year=YEAR, category_id=cid, annual_amount=330000)
    set_category_active(db, category_id=cid, active=False)
    body = admin_client.get(f"/api/budgets?year={YEAR}").json()
    assert any(b["category_id"] == cid for b in body["budgets"])


def test_list_rejects_bad_year(admin_client):
    assert admin_client.get("/api/budgets?year=not-a-year").status_code == 400
    assert admin_client.get("/api/budgets?year=1500").status_code == 400


# --- R2: upsert -------------------------------------------------------------

def test_upsert_creates_then_replaces_without_duplicate(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Seattle City Light")
    r1 = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 600000,
    })
    assert r1.status_code == 200
    assert r1.json()["annual_amount"] == 600000
    # Update the same line.
    r2 = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 650000,
    })
    assert r2.status_code == 200
    assert r2.json()["annual_amount"] == 650000
    # Exactly one row for (year, category) — the UNIQUE invariant holds.
    assert count_budgets(db, YEAR) == 1
    assert get_budget_row(db, year=YEAR, category_id=cid)["annual_amount"] == 650000


def test_upsert_stores_exact_cents(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Fire Alarm")
    admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 1234,
    })
    assert get_budget_row(db, year=YEAR, category_id=cid)["annual_amount"] == 1234


def test_upsert_timing_override_set_and_clear(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    # Set an override.
    admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 750000,
        "timing": "annual",
    })
    assert get_budget_row(db, year=YEAR, category_id=cid)["timing"] == "annual"
    # Re-upsert without timing clears the override (inherit category default).
    admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 750000,
    })
    assert get_budget_row(db, year=YEAR, category_id=cid)["timing"] is None


def test_upsert_rejects_negative_amount(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    r = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": -100,
    })
    assert r.status_code == 400
    assert get_budget_row(db, year=YEAR, category_id=cid) is None  # nothing written


def test_upsert_rejects_non_integer_amount(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Other")
    r = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 100.5,
    })
    assert r.status_code == 400
    assert get_budget_row(db, year=YEAR, category_id=cid) is None


def test_upsert_rejects_unknown_category(admin_client):
    r = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": 999999, "annual_amount": 1000,
    })
    assert r.status_code == 400


def test_upsert_rejects_invalid_timing(admin_client, app_env):
    cid = category_id(app_env["db_path"], "Other")
    r = admin_client.post("/api/budgets", json={
        "year": YEAR, "category_id": cid, "annual_amount": 1000,
        "timing": "weekly",
    })
    assert r.status_code == 400


# --- R6: delete -------------------------------------------------------------

def test_delete_removes_line(admin_client, app_env):
    db = app_env["db_path"]
    cid = category_id(db, "Common Area Cleaning")
    insert_budget(db, year=YEAR, category_id=cid, annual_amount=270000)
    r = admin_client.delete(f"/api/budgets?year={YEAR}&category_id={cid}")
    assert r.status_code == 200
    assert get_budget_row(db, year=YEAR, category_id=cid) is None


def test_delete_is_idempotent(admin_client, app_env):
    cid = category_id(app_env["db_path"], "Common Area Cleaning")
    # Deleting a non-existent line succeeds with count 0.
    r = admin_client.delete(f"/api/budgets?year={YEAR}&category_id={cid}")
    assert r.status_code == 200
    assert r.json()["count"] == 0
